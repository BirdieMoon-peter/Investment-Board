from copy import deepcopy
from decimal import Decimal as D
import pytest
from app.services.quant.engine import simulate, experiment, signal, initial_state


def test_next_open_is_causal_with_exact_cash(quant_dataset,quant_strategy,quant_costs):
    result=simulate(quant_dataset,quant_strategy,'10000',quant_costs)
    first=result['fills'][0]
    assert first['date']==quant_dataset['calendar'][2] and first['signal_date']==quant_dataset['calendar'][1]
    assert first['price']=='12' and first['quantity']=='800' and first['cash_after']=='400'
    changed=deepcopy(quant_dataset);changed['bars'][2].update(close='100',high='101')
    perturbed=simulate(changed,quant_strategy,'10000',quant_costs)
    assert perturbed['fills'][0]==first
    assert D(result['state']['cash'])>=0
    assert all(D(fill['quantity'])%100==0 for fill in result['fills'])


def test_volume_uses_previous_known_session_and_missing_halt(quant_dataset,quant_strategy,quant_costs):
    quant_dataset['bars'][1]['volume']='100'
    quant_dataset['bars'][2]['volume']='100000000'
    result=simulate(quant_dataset,quant_strategy,'10000',quant_costs)
    assert result['fills'][0]['quantity']=='100'
    assert any(r['reason']=='volume_cap_partial' for r in result['rejections'])
    data=deepcopy(quant_dataset);data['bars'][2]['volume']='0'
    assert not any(f['date']==data['calendar'][2] for f in simulate(data,quant_strategy,'10000',quant_costs)['fills'])
    data=deepcopy(quant_dataset)
    data['bars']=[b for b in data['bars'] if b['date']!=data['calendar'][3]]
    sparse=simulate(data,quant_strategy,'10000',quant_costs)
    assert any(r['reason']=='missing_open_bar' for r in sparse['rejections'])
    assert sparse['equity'][3]['stale_security_ids']


def test_limits_cost_tax_and_cash(quant_dataset,quant_strategy,quant_costs):
    quant_dataset['instruments'][0]['limit_pct']='0.05'
    limited=simulate(quant_dataset,quant_strategy,'10000',quant_costs)
    assert any(r['reason']=='one_sided_price_limit' for r in limited['rejections'])
    quant_dataset['instruments'][0]['limit_pct']=None
    costs=dict(quant_costs,minimum_commission='5',commission_rate='0.001',slippage='0.01',sell_tax='0.1')
    result=simulate(quant_dataset,quant_strategy,'10000',costs)
    assert all(D(f['cash_after'])>=0 for f in result['fills'])
    assert result['fills'][0]['price']=='12.12'
    # ETF sell tax is exempt even when the stock tax assumption is nonzero.
    state=initial_state('0',quant_dataset['calendar'][1]);state['positions']={'1':[{'quantity':'100','buy_date':quant_dataset['calendar'][0]}]};state['last_prices']={'1':'11'};state['pending_signal']={'date':quant_dataset['calendar'][1],'target_weights':{'1':'0'}}
    sold=simulate(quant_dataset,quant_strategy,'1000',costs,start_index=2,state=state)
    assert sold['fills'][0]['fee']=='5'
    quant_dataset['instruments'][0]['instrument_type']='a_share'
    taxed=simulate(quant_dataset,quant_strategy,'1000',costs,start_index=2,state=state)
    assert D(taxed['fills'][0]['fee'])==D('5')+D(taxed['fills'][0]['notional'])*D('0.1')


def test_settlement_guard_declared_actions_exactly_once_and_cashdate(quant_dataset,quant_strategy,quant_costs):
    day=quant_dataset['calendar'][2]
    state=initial_state('0',quant_dataset['calendar'][1]);state['positions']={'1':[{'quantity':'100','buy_date':day}]};state['last_prices']={'1':'11'};state['pending_signal']={'date':quant_dataset['calendar'][1],'target_weights':{'1':'0'}}
    result=simulate(quant_dataset,quant_strategy,'1000',quant_costs,start_index=2,state=state)
    assert not result['fills'] or result['fills'][0]['date']>day
    assert any(r['reason']=='settlement_lag_partial' for r in result['rejections'])
    state['positions']['1'][0]['buy_date']=quant_dataset['calendar'][0];state['pending_signal']=None
    quant_dataset['actions']=[{'security_id':1,'date':day,'kind':'split','value':'2','cash_available_date':None},{'security_id':1,'date':day,'kind':'cash_dividend','value':'0.5','cash_available_date':quant_dataset['calendar'][4]}]
    # Disable new buys so corporate action accounting can be checked directly.
    quant_strategy['parameters']['rebalance_every']=60
    action=simulate(quant_dataset,quant_strategy,'1000',quant_costs,start_index=2,state=state)
    assert action['actions'][1]['amount']=='50.0'
    assert D(action['equity'][0]['cash'])==0 and D(action['equity'][2]['cash'])==50
    assert len(action['state']['applied_actions'])==2
    assert sum(D(l['quantity']) for l in action['state']['positions']['1'])==200
    again=simulate(quant_dataset,quant_strategy,'1000',quant_costs,start_index=2,state=action['state'])
    assert again['actions']==[]


def test_known_split_and_dividend_do_not_create_raw_jump_signal(quant_dataset,quant_strategy):
    data=deepcopy(quant_dataset)
    for i,bar in enumerate(data['bars']):
        price='10' if i<2 else '5';bar.update(open=price,close=price,high=price,low=price)
    data['actions']=[{'security_id':1,'date':data['calendar'][2],'kind':'split','value':'2','cash_available_date':None}]
    assert signal(data,quant_strategy,2)['target_weights']['1']=='0'
    for i,bar in enumerate(data['bars']):
        price='10' if i<2 else '9';bar.update(open=price,close=price,high=price,low=price)
    data['actions']=[{'security_id':1,'date':data['calendar'][2],'kind':'cash_dividend','value':'1','cash_available_date':data['calendar'][2]}]
    assert signal(data,quant_strategy,2)['target_weights']['1']=='0'


def test_baseline_holdout_gross_robustness_and_metrics(quant_dataset,quant_strategy,quant_costs):
    costs=dict(quant_costs,minimum_commission='5',slippage='0.001')
    result=experiment(quant_dataset,quant_strategy,'10000',costs)
    assert len(result['baseline']['fills'])==1
    assert D(result['result']['metrics']['gross_return'])>=D(result['result']['metrics']['net_return'])
    assert result['holdout']['result']['equity'][0]['date']==result['holdout']['start_date']
    assert result['holdout']['result']['fills'][0]['cash_after']!=result['result']['fills'][0]['cash_after']
    assert result['robustness']['segment']=='same_chronological_holdout'
    assert result['robustness']['doubled_costs']['costs']['minimum_commission']=='10'
    assert result['result']['metrics']['annualized_sample_volatility'] is not None
    assert result['assumptions']['return_label']=='research_price_return'


def test_three_templates_and_no_future_action_signal(quant_dataset,quant_strategy,quant_costs):
    momentum=deepcopy(quant_strategy);momentum.update(template='etf_momentum',parameters={'lookback':2,'top_k':1,'rebalance_every':1})
    assert simulate(quant_dataset,momentum,'10000',quant_costs)['fills']
    mean=deepcopy(quant_strategy);mean.update(template='etf_mean_reversion',parameters={'ma_window':2,'rebalance_every':1,'entry_deviation':'-0.01','exit_deviation':'0'})
    assert simulate(quant_dataset,mean,'10000',quant_costs)['fills']==[]
    before=signal(quant_dataset,quant_strategy,1)
    quant_dataset['actions']=[{'security_id':1,'date':quant_dataset['calendar'][5],'kind':'split','value':'2','cash_available_date':None}]
    assert signal(quant_dataset,quant_strategy,1)==before


def test_signal_explanation_and_unfunded_sell_fee(quant_dataset,quant_strategy,quant_costs):
    explained=signal(quant_dataset,quant_strategy,1)['inputs'][0]
    assert explained['moving_average']=='10.5' and explained['sample_count']==2
    assert explained['window_end']==quant_dataset['calendar'][1] and explained['selected'] is True
    state=initial_state('0',quant_dataset['calendar'][1]);state['positions']={'1':[{'quantity':'100','buy_date':quant_dataset['calendar'][0]}]};state['last_prices']={'1':'0.001'};state['pending_signal']={'date':quant_dataset['calendar'][1],'target_weights':{'1':'0'}}
    for bar in quant_dataset['bars']:
        bar.update(open='0.001',close='0.001',high='0.001',low='0.001')
    costs=dict(quant_costs,minimum_commission='5')
    result=simulate(quant_dataset,quant_strategy,'1',costs,start_index=2,state=state)
    assert any(r['reason']=='insufficient_cash_for_sell_fee' for r in result['rejections'])
    assert D(result['state']['cash'])>=0


def test_holdout_seed_only_on_scheduled_close(quant_dataset,quant_strategy,quant_costs):
    quant_strategy['parameters']['rebalance_every']=5
    result=experiment(quant_dataset,quant_strategy,'10000',quant_costs,holdout_date=quant_dataset['calendar'][7])
    fills=result['holdout']['result']['fills']
    assert not any(fill['date']==quant_dataset['calendar'][7] for fill in fills)
    assert all(quant_dataset['calendar'].index(fill['signal_date'])%5==0 for fill in fills)


def test_missing_dividend_exdate_bar_preserves_nav_and_cash_availability(quant_dataset,quant_strategy,quant_costs):
    exdate=quant_dataset['calendar'][2];availability=quant_dataset['calendar'][3]
    quant_dataset['bars']=[b for b in quant_dataset['bars'] if b['date']!=exdate]
    quant_dataset['actions']=[{'security_id':1,'date':exdate,'kind':'cash_dividend','value':'1','cash_available_date':availability}]
    quant_strategy['parameters']['rebalance_every']=60
    state=initial_state('0',quant_dataset['calendar'][1]);state['positions']={'1':[{'quantity':'100','buy_date':quant_dataset['calendar'][0]}]};state['last_prices']={'1':'11'}
    result=simulate(quant_dataset,quant_strategy,'1100',quant_costs,start_index=2,state=state)
    assert D(result['equity'][0]['nav'])==1100 and D(result['equity'][0]['cash'])==0
    assert result['equity'][0]['stale_security_ids']==[1]
    assert result['steps'][0][1]['state']['last_prices']['1']=='10'
    assert D(result['equity'][1]['cash'])==100
    assert D(result['equity'][1]['nav'])==D(quant_dataset['bars'][2]['close'])*100+100


def test_saved_pending_signal_survives_seed_flag(quant_dataset,quant_strategy,quant_costs):
    state=initial_state('10000',quant_dataset['calendar'][2])
    state['pending_signal']=None
    result=simulate(quant_dataset,quant_strategy,'10000',quant_costs,start_index=3,state=state,seed_previous=True)
    assert not any(fill['date']==quant_dataset['calendar'][3] for fill in result['fills'])
