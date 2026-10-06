from copy import deepcopy
from datetime import timedelta
import pytest
from app.services.quant.contracts import DatasetImport, StrategyCreate, today


def test_exact_raw_and_canonical_order(quant_dataset):
    quant_dataset['bars'][0]['close'] = '10.000000000000000001'
    result = DatasetImport.model_validate(quant_dataset)
    assert result.model_dump(mode='json')['bars'][0]['close'] == '10.000000000000000001'


@pytest.mark.parametrize('field,value', [('price_basis','forward_adjusted'),('currency','index_points'),('volume_unit','lots')])
def test_rejects_nonraw_units(quant_dataset,field,value):
    quant_dataset[field] = value
    with pytest.raises(ValueError): DatasetImport.model_validate(quant_dataset)


@pytest.mark.parametrize('field,value', [('open','NaN'),('volume','Infinity'),('open',10.0),('low','20'),('volume','-1')])
def test_rejects_ohlc_nonfinite_and_floats(quant_dataset,field,value):
    quant_dataset['bars'][0][field] = value
    with pytest.raises(ValueError): DatasetImport.model_validate(quant_dataset)


def test_future_duplicate_calendar_actions_rules(quant_dataset):
    for change in [lambda d:d['bars'].append(deepcopy(d['bars'][0])), lambda d:d['calendar'].reverse(), lambda d:d['bars'][0].update(date=(today()+timedelta(days=1)).isoformat()), lambda d:d['instruments'][0].update(lot_size=0), lambda d:d.update(retrieved_at='2025-01-01T00:00:00'), lambda d:d.update(actions=[{'security_id':1,'date':d['calendar'][0],'kind':'cash_dividend','value':'1'}])]:
        data=deepcopy(quant_dataset);change(data)
        with pytest.raises(ValueError): DatasetImport.model_validate(data)


def test_template_parameter_bounds_no_code(quant_strategy):
    result=StrategyCreate.model_validate(quant_strategy)
    assert result.parameters['ma_window']==2
    for key,value in [('code','print(1)'),('ma_window',True),('ma_window',1)]:
        data=deepcopy(quant_strategy);data['parameters'][key]=value
        with pytest.raises(ValueError): StrategyCreate.model_validate(data)
