"""Saved-only GETs; explicit import/acquire/experiment/paper/research actions."""
import json
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from app.api.dependencies import get_session
from app.db.models.quant import QuantDataset, QuantStrategy, QuantRun, QuantAccount
from app.db.repositories.quant_repository import QuantConflict
from app.services.quant.contracts import DatasetImport, StrategyCreate, RunCreate, AccountCreate, Advance, Review, Generate, Acquire, PARAMETERS
from app.services.quant.acquisition import SOURCE_CONTRACT, AcquisitionError
from app.services.quant.service import QuantService
from app.services.quant.research import generate

router = APIRouter()


def get_service(session: Session = Depends(get_session)):
    return QuantService(session)


def view(row):
    result = row.model_dump(mode='json')
    stamp = row.created_at
    result['created_at'] = (stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)).isoformat()
    payload = json.loads(result.pop('payload_json'))
    return {**payload, **result}


def apply(action):
    try:
        return action()
    except QuantConflict as exc:
        raise HTTPException(409, str(exc)) from None
    except AcquisitionError as exc:
        raise HTTPException(502, str(exc)) from None
    except KeyError:
        raise HTTPException(404, 'quant object or security not found') from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from None


@router.get('/templates')
def templates():
    labels = {'etf_momentum': 'ETF momentum rotation', 'ma_trend': 'Moving-average trend', 'etf_mean_reversion': 'ETF mean reversion'}
    return {'templates': [{'key': key, 'name': labels[key], 'parameters': {name: {'minimum': low, 'maximum': high, 'default': default} for name, (low, high, default) in spec.items()}, 'instrument_types': ['etf'] if key.startswith('etf_') else ['a_share', 'etf', 'lof']} for key, spec in PARAMETERS.items()], 'source_contract': SOURCE_CONTRACT, 'limits': {'max_instruments': 8, 'max_sessions': 600, 'max_json_bytes': 2000000, 'max_run_json_bytes': 32000000, 'max_account_json_bytes': 2000000, 'max_annotation_json_bytes': 2000000}, 'mode': 'research_backtest_and_forward_paper_only'}


def listing(service, model, limit, security_id=None):
    # A bounded page is explicit; no unbounded JSON scan on every GET.
    rows = service.repo.list(model, limit)
    result = []
    for row in rows:
        data = view(row)
        if security_id is not None:
            universe = data.get('universe', data.get('strategy', {}).get('universe', []))
            if security_id not in universe:
                continue
        if model is QuantDataset:
            data.pop('bars'); data['bar_count'] = len(service.repo.decode(row)['bars']); data['session_count'] = len(data['calendar']); data['coverage_start'] = data['calendar'][0]; data['coverage_end'] = data['calendar'][-1]; data.pop('calendar'); data.pop('actions')
        elif model is QuantRun:
            data = {k: data[k] for k in ('id', 'strategy_id', 'dataset_id', 'fingerprint', 'created_at', 'status', 'engine_version', 'strategy', 'warnings')}
            payload = service.repo.decode(row); data['metrics'] = payload['result']['metrics']; data['holdout_start'] = payload['holdout']['start_date']
        result.append(data)
    return result


@router.get('/datasets')
def datasets(limit: int = Query(20, ge=1, le=100), service=Depends(get_service)):
    return listing(service, QuantDataset, limit)


@router.post('/datasets/import', status_code=201)
def import_dataset(body: DatasetImport, service=Depends(get_service)):
    return apply(lambda: view(service.import_dataset(body)))


@router.post('/datasets/acquire', status_code=201)
def acquire_dataset(body: Acquire, service=Depends(get_service)):
    return apply(lambda: view(service.acquire_dataset(body)))


@router.get('/datasets/{identifier}')
def dataset(identifier: int, service=Depends(get_service)):
    return apply(lambda: view(service.repo.require(QuantDataset, identifier)))


@router.get('/strategies')
def strategies(limit: int = Query(20, ge=1, le=100), security_id: int | None = Query(None, gt=0), service=Depends(get_service)):
    return listing(service, QuantStrategy, limit, security_id)


@router.post('/strategies', status_code=201)
def create_strategy(body: StrategyCreate, service=Depends(get_service)):
    return apply(lambda: view(service.create_strategy(body)))


@router.get('/strategies/{identifier}')
def strategy(identifier: int, service=Depends(get_service)):
    return apply(lambda: view(service.repo.require(QuantStrategy, identifier)))


@router.get('/runs')
def runs(limit: int = Query(20, ge=1, le=100), security_id: int | None = Query(None, gt=0), service=Depends(get_service)):
    return listing(service, QuantRun, limit, security_id)


@router.post('/runs', status_code=201)
def create_run(body: RunCreate, service=Depends(get_service)):
    return apply(lambda: view(service.create_run(body)))


@router.get('/runs/{identifier}')
def run(identifier: int, service=Depends(get_service)):
    def action():
        row = service.repo.require(QuantRun, identifier)
        return {**view(row), 'annotations': [view(annotation) for annotation in service.repo.annotations(identifier)]}
    return apply(action)


@router.get('/runs/{identifier}/holdings-comparison')
def comparison(identifier: int, service=Depends(get_service)):
    return apply(lambda: service.compare_holdings(identifier))


@router.post('/runs/{identifier}/research', status_code=201)
def research(identifier: int, body: Generate, service=Depends(get_service)):
    return apply(lambda: view(generate(service, identifier, body.critique)))


@router.post('/runs/{identifier}/review', status_code=201)
def review(identifier: int, body: Review, service=Depends(get_service)):
    return apply(lambda: view(service.review(identifier, body)))


@router.get('/accounts')
def accounts(limit: int = Query(20, ge=1, le=100), service=Depends(get_service)):
    return listing(service, QuantAccount, limit)


@router.post('/accounts', status_code=201)
def create_account(body: AccountCreate, service=Depends(get_service)):
    return apply(lambda: view(service.create_account(body)))


@router.get('/accounts/{identifier}')
def account(identifier: int, service=Depends(get_service)):
    return apply(lambda: {**view(service.repo.require(QuantAccount, identifier)), 'steps': [view(step) for step in service.repo.steps(identifier)]})


@router.post('/accounts/{identifier}/advance')
def advance(identifier: int, body: Advance, service=Depends(get_service)):
    return apply(lambda: {**view(service.advance_account(identifier, body)), 'steps': [view(step) for step in service.repo.steps(identifier)]})


@router.get('/summary')
def summary(service=Depends(get_service)):
    accounts = listing(service, QuantAccount, 100); runs = listing(service, QuantRun, 100)
    return {'accounts': len(accounts), 'awaiting_future_data': sum(a['status'] == 'awaiting_future_data' for a in accounts), 'active_accounts': sum(a['status'] == 'active' for a in accounts), 'latest_account_session': max((a['state']['last_date'] for a in accounts), default=None), 'failed_runs': sum(r['status'] == 'failed' for r in runs), 'window': 'latest_100_saved_objects', 'mode': 'paper_only'}
