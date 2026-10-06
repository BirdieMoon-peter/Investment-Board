from sqlmodel import select
from app.db.models import Security
from app.db.models.data_management import SecurityResearchMetadata, DataSource


def security(session, industry='银行'):
    row = Security(code='600000', market='SH', name='示例', industry=industry)
    session.add(row); session.commit(); session.refresh(row)
    return row


def test_read_unknown_has_no_mutation(client, session):
    row = security(session)
    response = client.get(f'/api/data/securities/{row.id}')
    assert response.status_code == 200
    data = response.json()
    assert data['categories']['price_history']['health'] == 'unknown'
    assert data['calendar']['verified'] is False
    assert not session.exec(select(DataSource)).all()
    assert client.get(f'/api/data/securities/{row.id}?limit=101').status_code == 422


def test_metadata_validation_and_partial_edit(client, session):
    row = security(session)
    url = f'/api/data/securities/{row.id}/metadata'
    assert client.put(url, json={'instrument_type':'etf', 'benchmark_code':'000300'}).status_code == 422
    assert client.put(url, json={'instrument_type':'etf', 'benchmark_code':'SH:000300','benchmark_name':'基准'}).status_code == 200
    assert client.put(url, json={'benchmark_name':None}).status_code == 200
    metadata = session.exec(select(SecurityResearchMetadata)).one()
    assert metadata.instrument_type == 'etf' and metadata.benchmark_code == 'SH:000300' and metadata.benchmark_name is None
    assert client.put(url, json={'manager':'fake'}).status_code == 422
    assert client.put('/api/data/securities/999/metadata', json={'instrument_type':'unknown'}).status_code == 404


def test_sync_validation(client, session):
    row = security(session)
    url = f'/api/data/securities/{row.id}/sync'
    assert client.post(url, json={'categories':['bogus']}).status_code == 422
    assert client.post(url, json={'categories':['news'], 'price_source':'sina'}).status_code == 422
    assert client.post(url, json={'categories':['price_history'], 'price_source':'bogus'}).status_code == 422
    assert client.post('/api/data/securities/999/sync', json={'categories':['news']}).status_code == 404

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
import pytest
from app.api.data_center import get_fund_nav_source, get_fund_profile_source
from app.api.stocks import get_aggregate_news_provider, get_aggregate_price_history_provider
from app.db.models.data_management import FundNavObservation, SecurityDataset, IngestionRun, DataQualityIssue
from app.db.repositories.data_management_repository import DataManagementRepository
from app.services.providers.eastmoney_fund_data import FundNavFetchResult, FundNavRow, FundProfileFetchResult, FundMetadata
from app.services.providers.fetch_provenance import SourceAttempt


class FundSource:
    def __init__(self, result):
        self.result, self.calls = result, []
    def fetch(self, code, market):
        self.calls.append((code,market))
        return self.result


def attempt(key, state='succeeded', count=1):
    return SourceAttempt(key,state,count,error_code='network_error' if state=='failed' else None,started_at=datetime.now(UTC),finished_at=datetime.now(UTC))


def nav_result(*, truncated=False, missing=False):
    return FundNavFetchResult(items=(FundNavRow(date.today(),'unit_nav',Decimal('1.2345678901234567890123456789')),
                                    FundNavRow(date.today(),'cumulative_nav',Decimal('2.345678901234567890123456789'))),
        attempts=(attempt('eastmoney_fund_nav'),),received_count=1,truncated=truncated,
        quality_issues=('missing_nav_value',) if missing else ())


def profile_result(kind='etf', **kwargs):
    return FundProfileFetchResult(item=FundMetadata(instrument_type=kind,**kwargs),attempts=(attempt('eastmoney_fund_profile'),),received_count=1)


def sources(override_dependency, nav=None, profile=None):
    nav = FundSource(nav or nav_result())
    profile = FundSource(profile or profile_result(manager='真实管理人'))
    override_dependency(get_fund_nav_source,lambda:nav)
    override_dependency(get_fund_profile_source,lambda:profile)
    return nav,profile


@pytest.mark.parametrize('industry',['银行','沪A','指数',None,'ETF联接','ETF Growth'])
def test_stock_index_unknown_never_query_colliding_fund(client, session, override_dependency, industry):
    row = security(session,industry)
    nav,profile = sources(override_dependency)
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_nav','fund_profile']})
    assert response.status_code == 200
    assert not nav.calls and not profile.calls
    assert response.json()['category_outcomes']['fund_nav']['outcome']=='unavailable'


def test_generic_fund_nav_only_does_not_hidden_profile(client, session, override_dependency):
    row=security(session,'基金'); nav,profile=sources(override_dependency)
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_nav']})
    assert response.status_code==200 and not nav.calls and not profile.calls


def test_profile_nav_resolution_exact_and_counts(client, session, override_dependency):
    row=security(session,'基金'); nav,profile=sources(override_dependency)
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_profile','fund_nav']})
    assert response.status_code==200
    assert len(nav.calls)==len(profile.calls)==1
    data=response.json()['data']; outcome=response.json()['category_outcomes']['fund_nav']
    assert outcome['received']==1 and outcome['written']==2
    assert outcome['received_count_unit']=='raw_nav_date_records'
    assert data['nav_observations'][0]['value']=='2.345678901234567890123456789'
    assert data['nav_observations'][0]['published_at'] is None
    dataset=data['categories']['fund_nav']
    assert dataset['coverage_start']==date.today().isoformat() and dataset['observation_at'].endswith('Z')
    assert dataset['health']=='healthy' and dataset['price_basis']=='unknown' and dataset['valuation_basis']=='official_nav'
    assert dataset['recent_attempts'][0]['records_received']==1 and dataset['recent_attempts'][0]['records_written']==2
    assert dataset['fetched_at'].endswith('Z')


@pytest.mark.parametrize('kind',['unknown'])
def test_feeder_profile_stays_unresolved_no_nav(client, session, override_dependency,kind):
    row=security(session,'基金'); nav,profile=sources(override_dependency,profile=profile_result(kind,manager='管理人'))
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_profile','fund_nav']})
    assert response.status_code==200 and profile.calls and not nav.calls
    assert response.json()['data']['metadata']['effective_instrument_type']=='unknown'


def test_manual_unknown_and_stock_override_fund_industry(client,session,override_dependency):
    row=security(session,'基金'); nav,profile=sources(override_dependency)
    client.put(f'/api/data/securities/{row.id}/metadata',json={'instrument_type':'unknown'})
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_profile','fund_nav']})
    assert response.status_code==200 and not nav.calls and not profile.calls
    client.put(f'/api/data/securities/{row.id}/metadata',json={'instrument_type':'stock'})
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_profile','fund_nav']})
    assert response.status_code==200 and not nav.calls and not profile.calls


def test_manual_preserved_and_optional_profile_merge(client,session,override_dependency):
    row=security(session,'ETF'); nav,profile=sources(override_dependency,profile=profile_result(manager='初始',management_fee=Decimal('.005'),fund_assets=Decimal('120000'),assets_as_of=date(2026,6,30),benchmark_name='原始'))
    url=f'/api/data/securities/{row.id}'
    assert client.post(url+'/sync',json={'categories':['fund_profile']}).status_code==200
    assert client.put(url+'/metadata',json={'instrument_type':'lof','benchmark_code':'SZ:399300','benchmark_name':'手动'}).status_code==200
    profile.result=profile_result('etf',manager='新管理人')
    data=client.post(url+'/sync',json={'categories':['fund_profile']}).json()['data']['metadata']
    assert data['instrument_type']=='lof' and data['benchmark_name']=='手动' and data['benchmark_code']=='SZ:399300'
    assert data['manager']=='新管理人' and data['management_fee']=='0.005' and data['fund_assets']=='120000' and data['assets_as_of']=='2026-06-30'
    assert data['source_key']=='manual' and data['provider_fields_source']=='eastmoney_fund_profile'
    assert data['as_of'] is None and data['publication_at'] is None


def test_truncated_and_failed_attempt_preserve_last_good(client,session,override_dependency):
    row=security(session,'ETF'); nav,profile=sources(override_dependency,nav=nav_result(truncated=True))
    url=f'/api/data/securities/{row.id}'
    first=client.post(url+'/sync',json={'categories':['fund_nav']}).json()['data']['categories']['fund_nav']
    assert first['health']=='partial'
    nav.result=FundNavFetchResult(attempts=(attempt('eastmoney_fund_nav','failed',2),),received_count=2)
    data=client.post(url+'/sync',json={'categories':['fund_nav']}).json()['data']
    latest=data['categories']['fund_nav']
    assert latest['fetched_at']==first['fetched_at'] and latest['observation_at']==first['observation_at']
    assert latest['latest_attempt']['status']=='failed' and latest['health']=='partial' and len(data['nav_observations'])==2
    nav.result=nav_result()
    latest=client.post(url+'/sync',json={'categories':['fund_nav']}).json()['data']['categories']['fund_nav']
    assert latest['health']=='healthy'
    assert not latest['unresolved_issues']


def test_disabled_alias_and_vendor_preserve_records_and_reenable(client,session,override_dependency):
    row=security(session,'ETF'); nav,profile=sources(override_dependency)
    url=f'/api/data/securities/{row.id}'
    first=client.post(url+'/sync',json={'categories':['fund_nav']}).json()['data']['categories']['fund_nav']
    for key in ('eastmoney','eastmoney_fund_nav'):
        source=session.exec(select(DataSource).where(DataSource.source_key==key)).first()
        if not source: source=DataSource(source_key=key,name=key)
        source.enabled=False;session.add(source);session.commit()
        calls=len(nav.calls)
        data=client.post(url+'/sync',json={'categories':['fund_nav']}).json()
        assert data['category_outcomes']['fund_nav']['outcome']=='disabled' and len(nav.calls)==calls
        assert data['data']['categories']['fund_nav']['fetched_at']==first['fetched_at']
        assert len(data['data']['categories']['fund_nav']['recent_attempts'])==1
        source.enabled=True;session.add(source);session.commit()
    assert client.post(url+'/sync',json={'categories':['fund_nav']}).json()['category_outcomes']['fund_nav']['outcome']=='succeeded'


def test_nav_savepoint_failure_is_atomic(client,session,override_dependency,monkeypatch):
    row=security(session,'ETF'); nav,profile=sources(override_dependency)
    original=DataManagementRepository.upsert_nav
    calls=[]
    def failing(repo,item,**kwargs):
        calls.append(item)
        if len(calls)==2: raise ValueError('private provider text')
        return original(repo,item,**kwargs)
    monkeypatch.setattr(DataManagementRepository,'upsert_nav',failing)
    data=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_nav']}).json()
    assert data['category_outcomes']['fund_nav']['outcome']=='failed_persist'
    assert not session.exec(select(FundNavObservation)).all()
    assert data['data']['categories']['fund_nav']['fetched_at'] is None
    assert data['data']['categories']['fund_nav']['latest_attempt']['error_code']=='invalid_data'


def test_metadata_failed_commit_atomic_503(client,session,monkeypatch):
    row=security(session)
    monkeypatch.setattr(session,'commit',lambda: (_ for _ in ()).throw(RuntimeError('secret')))
    assert client.put(f'/api/data/securities/{row.id}/metadata',json={'instrument_type':'etf'}).status_code==503
    assert not session.exec(select(SecurityResearchMetadata)).all()
    assert not session.exec(select(DataSource)).all()


def test_bounded_get_old_unknown_and_stale_estimate(client,session):
    row=security(session,'ETF')
    source=DataSource(source_key='eastmoney_fund_nav',name='Eastmoney');session.add(source);session.flush()
    dataset=SecurityDataset(security_id=row.id,category='fund_nav',source_id=source.id,fetched_at=datetime.now(UTC),observation_at=datetime.now(UTC)-timedelta(days=30),frequency='daily')
    session.add(dataset);session.flush()
    url=f'/api/data/securities/{row.id}'
    assert client.get(url).json()['categories']['fund_nav']['health']=='unknown'
    for i in range(25):
        session.add(IngestionRun(dataset_id=dataset.id,source_id=source.id,status='succeeded',records_received=1,records_written=2))
        session.add(DataQualityIssue(dataset_id=dataset.id,code='field_unknown',severity='warning',message='field unknown'))
    session.commit()
    data=client.get(url+'?limit=5').json()['categories']['fund_nav']
    assert len(data['recent_attempts'])==len(data['unresolved_issues'])==5
    assert data['freshness']=='stale' and data['health']=='partial'
    assert 'no_calendar' in data['freshness_basis']

from app.services.providers.stock_data_providers import AggregatePriceHistoryProvider, RawPriceHistorySourceAdapter
from app.services.providers.aggregate_providers import AggregateNewsProvider
from app.services.providers.news_provider import RawNewsSourceAdapter
from app.services.providers.raw_types import RawPriceBar, RawNewsItem


class RawSource:
    def __init__(self,rows):
        self.rows,self.calls=rows,[]
    def fetch(self,*args,**kwargs):
        self.calls.append((args,kwargs));return self.rows


def price_sources(override_dependency):
    bar=RawPriceBar(datetime.now(UTC).date(),*(Decimal(v) for v in ['10','12','8','11','100','1000']))
    raw={key:RawSource([bar]) for key in ('sina','eastmoney','netease')}
    provider=AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter(key,raw[key],price_basis='forward_adjusted' if key=='eastmoney' else 'unadjusted',volume_unit='shares',amount_available=True) for key in raw],fallback_enabled=False)
    override_dependency(get_aggregate_price_history_provider,lambda:provider)
    return raw,provider


def test_history_default_prefers_known_basis_then_retains_source(client,session,override_dependency):
    row=security(session,'沪A');raw,provider=price_sources(override_dependency);sources(override_dependency)
    url=f'/api/data/securities/{row.id}/sync'
    data=client.post(url,json={'categories':['price_history']}).json()
    assert data['category_outcomes']['price_history']['written']==1
    assert raw['eastmoney'].calls and not raw['sina'].calls
    assert [a.name for a in provider.raw_sources]==['sina','eastmoney','netease']
    assert data['data']['categories']['price_history']['price_basis']=='forward_adjusted'
    raw['eastmoney'].calls.clear()
    assert client.post(url,json={'categories':['price_history'],'price_source':'sina'}).status_code==200
    assert raw['sina'].calls and not raw['eastmoney'].calls
    raw['sina'].calls.clear()
    assert client.post(url,json={'categories':['price_history']}).status_code==200
    assert raw['sina'].calls and not raw['eastmoney'].calls


def test_explicit_disabled_history_no_fallback_or_new_attempt(client,session,override_dependency):
    row=security(session,'沪A');raw,provider=price_sources(override_dependency);sources(override_dependency)
    session.add(DataSource(source_key='sina',name='Sina',enabled=False));session.commit()
    data=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history'],'price_source':'sina'}).json()
    assert data['category_outcomes']['price_history']['outcome']=='disabled' and data['warnings']
    assert all(not s.calls for s in raw.values())
    assert not session.exec(select(IngestionRun)).all()
    assert data['data']['categories']['price_history']['health']=='unknown'


def test_fund_news_only_actual_news_and_no_unrelated_calls(client,session,override_dependency):
    row=security(session,'基金');nav,profile=sources(override_dependency)
    raw=RawSource([RawNewsItem('示例基金新闻',datetime.now(UTC),'eastmoney')])
    override_dependency(get_aggregate_news_provider,lambda:AggregateNewsProvider(raw_sources=[RawNewsSourceAdapter('eastmoney',raw)]))
    prices,provider=price_sources(override_dependency)
    data=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['news']}).json()
    assert data['category_outcomes']['news']['written']==1
    assert raw.calls and not nav.calls and not profile.calls and all(not s.calls for s in prices.values())
    assert data['data']['categories']['news']['latest_attempt']['provider_key']=='eastmoney'


def test_fund_announcements_never_company_substitute(client,session,override_dependency):
    row=security(session,'ETF');nav,profile=sources(override_dependency)
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['announcements']})
    assert response.status_code==200
    assert response.json()['category_outcomes']['announcements']['outcome']=='not_applicable'
    assert not session.exec(select(IngestionRun)).all() and not nav.calls and not profile.calls


def test_new_asset_without_date_cannot_inherit_old_valuation_date(client,session,override_dependency):
    row=security(session,'ETF');nav,profile=sources(override_dependency,profile=profile_result(fund_assets=Decimal('100'),assets_as_of=date(2026,6,30)))
    url=f'/api/data/securities/{row.id}/sync'
    client.post(url,json={'categories':['fund_profile']})
    profile.result=profile_result(fund_assets=Decimal('200'))
    data=client.post(url,json={'categories':['fund_profile']}).json()['data']['metadata']
    assert data['fund_assets']=='200' and data['assets_as_of'] is None


def test_current_unresolved_profile_does_not_authorize_nav_from_old_type(client,session,override_dependency):
    row=security(session,'基金');nav,profile=sources(override_dependency)
    url=f'/api/data/securities/{row.id}/sync'
    client.post(url,json={'categories':['fund_profile']})
    profile.result=profile_result('unknown',manager='同号未明确类型')
    data=client.post(url,json={'categories':['fund_profile','fund_nav']}).json()
    assert not nav.calls and data['category_outcomes']['fund_nav']['outcome']=='unavailable'
    assert data['data']['metadata']['instrument_type']=='etf'


def test_complete_profile_resolves_missing_warning(client,session,override_dependency):
    row=security(session,'ETF');nav,profile=sources(override_dependency)
    url=f'/api/data/securities/{row.id}/sync'
    client.post(url,json={'categories':['fund_profile']})
    profile.result=profile_result(manager='管理人',management_fee=Decimal('.005'),custody_fee=Decimal('.001'),fund_assets=Decimal('100'),assets_as_of=date.today(),benchmark_name='真实基准')
    data=client.post(url,json={'categories':['fund_profile']}).json()['data']['categories']['fund_profile']
    assert data['health']=='healthy' and not data['unresolved_issues']
    assert data['observation_at'] is None and data['frequency']=='on_request'


def test_outer_fund_commit_failure_rolls_back_all_nav(client,session,override_dependency,monkeypatch):
    row=security(session,'ETF');sources(override_dependency)
    monkeypatch.setattr(session,'commit',lambda:(_ for _ in ()).throw(RuntimeError('secret')))
    data=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['fund_nav']}).json()
    assert data['category_outcomes']['fund_nav']['outcome']=='failed_persist'
    assert not session.exec(select(FundNavObservation)).all() and not session.exec(select(IngestionRun)).all() and not session.exec(select(SecurityDataset)).all()


def test_get_service_forbids_network_and_mutations_with_sql_bounds(session,engine,monkeypatch):
    import httpx
    from sqlalchemy import event
    from app.services.data_center import SecurityDataCenterService
    row=security(session,'ETF')
    source=DataSource(source_key='eastmoney_fund_nav',name='Eastmoney');session.add(source);session.flush()
    dataset=SecurityDataset(security_id=row.id,category='fund_nav',source_id=source.id,fetched_at=datetime.now(UTC))
    session.add(dataset);session.flush()
    session.add(IngestionRun(dataset_id=dataset.id,source_id=source.id,status='succeeded',records_written=1));session.commit()
    def forbidden(*args,**kwargs):raise AssertionError('read must not mutate or call provider')
    monkeypatch.setattr(httpx.Client,'request',forbidden)
    monkeypatch.setattr(session,'add',forbidden)
    monkeypatch.setattr(session,'commit',forbidden)
    statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany):
        if any(table in statement for table in ('ingestion_runs','data_quality_issues','fund_nav_observations')):
            statements.append((statement,parameters))
    event.listen(engine,'before_cursor_execute',capture)
    try:
        data=SecurityDataCenterService(session).detail(row.id,5)
    finally:event.remove(engine,'before_cursor_execute',capture)
    assert data['categories']['fund_nav']['health']=='healthy'
    assert statements and all('LIMIT' in sql for sql,params in statements)
    assert any(5 in params for sql,params in statements) and any(100 in params for sql,params in statements)


def test_failed_retry_remains_separate_from_fresh_last_good(client,session,override_dependency):
    row=security(session,'ETF');nav,profile=sources(override_dependency)
    url=f'/api/data/securities/{row.id}/sync'
    initial=client.post(url,json={'categories':['fund_nav']}).json()['data']['categories']['fund_nav']
    nav.result=FundNavFetchResult(attempts=(attempt('eastmoney_fund_nav','failed'),))
    data=client.post(url,json={'categories':['fund_nav']}).json()['data']['categories']['fund_nav']
    assert data['health']=='healthy' and data['freshness']=='within_estimated_threshold'
    assert data['fetched_at']==initial['fetched_at'] and data['latest_attempt']['status']=='failed'


def test_health_does_not_hide_old_quality_behind_attempt_issue_limit(client,session,override_dependency):
    row=security(session,'ETF');nav,profile=sources(override_dependency,nav=nav_result(truncated=True))
    url=f'/api/data/securities/{row.id}'
    client.post(url+'/sync',json={'categories':['fund_nav']})
    nav.result=FundNavFetchResult(attempts=(attempt('eastmoney_fund_nav','failed'),))
    client.post(url+'/sync',json={'categories':['fund_nav']})
    data=client.get(url+'?limit=1').json()['categories']['fund_nav']
    assert len(data['unresolved_issues'])==1 and data['unresolved_issues'][0]['code']=='failed_fetch'
    assert data['health']=='partial'


def test_unresolved_profile_blocks_later_nav_only_until_profile_repair(client,session,override_dependency):
    row=security(session,'基金');nav,profile=sources(override_dependency)
    url=f'/api/data/securities/{row.id}/sync'
    client.post(url,json={'categories':['fund_profile']})
    profile.result=profile_result('unknown',manager='未明确类型')
    client.post(url,json={'categories':['fund_profile']})
    data=client.post(url,json={'categories':['fund_nav']}).json()
    assert not nav.calls and data['category_outcomes']['fund_nav']['outcome']=='unavailable'
    assert data['data']['metadata']['instrument_type']=='etf' and data['data']['metadata']['effective_instrument_type']=='unknown'
    profile.result=profile_result('etf',manager='管理人')
    data=client.post(url,json={'categories':['fund_profile','fund_nav']}).json()
    assert len(nav.calls)==1 and data['category_outcomes']['fund_nav']['outcome']=='succeeded'


@pytest.mark.parametrize('industry', ['ETF','LOF','ETF基金','LOF基金','基金'])
def test_unknown_profile_blocks_fresh_lookup_hint_until_positive_repair(client, session, override_dependency, industry):
    row = security(session, industry)
    nav, profile = sources(override_dependency, profile=profile_result('unknown', manager='类型未确认'))
    url = f'/api/data/securities/{row.id}/sync'
    assert not session.exec(select(SecurityResearchMetadata)).all()
    first = client.post(url, json={'categories':['fund_profile']}).json()
    assert first['data']['metadata']['effective_instrument_type'] == 'unknown'
    assert first['data']['metadata']['classification_origin'] == 'fund_profile_unresolved'
    retry = client.post(url, json={'categories':['fund_nav']}).json()
    assert retry['category_outcomes']['fund_nav']['outcome'] == 'unavailable'
    assert not nav.calls
    assert not session.exec(select(FundNavObservation)).all()
    profile.result = profile_result('lof' if 'LOF' in industry else 'etf', manager='管理人')
    repaired = client.post(url, json={'categories':['fund_profile','fund_nav']}).json()
    assert repaired['category_outcomes']['fund_nav']['outcome'] == 'succeeded'
    assert len(nav.calls) == 1


def test_manual_override_supersedes_fresh_unresolved_profile(client, session, override_dependency):
    row = security(session, 'ETF')
    nav, profile = sources(override_dependency, profile=profile_result('unknown', manager='类型未确认'))
    url = f'/api/data/securities/{row.id}'
    client.post(url+'/sync', json={'categories':['fund_profile']})
    assert client.put(url+'/metadata', json={'instrument_type':'lof'}).status_code == 200
    result = client.post(url+'/sync', json={'categories':['fund_profile','fund_nav']}).json()
    assert result['data']['metadata']['effective_instrument_type'] == 'lof'
    assert result['data']['metadata']['classification_origin'] == 'manual'
    assert result['category_outcomes']['fund_nav']['outcome'] == 'succeeded'
    assert len(nav.calls) == 1


def test_first_benchmark_overlay_snapshots_effective_unknown_not_old_provider_etf(client, session, override_dependency):
    row = security(session,'基金'); nav, profile = sources(override_dependency)
    url = f'/api/data/securities/{row.id}'
    client.post(url+'/sync', json={'categories':['fund_profile']})
    profile.result = profile_result('unknown', manager='未确认类型')
    client.post(url+'/sync', json={'categories':['fund_profile']})
    overlay = client.put(url+'/metadata', json={'benchmark_code':'SH:000300','benchmark_name':'仅改基准'}).json()
    assert overlay['metadata']['instrument_type'] == 'unknown'
    assert overlay['metadata']['effective_instrument_type'] == 'unknown'
    retry = client.post(url+'/sync', json={'categories':['fund_nav']}).json()
    assert retry['category_outcomes']['fund_nav']['outcome'] == 'unavailable' and not nav.calls
    # An explicitly chosen type remains an authorized override.
    client.put(url+'/metadata', json={'instrument_type':'lof'})
    assert client.post(url+'/sync', json={'categories':['fund_nav']}).json()['category_outcomes']['fund_nav']['outcome'] == 'succeeded'
    assert len(nav.calls) == 1


@pytest.mark.parametrize('industry,expected',[('ETF','etf'),('LOF','lof'),('沪A','stock'),('基金','unknown')])
def test_fresh_benchmark_overlay_snapshots_current_label(client,session,industry,expected):
    row=security(session,industry)
    result=client.put(f'/api/data/securities/{row.id}/metadata',json={'benchmark_name':'基准'}).json()
    assert result['metadata']['instrument_type']==expected and result['metadata']['effective_instrument_type']==expected


def test_existing_manual_type_survives_benchmark_only_edit(client,session,override_dependency):
    row=security(session,'基金');nav,profile=sources(override_dependency)
    url=f'/api/data/securities/{row.id}'
    client.put(url+'/metadata',json={'instrument_type':'lof'})
    profile.result=profile_result('unknown',manager='未确认类型')
    client.post(url+'/sync',json={'categories':['fund_profile']})
    result=client.put(url+'/metadata',json={'benchmark_name':'仅改基准'}).json()
    assert result['metadata']['instrument_type']=='lof' and result['metadata']['effective_instrument_type']=='lof'


class OpaquePriceProvider:
    def __init__(self):self.calls=[]
    def fetch_for_security(self,*args,**kwargs):
        self.calls.append((args,kwargs));return []


@pytest.mark.parametrize('selected',['eastmoney','sina','netease'])
def test_explicit_source_does_not_invoke_opaque_custom_provider(client,session,override_dependency,selected):
    row=security(session,'沪A');sources(override_dependency)
    custom=OpaquePriceProvider()
    override_dependency(get_aggregate_price_history_provider,lambda:custom)
    response=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history'],'price_source':selected})
    assert response.status_code==200
    result=response.json()
    assert not custom.calls
    assert result['category_outcomes']['price_history']['outcome']=='unavailable'
    assert result['category_outcomes']['price_history']['reason']
    assert not session.exec(select(IngestionRun)).all() and not session.exec(select(SecurityDataset)).all()


def test_default_opaque_custom_provider_compatibility_preserved(client,session,override_dependency):
    row=security(session,'沪A');sources(override_dependency)
    custom=OpaquePriceProvider()
    override_dependency(get_aggregate_price_history_provider,lambda:custom)
    result=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history']}).json()
    assert len(custom.calls)==1 and result['category_outcomes']['price_history']['outcome']=='empty'


def test_explicit_unavailable_custom_source_keeps_other_category_work(client,session,override_dependency):
    row=security(session,'沪A');sources(override_dependency)
    custom=OpaquePriceProvider()
    override_dependency(get_aggregate_price_history_provider,lambda:custom)
    raw=RawSource([RawNewsItem('实际新闻',datetime.now(UTC),'eastmoney')])
    override_dependency(get_aggregate_news_provider,lambda:AggregateNewsProvider(raw_sources=[RawNewsSourceAdapter('eastmoney',raw)]))
    result=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history','news'],'price_source':'eastmoney'}).json()
    assert not custom.calls and raw.calls
    assert result['category_outcomes']['price_history']['outcome']=='unavailable'
    assert result['category_outcomes']['news']['outcome']=='succeeded' and result['category_outcomes']['news']['written']==1
    assert not session.exec(select(SecurityDataset).where(SecurityDataset.category=='price_history')).all()


def test_explicit_source_with_no_matching_raw_adapter_is_unavailable(client,session,override_dependency):
    row=security(session,'沪A');sources(override_dependency)
    raw=RawSource([])
    provider=AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('sina',raw)])
    override_dependency(get_aggregate_price_history_provider,lambda:provider)
    result=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history'],'price_source':'eastmoney'}).json()
    assert result['category_outcomes']['price_history']['outcome']=='unavailable' and not raw.calls
    assert not session.exec(select(IngestionRun)).all()


def test_opaque_explicit_source_preserves_old_freshness_and_attempts(client,session,override_dependency):
    row=security(session,'沪A');sources(override_dependency);price_sources(override_dependency)
    url=f'/api/data/securities/{row.id}/sync'
    initial=client.post(url,json={'categories':['price_history']}).json()['data']['categories']['price_history']
    opaque=OpaquePriceProvider()
    override_dependency(get_aggregate_price_history_provider,lambda:opaque)
    result=client.post(url,json={'categories':['price_history'],'price_source':'eastmoney'}).json()
    current=result['data']['categories']['price_history']
    assert result['category_outcomes']['price_history']['outcome']=='unavailable' and not opaque.calls
    assert current['fetched_at']==initial['fetched_at'] and current['recent_attempts']==initial['recent_attempts']

from app.api.stocks import get_aggregate_quote_snapshot_provider
from app.services.providers.stock_data_providers import AggregateQuoteSnapshotProvider, RawQuoteSnapshotSourceAdapter
from app.services.providers.raw_types import RawQuoteSnapshot


@pytest.mark.parametrize('industry,manual_type',[('指数',None),('沪A','index')])
def test_resolved_index_units_basis_and_volume_context_are_truthful(client,session,override_dependency,industry,manual_type):
    row=security(session,industry);sources(override_dependency)
    prices,provider=price_sources(override_dependency)
    quote=RawSource(RawQuoteSnapshot(Decimal('11'),Decimal('1'),Decimal('10'),datetime.now(UTC)))
    override_dependency(get_aggregate_quote_snapshot_provider,lambda:AggregateQuoteSnapshotProvider(raw_sources=[RawQuoteSnapshotSourceAdapter('eastmoney',quote)]))
    url=f'/api/data/securities/{row.id}'
    if manual_type:client.put(url+'/metadata',json={'instrument_type':manual_type})
    result=client.post(url+'/sync',json={'categories':['price_history','quote_snapshot']}).json()
    for category in ('price_history','quote_snapshot'):
        data=result['data']['categories'][category]
        assert data['unit']=='index_points' and data['price_basis']=='unknown'
    codes={issue['code'] for issue in result['data']['categories']['price_history']['unresolved_issues']}
    assert {'index_volume_context_unverified','volume_unit_unknown','price_basis_unknown'} <= codes
    assert result['data']['categories']['price_history']['health']=='partial'
    assert provider.raw_sources[1].price_basis=='forward_adjusted' and provider.raw_sources[1].volume_unit=='shares'


@pytest.mark.parametrize('industry',['沪A','ETF'])
def test_stock_and_etf_currency_basis_semantics_unchanged(client,session,override_dependency,industry):
    row=security(session,industry);sources(override_dependency);price_sources(override_dependency)
    result=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history']}).json()
    data=result['data']['categories']['price_history']
    assert data['unit']=='CNY' and data['price_basis']=='forward_adjusted'
    assert not any(issue['code'].startswith('index_') for issue in data['unresolved_issues'])


def test_index_unsupported_source_units_unknown_with_explicit_issue(client,session,override_dependency):
    row=security(session,'指数');sources(override_dependency)
    bar=RawPriceBar(datetime.now(UTC).date(),*(Decimal(v) for v in ['10','12','8','11','100','1000']))
    raw=RawSource([bar])
    override_dependency(get_aggregate_price_history_provider,lambda:AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('custom_unknown',raw,price_basis='forward_adjusted',volume_unit='shares')]))
    result=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history']}).json()['data']['categories']['price_history']
    assert result['unit'] is None and result['price_basis']=='unknown'
    assert 'unit_unverified' in {issue['code'] for issue in result['unresolved_issues']}


def test_index_native_volume_is_not_coerced_as_equity_lots(client,session,override_dependency):
    from app.db.models import PriceHistory
    row=security(session,'指数');sources(override_dependency)
    bar=RawPriceBar(datetime.now(UTC).date(),*(Decimal(v) for v in ['10','12','8','11','100','1000']))
    raw=RawSource([bar])
    provider=AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('eastmoney',raw,price_basis='forward_adjusted',volume_unit='lots')])
    override_dependency(get_aggregate_price_history_provider,lambda:provider)
    result=client.post(f'/api/data/securities/{row.id}/sync',json={'categories':['price_history']}).json()
    assert result['category_outcomes']['price_history']['written']==1
    stored=session.exec(select(PriceHistory).where(PriceHistory.security_id==row.id)).one()
    assert stored.volume==Decimal('100') and stored.close_price==Decimal('11')
    assert provider.raw_sources[0].volume_unit=='lots'
    assert 'index_volume_context_unverified' in {issue['code'] for issue in result['data']['categories']['price_history']['unresolved_issues']}


def test_index_get_legacy_currency_basis_is_derived_unknown_without_mutation(client,session,monkeypatch):
    row=security(session,'指数')
    source=DataSource(source_key='eastmoney',name='Eastmoney');session.add(source);session.flush()
    dataset=SecurityDataset(security_id=row.id,category='price_history',source_id=source.id,unit='CNY',price_basis='forward_adjusted',fetched_at=datetime.now(UTC))
    session.add(dataset);session.flush()
    session.add(IngestionRun(dataset_id=dataset.id,source_id=source.id,status='succeeded',records_written=1));session.commit()
    def forbidden(*args,**kwargs):raise AssertionError('GET must not persist derived disclosures')
    monkeypatch.setattr(session,'add',forbidden);monkeypatch.setattr(session,'commit',forbidden)
    data=client.get(f'/api/data/securities/{row.id}').json()['categories']['price_history']
    assert data['unit'] is None and data['price_basis']=='unknown' and data['health']=='partial'
    assert data['context_disclosures'] and data['unit_provenance']=='unverified_index_context'
    session.refresh(dataset)
    assert dataset.unit=='CNY' and dataset.price_basis=='forward_adjusted'
    assert not session.exec(select(DataQualityIssue)).all()
