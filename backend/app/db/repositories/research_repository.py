"""Validated persistence with explicit transaction ownership and atomic revisions."""
import json
import re
from sqlalchemy import update
from sqlmodel import select
from app.db.models import Security, utc_now
from app.db.models.research import ResearchProject, ResearchRun, ResearchReviewEvent

MAX_JSON_BYTES = 500 * 1024
ERROR_CODES = {'not_configured','unsupported_provider','timeout','authentication','rate_limit','provider_unavailable','provider_error','invalid_output','invalid_references'}


class ResearchConflict(ValueError):
    pass


def json_object(raw):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > MAX_JSON_BYTES:
        raise ValueError('JSON object exceeds size limit')
    try:
        obj = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    except (ValueError, RecursionError):
        raise ValueError('invalid JSON object') from None
    if not isinstance(obj, dict):
        raise ValueError('JSON must be an object')
    # Parsing 1e999 is another route to a nonfinite number.
    try:
        json.dumps(obj, allow_nan=False)
    except (ValueError, RecursionError):
        raise ValueError('invalid JSON object') from None
    return obj


def bounded(limit):
    if isinstance(limit, bool) or not isinstance(limit,int) or not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    return limit


def fingerprint(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
        raise ValueError('invalid fingerprint')


def project_fields(values):
    limits={'question':2000,'hypothesis':4000,'horizon':200}
    if set(values)-set(limits)-{'status'}:
        raise ValueError('unknown project field')
    for key,limit in limits.items():
        if key not in values: continue
        value=values[key]
        if value is None and key!='question': continue
        if not isinstance(value,str) or len(value)>limit or (key=='question' and not value.strip()):
            raise ValueError('invalid '+key)
    if 'status' in values and values['status'] not in {'active','archived'}:
        raise ValueError('invalid project status')


class ResearchRepository:
    def __init__(self, session):
        self.session=session

    def _outer_transaction(self):
        connection=self.session.connection()
        if connection.dialect.name=='sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')

    def _save(self,row,commit):
        self._outer_transaction()
        with self.session.begin_nested():
            self.session.add(row)
            self.session.flush()
        if commit: self.session.commit()
        self.session.refresh(row)
        return row

    def get_project(self,project_id):
        return self.session.get(ResearchProject,project_id)

    def create_project(self, *, security_id, question, hypothesis=None, horizon=None, commit=True):
        values=dict(question=question,hypothesis=hypothesis,horizon=horizon)
        project_fields(values)
        if self.session.get(Security,security_id) is None: raise ValueError('security not found')
        return self._save(ResearchProject(security_id=security_id,**values),commit)

    def list_projects(self, *, security_id=None, limit=20):
        statement=select(ResearchProject)
        if security_id is not None: statement=statement.where(ResearchProject.security_id==security_id)
        return list(self.session.exec(statement.order_by(ResearchProject.updated_at.desc(),ResearchProject.id.desc()).limit(bounded(limit))))

    def update_project(self, project_id, *, expected_version, commit=True, **values):
        project_fields(values)
        if isinstance(expected_version,bool) or not isinstance(expected_version,int) or expected_version<1: raise ValueError('invalid version')
        row=self.get_project(project_id)
        if row is None: return None
        self.session.refresh(row)
        changes={k:v for k,v in values.items() if getattr(row,k)!=v}
        # The SQL predicate is the concurrency gate, including no-op requests.
        payload={**changes,'version':expected_version+1,'updated_at':utc_now()} if changes else {'version':expected_version}
        result=self.session.execute(update(ResearchProject).where(ResearchProject.id==project_id,ResearchProject.version==expected_version).values(**payload).execution_options(synchronize_session=False))
        if result.rowcount!=1: raise ResearchConflict('project version conflict')
        if commit: self.session.commit()
        else: self.session.flush()
        self.session.refresh(row)
        return row

    def archive_project(self, project_id, *, expected_version, commit=True):
        return self.update_project(project_id,expected_version=expected_version,status='archived',commit=commit)

    def append_run(self, *, commit=True, **values):
        project=self.get_project(values.get('project_id'))
        if project is None: raise ValueError('project not found')
        version=values.get('project_version')
        if isinstance(version,bool) or not isinstance(version,int) or not 1<=version<=project.version: raise ValueError('invalid project version')
        status=values.get('status')
        if status not in {'completed','failed'}: raise ValueError('invalid run status')
        json_object(values.get('input_snapshot_json')); fingerprint(values.get('input_fingerprint'))
        output=values.get('output_json')
        if output is not None: json_object(output)
        error=values.get('error_code')
        if status=='completed' and (output is None or error is not None): raise ValueError('invalid completed run')
        if status=='failed' and (output is not None or error not in ERROR_CODES): raise ValueError('invalid failed run')
        for name in ('model_name','prompt_version'):
            if not isinstance(values.get(name),str) or not 1<=len(values[name])<=200: raise ValueError('invalid '+name)
        return self._save(ResearchRun(**values),commit)

    def get_run(self,run_id):
        return self.session.get(ResearchRun,run_id)

    def list_runs(self,project_id, *, limit=20):
        return list(self.session.exec(select(ResearchRun).where(ResearchRun.project_id==project_id).order_by(ResearchRun.created_at.desc(),ResearchRun.id.desc()).limit(bounded(limit))))

    def latest_completed_run(self,project_id):
        return self.session.exec(select(ResearchRun).where(ResearchRun.project_id==project_id,ResearchRun.status=='completed').order_by(ResearchRun.created_at.desc(),ResearchRun.id.desc()).limit(1)).first()

    def record_event(self, *, project_id,run_id,input_fingerprint,reason_code,details_json,commit=True):
        run=self.get_run(run_id)
        if run is None or run.project_id!=project_id: raise ValueError('run/project mismatch')
        fingerprint(input_fingerprint); json_object(details_json)
        if reason_code not in {'data_changed','condition_triggered','data_unavailable'}: raise ValueError('invalid event reason')
        statement=select(ResearchReviewEvent).where(ResearchReviewEvent.project_id==project_id,ResearchReviewEvent.run_id==run_id,ResearchReviewEvent.input_fingerprint==input_fingerprint,ResearchReviewEvent.reason_code==reason_code)
        existing=self.session.exec(statement).first()
        if existing: return existing
        # Savepoint confines concurrent dedup conflicts without rolling back caller work.
        from sqlalchemy.exc import IntegrityError
        self._outer_transaction()
        try:
            with self.session.begin_nested():
                row=ResearchReviewEvent(project_id=project_id,run_id=run_id,input_fingerprint=input_fingerprint,reason_code=reason_code,details_json=details_json)
                self.session.add(row); self.session.flush()
        except IntegrityError:
            return self.session.exec(statement).one()
        if commit: self.session.commit()
        self.session.refresh(row)
        return row

    def list_events(self,project_id, *, limit=20):
        return list(self.session.exec(select(ResearchReviewEvent).where(ResearchReviewEvent.project_id==project_id).order_by(ResearchReviewEvent.created_at.desc(),ResearchReviewEvent.id.desc()).limit(bounded(limit))))

    def resolve_event(self,event_id, *, commit=True):
        row=self.session.get(ResearchReviewEvent,event_id)
        if row is None: return None
        self.session.execute(update(ResearchReviewEvent).where(ResearchReviewEvent.id==event_id,ResearchReviewEvent.status=='open').values(status='resolved',resolved_at=utc_now()).execution_options(synchronize_session=False))
        if commit: self.session.commit()
        else: self.session.flush()
        self.session.refresh(row)
        return row
