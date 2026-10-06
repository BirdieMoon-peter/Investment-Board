from copy import deepcopy
from datetime import date
from decimal import Decimal
import httpx
import pytest
from app.services.quant.service import QuantService
from app.services.quant.contracts import Advance, Acquire
from app.services.quant.acquisition import RawDailySource, AcquisitionError
from app.db.models import Holding, DataSource, QuoteSnapshot
from app.db.repositories.quant_repository import QuantConflict


def setup(service,data,strategy,costs):
    dataset=service.import_dataset(data);revision=service.create_strategy(strategy)
    return dataset,revision,{'strategy_id':revision.id,'dataset_id':dataset.id,'initial_cash':'10000','costs':costs}


def partial(data,count):
    result=deepcopy(data);result['calendar']=result['calendar'][:count];result['bars']=result['bars'][:count]
    return result


def test_forward_creation_cutoff_warmup_and_idempotence(session,quant_dataset,quant_strategy,quant_costs):
    current=[date(2025,1,5)]
    service=QuantService(session,clock=lambda:current[0])
    d,s,body=setup(service,partial(quant_dataset,3),quant_strategy,quant_costs)
    account=service.create_account(dict(body,name='Forward only'))
    original=service.repo.decode(account)
    assert original['activation_date']=='2025-01-05' and original['state']['cash']=='10000'
    early=service.import_dataset(partial(quant_dataset,5))
    account=service.advance_account(account.id,Advance(expected_version=1,dataset_id=early.id))
    assert service.repo.steps(account.id)==[] and service.repo.decode(account)['state']['positions']=={}
    current[0]=date(2025,1,8)
    later=service.import_dataset(partial(quant_dataset,8))
    account=service.advance_account(account.id,Advance(expected_version=2,dataset_id=later.id))
    steps=service.repo.steps(account.id)
    assert [step.session_date for step in steps]==['2025-01-06','2025-01-07','2025-01-08']
    assert service.repo.decode(steps[0])['fills'][0]['date']=='2025-01-06'
    snapshots=[step.payload_json for step in steps]
    version=account.version
    assert service.advance_account(account.id,Advance(expected_version=version,dataset_id=later.id)).version==version
    assert [step.payload_json for step in service.repo.steps(account.id)]==snapshots
    with pytest.raises(QuantConflict): service.advance_account(account.id,Advance(expected_version=1,dataset_id=later.id))


def test_prefix_future_and_revision_are_pinned(session,quant_dataset,quant_strategy,quant_costs):
    service=QuantService(session,clock=lambda:date(2025,1,5))
    d,s,body=setup(service,partial(quant_dataset,3),quant_strategy,quant_costs)
    a=service.create_account(dict(body,name='Pinned'))
    changed=partial(quant_dataset,5);changed['bars'][0]['close']='10.01'
    amended=service.import_dataset(changed)
    with pytest.raises(ValueError,match='prefix'): service.advance_account(a.id,Advance(expected_version=1,dataset_id=amended.id))
    future=service.import_dataset(partial(quant_dataset,8))
    with pytest.raises(ValueError,match='future'): service.advance_account(a.id,Advance(expected_version=1,dataset_id=future.id))
    updated=deepcopy(quant_strategy);updated['parent_id']=s.id;updated['parameters']['ma_window']=5
    service.create_strategy(updated)
    assert service.repo.decode(a)['strategy']['parameters']['ma_window']==2
    assert service.repo.steps(a.id)==[] and a.version==1


def test_run_saved_metrics_holdings_local_read_and_hypothesis(session,quant_dataset,quant_strategy,quant_costs,seeded_security):
    from app.db.repositories.research_repository import ResearchRepository
    service=QuantService(session)
    d,s,body=setup(service,quant_dataset,quant_strategy,quant_costs)
    run=service.create_run(body);frozen=run.payload_json
    holding=Holding(security_id=seeded_security.id,quantity=Decimal('123'),average_cost=Decimal('8'),notes='PRIVATE ACTUAL HOLDING')
    session.add(holding);session.commit()
    comparison=service.compare_holdings(run.id)
    assert comparison['missing_security_ids']==[seeded_security.id]
    assert comparison['rows'][0]['actual_weight'] is None
    assert holding.notes=='PRIVATE ACTUAL HOLDING' and holding.quantity==123
    project=ResearchRepository(session).create_project(security_id=seeded_security.id,question='Synthetic hypothesis',hypothesis='Saved statement')
    event=service.review(run.id,{'status':'invalidated','note':'Needs review','research_project_id':project.id,'hypothesis':'Experiment test'})
    assert service.repo.decode(event)['invalidation_flag'] is True
    assert service.repo.decode(event)['linked_project_snapshot']['hypothesis']=='Saved statement'
    assert run.payload_json==frozen


def test_unknown_coverage_ineligible_template_and_master_identity(session,quant_dataset,quant_strategy,quant_costs):
    service=QuantService(session)
    d,s,body=setup(service,quant_dataset,quant_strategy,quant_costs)
    run=service.repo.decode(service.create_run(body))
    assert run['assumptions']['return_label']=='research_price_return'
    bad=deepcopy(quant_dataset);bad['instruments'][0]['code']='999999'
    with pytest.raises(ValueError,match='identity'):service.import_dataset(bad)
    bad=deepcopy(quant_strategy);bad.update(template='etf_momentum',parameters={'lookback':2,'top_k':1,'rebalance_every':1})
    revision=service.create_strategy(bad)
    stock=deepcopy(quant_dataset);stock['instruments'][0]['instrument_type']='a_share'
    stockdata=service.import_dataset(stock)
    with pytest.raises(ValueError,match='ETF'):service.create_run(dict(body,strategy_id=revision.id,dataset_id=stockdata.id))


def test_acquisition_mock_raw_fqt0_normalization_and_disabled(session,quant_dataset):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'data':{'code':quant_dataset['instruments'][0]['code'],'klines':['2025-01-01,10,10,11,9,123,100','2025-01-02,11,11,12,10,100,200','2025-01-03,12,12,13,11,100,200']}})
    source=RawDailySource(httpx.MockTransport(handler));service=QuantService(session,source=source)
    body={'name':'Mock raw adapter','instruments':quant_dataset['instruments'],'start_date':'2025-01-01','end_date':'2025-01-03'}
    d=service.acquire_dataset(body);payload=service.repo.decode(d)
    assert calls[0].url.params['fqt']=='0' and payload['bars'][0]['volume']=='12300'
    assert payload['price_basis']=='raw' and payload['source']=='eastmoney_fqt0'
    session.add(DataSource(source_key='eastmoney',name='Eastmoney',enabled=False));session.commit()
    with pytest.raises(AcquisitionError,match='disabled'):service.acquire_dataset(body)
    assert len(calls)==1


def test_vendor_ignored_limit_is_explicitly_capped_and_invalid_identity(quant_dataset):
    from datetime import timedelta
    start=date(2023,1,1)
    rows=[f'{(start+timedelta(days=i)).isoformat()},10,10,11,9,100,100' for i in range(700)]
    body=Acquire(name='Mock bound',instruments=quant_dataset['instruments'],start_date=start,end_date=start+timedelta(days=699))
    source=RawDailySource(httpx.MockTransport(lambda r:httpx.Response(200,json={'data':{'code':'000001','klines':rows}})))
    dataset=source.acquire(body)
    assert len(dataset.calendar)==600 and len(dataset.bars)==600
    bad=RawDailySource(httpx.MockTransport(lambda r:httpx.Response(200,json={'data':{'code':'999999','klines':rows}})))
    with pytest.raises(AcquisitionError):bad.acquire(body)


def test_insufficient_history_rejected_without_zero_run(session,quant_dataset,quant_strategy,quant_costs):
    from app.db.models.quant import QuantRun
    service=QuantService(session)
    strategy=deepcopy(quant_strategy);strategy['parameters']['ma_window']=20
    d,s,body=setup(service,partial(quant_dataset,3),strategy,quant_costs)
    with pytest.raises(ValueError,match='insufficient'):service.create_run(body)
    assert service.repo.list(QuantRun)==[]


def test_paper_daily_and_batch_advance_keep_fixed_rebalance_clock(session,quant_dataset,quant_strategy,quant_costs):
    service=QuantService(session,clock=lambda:date(2025,1,3))
    quant_strategy['parameters']['rebalance_every']=5
    quant_dataset['bars'][4].update(open='9',close='9',high='10',low='8')
    d,s,body=setup(service,partial(quant_dataset,3),quant_strategy,quant_costs)
    batch=service.create_account(dict(body,name='Batch'));daily=service.create_account(dict(body,name='Daily'))
    assert service.repo.decode(batch)['state']['pending_signal'] is None
    service.clock=lambda:date(2025,1,8)
    final=service.import_dataset(partial(quant_dataset,8))
    service.advance_account(batch.id,Advance(expected_version=1,dataset_id=final.id))
    for count in range(4,9):
        next_data=service.import_dataset(partial(quant_dataset,count))
        daily=service.advance_account(daily.id,Advance(expected_version=daily.version,dataset_id=next_data.id))
    batch_steps=[service.repo.decode(step) for step in service.repo.steps(batch.id)]
    daily_steps=[service.repo.decode(step) for step in service.repo.steps(daily.id)]
    assert batch_steps==daily_steps
    assert all((date.fromisoformat(fill['signal_date'])-date(2025,1,1)).days%5==0 for step in batch_steps for fill in step['fills'])


def test_pre_activation_warmup_pending_obeys_phase_and_timestamp_offsets(session,quant_dataset,quant_strategy,quant_costs):
    service=QuantService(session,clock=lambda:date(2025,1,5));quant_strategy['parameters']['rebalance_every']=5
    d,s,body=setup(service,partial(quant_dataset,3),quant_strategy,quant_costs)
    account=service.create_account(dict(body,name='Warmup'))
    warmup=partial(quant_dataset,5);warmup['retrieved_at']='2025-02-01T08:00:00+08:00'
    later=service.import_dataset(warmup)
    account=service.advance_account(account.id,Advance(expected_version=1,dataset_id=later.id))
    assert service.repo.decode(account)['state']['pending_signal'] is None
    assert service.repo.steps(account.id)==[]


def test_holdout_without_scheduled_execution_is_unavailable(session,quant_dataset,quant_strategy,quant_costs):
    quant_strategy['parameters']['rebalance_every']=6
    service=QuantService(session);d,s,body=setup(service,quant_dataset,quant_strategy,quant_costs)
    result=service.repo.decode(service.create_run(dict(body,holdout_date=quant_dataset['calendar'][9])))
    assert result['robustness']['status']=='unavailable'
    assert 'holdout_insufficient_signal_history_robustness_unavailable' in result['warnings']
