import pytest
from app.db.models import Holding, PriceHistory
from sqlmodel import select


def test_immutable_api_workflow_and_saved_only_get(client,session,quant_dataset,quant_strategy,quant_costs,monkeypatch):
    import app.services.quant.service as services
    import app.services.quant.research as research
    def forbidden(*args,**kwargs):raise AssertionError('GET must not call network/model')
    monkeypatch.setattr(services.RawDailySource,'acquire',forbidden)
    monkeypatch.setattr(research,'build_configured_provider',forbidden)
    templates=client.get('/api/quant/templates').json()
    assert len(templates['templates'])==3 and templates['source_contract']['native_request']['fqt']=='0'
    dataset=client.post('/api/quant/datasets/import',json=quant_dataset)
    assert dataset.status_code==201
    d=dataset.json();assert d['price_basis']=='raw'
    s=client.post('/api/quant/strategies',json=quant_strategy).json()
    response=client.post('/api/quant/runs',json={'strategy_id':s['id'],'dataset_id':d['id'],'initial_cash':'10000','costs':quant_costs})
    assert response.status_code==201
    run=response.json();assert run['result']['fills'][0]['signal_date']<run['result']['fills'][0]['date']
    assert client.get(f"/api/quant/runs/{run['id']}").json()['fingerprint']==run['fingerprint']
    assert client.get('/api/quant/datasets').json()[0]['bar_count']==12
    assert 'bars' not in client.get('/api/quant/datasets').json()[0]
    assert client.get('/api/quant/strategies').json()[0]['id']==s['id']
    assert client.get('/api/quant/runs').json()[0]['metrics']==run['result']['metrics']
    account=client.post('/api/quant/accounts',json={'name':'Forward','strategy_id':s['id'],'dataset_id':d['id'],'initial_cash':'10000','costs':quant_costs}).json()
    assert account['state']['positions']=={} and account['status']=='awaiting_future_data'
    same=client.post(f"/api/quant/accounts/{account['id']}/advance",json={'expected_version':1,'dataset_id':d['id']})
    assert same.status_code==200 and same.json()['version']==1
    assert client.get('/api/quant/summary').json()['awaiting_future_data']==1
    assert client.get(f"/api/quant/runs/{run['id']}/holdings-comparison").status_code==200
    assert list(session.exec(select(Holding)))==[] and list(session.exec(select(PriceHistory)))==[]


def test_errors_and_failed_frozen_research(client,quant_dataset,quant_strategy):
    d=client.post('/api/quant/datasets/import',json=quant_dataset).json();s=client.post('/api/quant/strategies',json=quant_strategy).json()
    assert client.get('/api/quant/runs/999').status_code==404
    assert client.get('/api/quant/runs?limit=101').status_code==422
    bad=dict(quant_dataset,price_basis='forward_adjusted')
    assert client.post('/api/quant/datasets/import',json=bad).status_code==422
    assert client.post('/api/quant/runs',json={'strategy_id':s['id'],'dataset_id':d['id'],'initial_cash':10000.0}).status_code==422


def test_insufficient_history_is_422_not_fake_zero_experiment(client,quant_dataset,quant_strategy):
    quant_strategy['parameters']['ma_window']=20
    d=client.post('/api/quant/datasets/import',json=quant_dataset).json();s=client.post('/api/quant/strategies',json=quant_strategy).json()
    response=client.post('/api/quant/runs',json={'strategy_id':s['id'],'dataset_id':d['id']})
    assert response.status_code==422 and 'insufficient' in response.json()['detail']
    assert client.get('/api/quant/runs').json()==[]


@pytest.mark.parametrize('precision_early', [False, True])
def test_full_eight_instrument_six_hundred_session_run_persists(client,session,quant_dataset,quant_costs,precision_early):
    from copy import deepcopy
    from datetime import date, timedelta
    from app.db.models import Security
    from app.db.models.quant import QuantRun
    data=deepcopy(quant_dataset);data['calendar']=[(date(2024,1,1)+timedelta(days=i)).isoformat() for i in range(600)]
    data['instruments']=[];data['bars']=[]
    for sid in range(1,9):
        if session.get(Security,sid) is None:
            session.add(Security(id=sid,market='SZ',code=f'{sid:06d}',name='Synthetic maximum-bound fixture',status='active'))
        data['instruments'].append({'security_id':sid,'market':'SZ','code':f'{sid:06d}','name':'Synthetic ETF assumption','instrument_type':'etf','lot_size':100,'settlement_lag':1,'limit_pct':None})
        for index,day in enumerate(data['calendar']):
            data['bars'].append({'security_id':sid,'date':day,'open':str(10+index),'close':str(10+index),'high':str(11+index),'low':str(9+index),'volume':'1000000'})
    if precision_early:
        for bar in data['bars']:
            bar['close']=bar['close']+'.'+'1234567890'*4
            bar['open']=bar['close'];bar['high']=bar['high']+'.9';bar['low']=bar['low']+'.0'
    session.commit()
    d=client.post('/api/quant/datasets/import',json=data);assert d.status_code==201
    strategy={'name':'Synthetic maximum only','template':'ma_trend','universe':list(range(1,9)),'parameters':{'ma_window':2,'rebalance_every':5},'max_exposure':'1'}
    s=client.post('/api/quant/strategies',json=strategy).json()
    request={'strategy_id':s['id'],'dataset_id':d.json()['id'],'initial_cash':'100000','costs':quant_costs}
    if precision_early:
        request['holdout_date']=data['calendar'][1]
    response=client.post('/api/quant/runs',json=request)
    assert response.status_code==201,response.text[:200]
    result=response.json();assert result['result']['metrics']['sample_count']==600
    row=session.get(QuantRun,result['id'])
    assert 2_000_000<len(row.payload_json.encode())<32_000_000
    if precision_early:
        assert len(row.payload_json.encode())>8_000_000
    assert client.get(f"/api/quant/runs/{result['id']}").json()['fingerprint']==result['fingerprint']
    assert client.get('/api/quant/templates').json()['limits']['max_json_bytes']==2_000_000
    assert client.get('/api/quant/templates').json()['limits']['max_run_json_bytes']==32_000_000
