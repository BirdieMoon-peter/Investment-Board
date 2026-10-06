import pytest
from app.db.repositories.quant_repository import QuantRepository, QuantConflict, canonical


def test_immutable_dedupe_rollback_and_cas(session):
    repo = QuantRepository(session)
    raw = {'prices': ['1.00000000000000000001']}
    dataset = repo.dataset(raw)
    raw['prices'].append('9')
    assert repo.dataset({'prices': ['1.00000000000000000001']}).id == dataset.id
    assert repo.decode(dataset)['prices'] == ['1.00000000000000000001']
    strategy = repo.strategy({'name': 'sample'})
    run = repo.run(strategy.id, dataset.id, {'status': 'completed'})
    account = repo.account(strategy.id, dataset.id, {'cash': '100', 'last_date': '2026-01-01'})
    repo.advance(account.id, 1, dataset.id, {'cash': '101'}, [('2026-01-02', {'cash': '101'})], commit=False)
    session.rollback()
    session.refresh(account)
    assert account.version == 1 and repo.steps(account.id) == []
    repo.advance(account.id, 1, dataset.id, {'cash': '101'}, [('2026-01-02', {'cash': '101'})])
    with pytest.raises(QuantConflict): repo.advance(account.id, 1, dataset.id, {}, [])
    assert len(repo.steps(account.id)) == 1
    assert repo.decode(run)['status'] == 'completed'


@pytest.mark.parametrize('value', [{'x': float('nan')}, {'x': float('inf')}, {'x': 'x' * 2100000}])
def test_bounded_json(value):
    with pytest.raises(ValueError): canonical(value)


def test_foreign_keys_and_append_only(session):
    from app.db.models.quant import QuantStep
    from sqlalchemy.exc import IntegrityError
    repo = QuantRepository(session)
    with pytest.raises(ValueError): repo.run(999, 999, {})
    d = repo.dataset({}); s = repo.strategy({}); a = repo.account(s.id, d.id, {})
    repo.advance(a.id, 1, d.id, {}, [('2026-01-01', {})])
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(QuantStep(account_id=a.id, session_date='2026-01-01', payload_json='{}')); session.flush()
    assert len(repo.steps(a.id)) == 1


def test_step_failure_rolls_back_cas_and_preserves_caller_transaction(session):
    from sqlalchemy.exc import IntegrityError
    repo=QuantRepository(session);d=repo.dataset({});s=repo.strategy({});a=repo.account(s.id,d.id,{'cash':'100'})
    repo.advance(a.id,1,d.id,{'cash':'100'},[('2025-01-01',{})])
    with pytest.raises(IntegrityError):repo.advance(a.id,2,d.id,{'cash':'999'},[('2025-01-01',{})],commit=False)
    session.refresh(a)
    assert a.version==2 and repo.decode(a)['cash']=='100' and len(repo.steps(a.id))==1
    pending=repo.strategy({'name':'caller work'},commit=False)
    session.rollback()
    assert session.get(type(pending),pending.id) is None


def test_distinct_run_bound_retains_dataset_and_annotation_limits(session):
    from app.db.repositories.quant_repository import MAX_RUN_JSON_BYTES
    repo=QuantRepository(session);dataset=repo.dataset({});strategy=repo.strategy({})
    large={'large':'x'*2_100_000}
    with pytest.raises(ValueError):repo.dataset(large)
    run=repo.run(strategy.id,dataset.id,large)
    assert len(run.payload_json.encode())>2_000_000
    with pytest.raises(ValueError):repo.account(strategy.id,dataset.id,large)
    with pytest.raises(ValueError):repo.annotate(run.id,'review',large)
    with pytest.raises(ValueError):canonical({'large':'x'*MAX_RUN_JSON_BYTES},max_bytes=MAX_RUN_JSON_BYTES)
