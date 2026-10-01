from datetime import UTC, date, datetime, timedelta
from decimal import Decimal as D
import pytest
from sqlmodel import select
from app.db.models import Security, PriceHistory, QuoteSnapshot, Holding, FinancialMetrics
from app.db.models.data_management import DataSource, SecurityDataset, IngestionRun, DataQualityIssue, FundNavObservation


def metrics(response):
    return {r['key']:r for r in response.json()['metrics']}


def managed(session, security, category, *, source='eastmoney', basis='forward_adjusted', unit='CNY', frequency='daily', issues=()):
    provider = session.exec(select(DataSource).where(DataSource.source_key==source)).first()
    if not provider:
        provider=DataSource(source_key=source,name=source)
        session.add(provider); session.flush()
    dataset=SecurityDataset(security_id=security.id,category=category,source_id=provider.id,unit=unit,frequency=frequency,price_basis=basis,
        observation_at=datetime(2026,1,21,tzinfo=UTC),fetched_at=datetime(2026,1,22,tzinfo=UTC),coverage_start=date(2026,1,1),coverage_end=date(2026,1,21))
    session.add(dataset);session.flush()
    session.add(IngestionRun(dataset_id=dataset.id,source_id=provider.id,status='succeeded',records_written=253))
    for code in issues:
        session.add(DataQualityIssue(dataset_id=dataset.id,code=code,severity='warning',message=code))
    session.commit()
    return dataset


def history(session,security,count=253):
    for i in range(count):
        session.add(PriceHistory(security_id=security.id,trade_date=date(2025,1,1)+timedelta(days=i),open_price=i+1,high_price=i+1,low_price=i+1,close_price=i+1,volume=100,amount=100))
    session.commit()


def stock(session,security):
    security.industry='A股';session.add(security);session.commit()


def test_missing_and_empty_security(client,seeded_security):
    assert client.get('/api/indicators/securities/999999').status_code==404
    response=client.get(f'/api/indicators/securities/{seeded_security.id}')
    assert response.status_code==200
    assert all(r['value'] is None for r in response.json()['metrics'])


def test_managed_253_prices_return_precision_and_provenance(client,session,seeded_security):
    stock(session,seeded_security);history(session,seeded_security)
    managed(session,seeded_security,'price_history')
    response=client.get(f'/api/indicators/securities/{seeded_security.id}')
    output=metrics(response)
    assert D(output['price_return_252']['value'])==252
    assert output['price_return_252']['sample_count']==253
    assert output['price_return_252']['input_refs'][0]['source_key']=='eastmoney'
    assert output['price_return_252']['input_refs'][0]['freshness']=='stale'
    assert response.json()['data_context']['calendar']['verified'] is False


@pytest.mark.parametrize('issue',[None,'incomplete_price_refresh','mixed_source_write_attribution_unknown','price_basis_unknown'])
def test_legacy_or_mixed_not_certified(client,session,seeded_security,issue):
    stock(session,seeded_security);history(session,seeded_security)
    if issue:managed(session,seeded_security,'price_history',issues=[issue])
    assert metrics(client.get(f'/api/indicators/securities/{seeded_security.id}'))['price_return_252']['value'] is None


def test_index_context_cannot_value_cash_or_certify_basis(client,session,seeded_security):
    seeded_security.industry='指数';session.add(seeded_security);session.commit()
    history(session,seeded_security)
    managed(session,seeded_security,'price_history')
    managed(session,seeded_security,'quote_snapshot')
    session.add(QuoteSnapshot(security_id=seeded_security.id,last_price=10,change_amount=0,change_percent=0,snapshot_time=datetime(2026,1,21,tzinfo=UTC)))
    session.add(Holding(security_id=seeded_security.id,quantity=10,average_cost=5));session.commit()
    output=metrics(client.get(f'/api/indicators/securities/{seeded_security.id}'))
    assert output['price_return_252']['value'] is None
    response=client.get('/api/indicators/holdings').json()
    assert response['missing_price_security_ids']==[seeded_security.id]
    assert response['valuation_complete'] is False


def test_holdings_partial_denominator_and_zero_cost(client,session,seeded_security):
    stock(session,seeded_security)
    missing=Security(market='SH',code='600000',name='Missing',industry='A股')
    session.add(missing);session.flush()
    session.add(Holding(security_id=missing.id,quantity=1,average_cost=1))
    session.add(Holding(security_id=seeded_security.id,quantity=D('2.5'),average_cost=0))
    session.add(QuoteSnapshot(security_id=seeded_security.id,last_price=D('12.3456'),change_amount=0,change_percent=0,snapshot_time=datetime(2026,1,21,tzinfo=UTC)))
    session.commit();managed(session,seeded_security,'quote_snapshot',basis='unknown',frequency='snapshot')
    response=client.get('/api/indicators/holdings').json()
    assert response['valuation_complete'] is False
    assert response['denominator']=='known_valued_positions_only'
    assert response['missing_price_security_ids']==[missing.id]
    position=next(p for p in response['positions'] if p['security_id']==seeded_security.id)
    output={r['key']:r for r in position['metrics']}
    assert D(output['market_value']['value'])==D('30.86400')
    assert output['unrealized_pnl_percent']['value'] is None
    assert D(output['known_valued_weight']['value'])==1
    assert metrics(client.get('/api/indicators/holdings'))['concentration_hhi']['value']=='1'


def test_empty_holdings_no_invented_concentration(client):
    response=client.get('/api/indicators/holdings')
    assert response.status_code==200
    assert metrics(response)['known_market_value']['value']=='0'
    assert metrics(response)['concentration_hhi']['value'] is None


def test_fund_adjusted_close_and_cumulative_nav_do_not_make_premium_or_total_return(client,session,seeded_security):
    seeded_security.industry='ETF';session.add(seeded_security);session.commit();history(session,seeded_security)
    managed(session,seeded_security,'price_history')
    nav_dataset=managed(session,seeded_security,'fund_nav',source='eastmoney_fund_nav',basis='unknown',unit='CNY_per_fund_unit')
    session.add(FundNavObservation(security_id=seeded_security.id,source_id=nav_dataset.source_id,nav_date=date(2025,1,1)+timedelta(days=252),value=D(10)))
    session.commit()
    output=metrics(client.get(f'/api/indicators/securities/{seeded_security.id}'))
    assert output['fund_premium']['value'] is None
    assert output['total_return']['value'] is None
    assert output['tracking_error']['value'] is None
    assert output['revenue_yoy']['value'] is None


def test_financial_canonical_periods_source_percent_and_readonly(client,session,seeded_security):
    stock(session,seeded_security)
    managed(session,seeded_security,'financial_metrics',basis='unknown',frequency='quarterly')
    session.add_all([FinancialMetrics(security_id=seeded_security.id,report_period='2025年三季报',revenue=150,net_profit=15,roe=D('16.75')),FinancialMetrics(security_id=seeded_security.id,report_period='2024年三季报',revenue=100,net_profit=10)])
    session.commit()
    before=list(session.exec(select(IngestionRun.id)).all())
    output=metrics(client.get(f'/api/indicators/securities/{seeded_security.id}'))
    assert D(output['revenue_yoy']['value'])==D('.5')
    assert D(output['roe']['value'])==D('16.75')
    assert list(session.exec(select(IngestionRun.id)).all())==before


def test_unknown_source_contract_cannot_be_certified_by_metadata(client,session,seeded_security):
    stock(session,seeded_security);history(session,seeded_security)
    managed(session,seeded_security,'price_history',source='sina',basis='unadjusted')
    output=metrics(client.get(f'/api/indicators/securities/{seeded_security.id}'))
    assert output['price_return_252']['value'] is None


def test_quote_outside_successful_observation_cannot_value_holdings(client,session,seeded_security):
    stock(session,seeded_security)
    managed(session,seeded_security,'quote_snapshot',basis='unknown',frequency='intraday')
    session.add(Holding(security_id=seeded_security.id,quantity=1,average_cost=1))
    session.add(QuoteSnapshot(security_id=seeded_security.id,last_price=10,change_amount=0,change_percent=0,snapshot_time=datetime(2026,2,1,tzinfo=UTC)))
    session.commit()
    assert client.get('/api/indicators/holdings').json()['missing_price_security_ids']==[seeded_security.id]


def test_source_unit_context_mismatch_cannot_produce_cash_metrics(client,session,seeded_security):
    stock(session,seeded_security);history(session,seeded_security)
    managed(session,seeded_security,'price_history',unit='index_points')
    assert metrics(client.get(f'/api/indicators/securities/{seeded_security.id}'))['price_return_252']['value'] is None


def test_readonly_get_never_constructs_remote_sources(client,seeded_security,monkeypatch):
    import app.api.data_center as routes
    def forbidden():raise AssertionError('remote source constructed')
    monkeypatch.setattr(routes.eastmoney,'build_fund_nav_source',forbidden)
    monkeypatch.setattr(routes.eastmoney,'build_fund_profile_source',forbidden)
    assert client.get(f'/api/indicators/securities/{seeded_security.id}').status_code==200
    assert client.get('/api/indicators/holdings').status_code==200


def test_legacy_ambiguous_benchmark_is_disclosed_not_resolved(client,session,seeded_security):
    from app.db.models.data_management import SecurityResearchMetadata
    session.add(SecurityResearchMetadata(security_id=seeded_security.id,benchmark_code='000300'))
    session.commit()
    response=client.get(f'/api/indicators/securities/{seeded_security.id}')
    assert response.status_code==200
    assert 'benchmark_mapping_not_market_qualified' in metrics(response)['tracking_error']['warnings']
