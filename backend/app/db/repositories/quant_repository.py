"""Immutable inserts and transaction-owned optimistic paper-account advancement."""
import hashlib
import json
from datetime import date
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from app.db.models.quant import QuantDataset, QuantStrategy, QuantRun, QuantAccount, QuantStep, QuantAnnotation
from app.db.models.research import ResearchProject

MAX_JSON_BYTES = 2_000_000
MAX_RUN_JSON_BYTES = 32_000_000
MAX_ACCOUNT_JSON_BYTES = 2_000_000
MAX_ANNOTATION_JSON_BYTES = 2_000_000


class QuantConflict(ValueError):
    pass


def canonical(value, *, max_bytes=MAX_JSON_BYTES):
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        raise ValueError('invalid finite JSON object') from None
    if not isinstance(value, dict) or len(raw.encode()) > max_bytes:
        raise ValueError(f'JSON object exceeds {max_bytes}-byte limit')
    return raw


def fingerprint(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


class QuantRepository:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def decode(row):
        return json.loads(row.payload_json)

    def _outer(self):
        connection = self.session.connection()
        if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')

    def _insert(self, row, commit=True):
        self._outer()
        with self.session.begin_nested():
            self.session.add(row)
            self.session.flush()
        if commit:
            self.session.commit()
        self.session.refresh(row)
        return row

    def require(self, model, identifier):
        row = self.session.get(model, identifier)
        if row is None:
            raise KeyError('quant object not found')
        return row

    def list(self, model, limit=20):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError('limit must be 1..100')
        return list(self.session.exec(select(model).order_by(model.id.desc()).limit(limit)))

    def dataset(self, payload, commit=True):
        raw = canonical(payload); digest = fingerprint(raw)
        statement = select(QuantDataset).where(QuantDataset.fingerprint == digest)
        existing = self.session.exec(statement).first()
        if existing:
            return existing
        try:
            return self._insert(QuantDataset(fingerprint=digest, payload_json=raw), commit)
        except IntegrityError:
            existing = self.session.exec(statement).first()
            if existing is None:
                raise
            return existing

    def strategy(self, payload, parent_id=None, commit=True):
        if parent_id is not None:
            self.require(QuantStrategy, parent_id)
        raw = canonical(payload)
        return self._insert(QuantStrategy(parent_id=parent_id, payload_json=raw, fingerprint=fingerprint(raw)), commit)

    def run(self, strategy_id, dataset_id, payload, commit=True):
        if self.session.get(QuantStrategy, strategy_id) is None or self.session.get(QuantDataset, dataset_id) is None:
            raise ValueError('run references unavailable objects')
        raw = canonical(payload, max_bytes=MAX_RUN_JSON_BYTES)
        return self._insert(QuantRun(strategy_id=strategy_id, dataset_id=dataset_id, payload_json=raw, fingerprint=fingerprint(raw)), commit)

    def account(self, strategy_id, dataset_id, payload, commit=True):
        self.require(QuantStrategy, strategy_id); self.require(QuantDataset, dataset_id)
        return self._insert(QuantAccount(strategy_id=strategy_id, dataset_id=dataset_id, payload_json=canonical(payload, max_bytes=MAX_ACCOUNT_JSON_BYTES)), commit)

    def steps(self, account_id):
        # A compatible cumulative snapshot is bounded to 600 observed sessions.
        return list(self.session.exec(select(QuantStep).where(QuantStep.account_id == account_id).order_by(QuantStep.session_date)))

    def advance(self, account_id, expected_version, dataset_id, state, steps, commit=True):
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
            raise ValueError('invalid expected version')
        self.require(QuantDataset, dataset_id)
        raw = canonical(state, max_bytes=MAX_ACCOUNT_JSON_BYTES)
        prepared = []
        for day, payload in steps:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError('invalid session date')
            prepared.append(QuantStep(account_id=account_id, session_date=day, payload_json=canonical(payload)))
        self._outer()
        with self.session.begin_nested():
            changed = self.session.execute(update(QuantAccount).where(QuantAccount.id == account_id, QuantAccount.version == expected_version).values(version=expected_version + 1, dataset_id=dataset_id, payload_json=raw).execution_options(synchronize_session=False))
            if changed.rowcount != 1:
                raise QuantConflict('paper account version conflict')
            self.session.add_all(prepared)
            self.session.flush()
        if commit:
            self.session.commit()
        row = self.require(QuantAccount, account_id)
        self.session.refresh(row)
        return row

    def annotate(self, run_id, kind, payload, research_project_id=None, commit=True):
        self.require(QuantRun, run_id)
        if kind not in {'review', 'research'}:
            raise ValueError('invalid annotation kind')
        if research_project_id is not None:
            self.require(ResearchProject, research_project_id)
        return self._insert(QuantAnnotation(run_id=run_id, kind=kind, research_project_id=research_project_id, payload_json=canonical(payload, max_bytes=MAX_ANNOTATION_JSON_BYTES)), commit)

    def annotations(self, run_id):
        return list(self.session.exec(select(QuantAnnotation).where(QuantAnnotation.run_id == run_id).order_by(QuantAnnotation.id.desc()).limit(100)))
