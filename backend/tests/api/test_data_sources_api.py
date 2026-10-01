from datetime import datetime
from sqlmodel import select
import pytest
from app.db.models.data_management import DataSource, SecurityDataset, IngestionRun


def test_catalog_is_independent_read_only_and_unknown(client, session):
    result = client.get('/api/data/sources')
    assert result.status_code == 200
    sources = result.json()['sources']
    assert {s['vendor_key'] for s in sources} == {'eastmoney','sina','netease','tencent','ifeng'}
    assert session.exec(select(DataSource)).all() == []
    for source in sources:
        assert source['runtime']['state'] == 'unknown'
        assert source['runtime']['recent_attempts'] == []
        assert client.get('/api/data/sources/' + source['vendor_key']).json() == source
        assert source['configurable'] == (source['vendor_key'] in {'eastmoney','sina','netease'})
    eastmoney = next(s for s in sources if s['vendor_key'] == 'eastmoney')
    assert 'fund_nav' not in eastmoney['managed_categories']
    assert client.get('/api/data/sources/absent').status_code == 404


@pytest.mark.parametrize('body', [{'enabled':1},{'enabled':'false'},{'enabled':None},{'enabled':False,'url':'https://secret'},{'enabled':True,'token':'secret'},{}])
def test_strict_mutation(client, body):
    assert client.put('/api/data/sources/eastmoney', json=body).status_code == 422


def test_toggle_persistence_and_preserved_metadata(client, session):
    source = DataSource(source_key='eastmoney',name='old',access_mode='public',url='https://legacy')
    session.add(source); session.commit()
    assert client.put('/api/data/sources/eastmoney',json={'enabled':False}).status_code == 200
    session.refresh(source)
    assert source.enabled is False and source.url == 'https://legacy'
    assert client.get('/api/data/sources/eastmoney').json()['enabled'] is False
    assert client.put('/api/data/sources/tencent',json={'enabled':False}).status_code == 422
    assert client.put('/api/data/sources/ifeng',json={'enabled':False}).status_code == 422
    assert client.put('/api/data/sources/absent',json={'enabled':False}).status_code == 404


@pytest.mark.parametrize('limit', ['0','101','bad'])
def test_history_limit_validation(client, limit):
    assert client.get('/api/data/sources?limit='+limit).status_code == 422


def test_runtime_alias_empty_and_internal_exclusion(client, session, seeded_security):
    dataset = SecurityDataset(security_id=seeded_security.id,category='quote_snapshot')
    session.add(dataset); session.commit()
    for key in ['eastmoney_intraday','aggregate:quote_snapshot']:
        source = DataSource(source_key=key,name=key); session.add(source); session.commit()
        for i in range(25):
            session.add(IngestionRun(dataset_id=dataset.id,source_id=source.id,status='succeeded',started_at=datetime(2026,1,1),finished_at=datetime(2026,1,1),records_received=0))
        session.commit()
    data = client.get('/api/data/sources/eastmoney?limit=3').json()
    attempts = data['runtime']['recent_attempts']
    assert len(attempts) == 3
    assert [a['id'] for a in attempts] == sorted([a['id'] for a in attempts],reverse=True)
    assert all(a['provider_key']=='eastmoney_intraday' and a['state']=='empty' for a in attempts)
    assert attempts[0]['started_at'].endswith(('Z', '+00:00'))
    assert attempts[0]['persisted_coverage'] == 'unknown'
    assert data['runtime']['state'] != 'healthy'
    assert data['runtime']['last_succeeded_attempt'] is not None


def test_get_no_network_or_writes_and_sql_bound(client, session, engine, monkeypatch):
    import httpx
    from sqlalchemy import event
    def forbidden(*args, **kwargs):
        raise AssertionError('GET must be local and read-only')
    monkeypatch.setattr(httpx.Client,'request',forbidden)
    monkeypatch.setattr(session,'add',forbidden)
    monkeypatch.setattr(session,'commit',forbidden)
    statements=[]
    def capture(conn,cursor,statement,parameters,context,executemany):
        if 'ingestion_runs' in statement:
            statements.append((statement,parameters))
    event.listen(engine,'before_cursor_execute',capture)
    try:
        # TestClient uses its own httpx request; call service to forbid provider transport.
        from app.services.data_source_management import DataSourceManagementService
        DataSourceManagementService(session).detail('eastmoney')
    finally:
        event.remove(engine,'before_cursor_execute',capture)
    assert statements and all('LIMIT' in sql for sql,_ in statements)
    assert any(20 in params for _,params in statements)


def test_new_app_reads_saved_setting(client,session):
    from app.main import create_app
    from app.api.dependencies import get_session
    from fastapi.testclient import TestClient
    client.put('/api/data/sources/sina',json={'enabled':False})
    app=create_app(); app.dependency_overrides[get_session]=lambda:session
    with TestClient(app) as new_client:
        assert new_client.get('/api/data/sources/sina').json()['enabled'] is False


def test_write_failure_is_controlled_and_atomic(client,session,monkeypatch):
    def fail():
        raise RuntimeError('password=topsecret https://private')
    monkeypatch.setattr(session,'commit',fail)
    response=client.put('/api/data/sources/eastmoney',json={'enabled':False})
    assert response.status_code==503
    assert 'topsecret' not in response.text
    assert session.exec(select(DataSource)).all()==[]


def test_old_success_independent_of_recent_limit(client,session,seeded_security):
    source=DataSource(source_key='sina_fund',name='sina'); session.add(source); session.commit()
    dataset=SecurityDataset(security_id=seeded_security.id,category='quote_snapshot'); session.add(dataset); session.commit()
    first=IngestionRun(dataset_id=dataset.id,source_id=source.id,status='succeeded',started_at=datetime(2025,1,1),records_received=2,records_written=1)
    session.add(first); session.commit()
    for i in range(22):
        session.add(IngestionRun(dataset_id=dataset.id,source_id=source.id,status='failed',started_at=datetime(2026,1,1),error_message='network_error'))
    session.commit()
    result=client.get('/api/data/sources/sina').json()['runtime']
    assert len(result['recent_attempts'])==20
    assert result['state']=='failed'
    assert result['last_succeeded_attempt']['id']==first.id
    assert result['last_succeeded_attempt']['persisted_coverage']=='attributed_write'

def test_actual_route_enforces_disabled_and_reenable(client,session,seeded_security,override_dependency):
    from unittest.mock import Mock
    from app.services.providers import AggregateAnnouncementProvider, AggregateNewsProvider, RawAnnouncementSourceAdapter
    from app.api.stocks import get_aggregate_announcement_provider, get_aggregate_news_provider, get_aggregate_price_history_provider, get_aggregate_financial_metrics_provider, get_aggregate_quote_snapshot_provider, get_aggregate_company_profile_provider
    forbidden=Mock(); forbidden.fetch.side_effect=AssertionError('disabled fetch called')
    announcement=AggregateAnnouncementProvider(raw_sources=[RawAnnouncementSourceAdapter('eastmoney',forbidden)])
    override_dependency(get_aggregate_announcement_provider,lambda:announcement)
    override_dependency(get_aggregate_news_provider,lambda:AggregateNewsProvider())
    for dependency in [get_aggregate_price_history_provider,get_aggregate_financial_metrics_provider,get_aggregate_quote_snapshot_provider,get_aggregate_company_profile_provider]:
        override_dependency(dependency,lambda:None)
    client.put('/api/data/sources/eastmoney',json={'enabled':False})
    response=client.post(f'/api/stocks/{seeded_security.id}/sync')
    assert response.status_code==200
    assert 'disabled' in ' '.join(response.json()['warnings'])
    forbidden.fetch.assert_not_called()
    assert session.exec(select(IngestionRun)).all()==[]
    forbidden.fetch.side_effect=None; forbidden.fetch.return_value=[]
    client.put('/api/data/sources/eastmoney',json={'enabled':True})
    assert session.exec(select(IngestionRun)).all()==[]
    response=client.post(f'/api/stocks/{seeded_security.id}/sync')
    assert response.status_code==200
    forbidden.fetch.assert_called_once()
    assert len(announcement.raw_sources)==1
    assert session.exec(select(IngestionRun)).first().records_received==0
