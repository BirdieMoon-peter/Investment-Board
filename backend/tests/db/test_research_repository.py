import json
import pytest
from app.db.repositories.research_repository import ResearchRepository, ResearchConflict


def test_projects_runs_events(session, seeded_security):
    repo = ResearchRepository(session)
    p = repo.create_project(security_id=seeded_security.id, question='Why?')
    assert p.version == 1
    p = repo.update_project(p.id, expected_version=1, question='Why now?')
    assert p.version == 2
    with pytest.raises(ResearchConflict):
        repo.update_project(p.id, expected_version=1, question='stale')
    run = repo.append_run(project_id=p.id, project_version=2, status='completed', input_snapshot_json='{}', input_fingerprint='a'*64, output_json='{}', model_name='synthetic', prompt_version='1')
    e = repo.record_event(project_id=p.id, run_id=run.id, input_fingerprint='b'*64, reason_code='data_changed', details_json='{}')
    assert repo.record_event(project_id=p.id, run_id=run.id, input_fingerprint='b'*64, reason_code='data_changed', details_json='{}').id == e.id
    assert repo.resolve_event(e.id).resolved_at
    assert repo.get_run(run.id).input_snapshot_json == '{}'


@pytest.mark.parametrize('payload', ['[]', '{"x":NaN}', '{"x":Infinity}', json.dumps({'x':'中'*180000})])
def test_json_rejection_atomic(session, seeded_security, payload):
    repo = ResearchRepository(session)
    p = repo.create_project(security_id=seeded_security.id, question='Why?')
    with pytest.raises(ValueError):
        repo.append_run(project_id=p.id, project_version=1, status='completed', input_snapshot_json=payload, input_fingerprint='a'*64, output_json='{}', model_name='test', prompt_version='1')
    assert repo.list_runs(p.id) == []


def test_validation_orphans_event_matching_and_transaction(session,seeded_security):
    repo=ResearchRepository(session)
    with pytest.raises(ValueError): repo.create_project(security_id=99999,question='x')
    with pytest.raises(ValueError): repo.create_project(security_id=seeded_security.id,question=' ')
    p=repo.create_project(security_id=seeded_security.id,question='x')
    other=repo.create_project(security_id=seeded_security.id,question='y')
    run=repo.append_run(project_id=p.id,project_version=1,status='failed',input_snapshot_json='{}',input_fingerprint='a'*64,model_name='test',prompt_version='1',error_code='timeout',commit=False)
    with pytest.raises(ValueError): repo.record_event(project_id=other.id,run_id=run.id,input_fingerprint='b'*64,reason_code='data_changed',details_json='{}')
    session.rollback()
    assert repo.list_runs(p.id)==[]
    assert repo.archive_project(p.id,expected_version=1).status=='archived'
    assert repo.update_project(p.id,expected_version=2,status='archived').version==2


def test_bounded_tie_order_latest_completed_and_safe_failure(session,seeded_security):
    repo=ResearchRepository(session); p=repo.create_project(security_id=seeded_security.id,question='x')
    common=dict(project_id=p.id,project_version=1,input_snapshot_json='{}',input_fingerprint='a'*64,model_name='test',prompt_version='1')
    completed=repo.append_run(**common,status='completed',output_json='{}')
    for _ in range(101): repo.append_run(**common,status='failed',error_code='timeout')
    assert len(repo.list_runs(p.id))==20
    assert repo.latest_completed_run(p.id).id==completed.id
    assert repo.list_runs(p.id)[0].id>repo.list_runs(p.id)[1].id
    with pytest.raises(ValueError): repo.list_runs(p.id,limit=101)
    with pytest.raises(ValueError): repo.append_run(**common,status='failed',error_code='SECRET raw provider body')


def test_atomic_sql_version_against_stale_identity(session,engine,seeded_security):
    from sqlmodel import Session
    repo=ResearchRepository(session); p=repo.create_project(security_id=seeded_security.id,question='x')
    with Session(engine) as other:
        ResearchRepository(other).update_project(p.id,expected_version=1,question='new')
    with pytest.raises(ResearchConflict): repo.update_project(p.id,expected_version=1,question='stale')
    session.refresh(p)
    assert p.question=='new' and p.version==2


def test_event_commit_false_rolls_back_and_resolve_is_idempotent(session,seeded_security):
    repo=ResearchRepository(session);p=repo.create_project(security_id=seeded_security.id,question='x')
    run=repo.append_run(project_id=p.id,project_version=1,status='completed',input_snapshot_json='{}',input_fingerprint='a'*64,output_json='{}',model_name='test',prompt_version='1')
    event=repo.record_event(project_id=p.id,run_id=run.id,input_fingerprint='b'*64,reason_code='data_changed',details_json='{}',commit=False)
    event_id=event.id;session.rollback()
    assert repo.list_events(p.id)==[]
    event=repo.record_event(project_id=p.id,run_id=run.id,input_fingerprint='b'*64,reason_code='data_changed',details_json='{}')
    first=repo.resolve_event(event.id).resolved_at
    assert repo.resolve_event(event.id).resolved_at==first


def test_database_fk_and_old_advice_table_unchanged(session,seeded_security):
    from sqlalchemy import inspect
    from sqlalchemy.exc import IntegrityError
    from app.db.models.research import ResearchReviewEvent
    from app.db.models import InvestmentAdviceCache
    repo=ResearchRepository(session);p=repo.create_project(security_id=seeded_security.id,question='x');other=repo.create_project(security_id=seeded_security.id,question='y')
    run=repo.append_run(project_id=p.id,project_version=1,status='completed',input_snapshot_json='{}',input_fingerprint='a'*64,output_json='{}',model_name='test',prompt_version='1')
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(ResearchReviewEvent(project_id=other.id,run_id=run.id,input_fingerprint='b'*64,reason_code='data_changed',details_json='{}'));session.flush()
    columns=inspect(session.get_bind()).get_columns(InvestmentAdviceCache.__tablename__)
    assert {c['name'] for c in columns}==set(InvestmentAdviceCache.model_fields)
    assert repo.get_run(run.id).project_id==p.id
