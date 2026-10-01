from types import SimpleNamespace
from unittest.mock import Mock
from sqlmodel import select
from app.api.stocks import get_stock_sync_service
from app.db.models.data_management import DataSource, IngestionRun, SecurityDataset
from app.services.data_source_management import DataSourceManagementService
from app.services.providers import AggregateAnnouncementProvider, AggregateNewsProvider, RawAnnouncementSourceAdapter, RawNewsSourceAdapter


def disable(session, *keys):
    for key in keys:
        session.add(DataSource(source_key=key,name=key,enabled=False))
    session.commit()


def test_policy_is_request_local_and_partial(session):
    disable(session,'eastmoney')
    shared = AggregateAnnouncementProvider(raw_sources=[RawAnnouncementSourceAdapter('eastmoney',Mock()),RawAnnouncementSourceAdapter('sina',Mock())])
    policy = DataSourceManagementService(session)
    local, disabled = policy.apply_policy(shared,'announcements')
    assert not disabled and [a.name for a in local.raw_sources] == ['sina']
    assert [a.name for a in shared.raw_sources] == ['eastmoney','sina']
    assert local.raw_sources[0] is not shared.raw_sources[1]
    policy.update('eastmoney',True)
    assert len(policy.apply_policy(shared,'announcements')[0].raw_sources)==2


def test_alias_disable_and_anonymous_compatibility(session):
    disable(session,'eastmoney_intraday')
    policy = DataSourceManagementService(session)
    provider = SimpleNamespace(raw_sources=[SimpleNamespace(name='eastmoney_intraday'),SimpleNamespace(name='eastmoney')])
    assert [a.name for a in policy.apply_policy(provider,'quote_snapshot')[0].raw_sources]==['eastmoney']
    custom = Mock(spec=['fetch_for_security'])
    assert policy.apply_policy(custom,'news') == (custom,False)
    anonymous = SimpleNamespace(raw_sources=[SimpleNamespace(name='custom')])
    assert not policy.apply_policy(anonymous,'news')[1]


def test_actual_dependency_all_disabled_preserves_no_attempts(session,seeded_security):
    disable(session,'eastmoney','sina','netease')
    forbidden = Mock(); forbidden.fetch.side_effect=AssertionError('disabled fetch called')
    announcements = AggregateAnnouncementProvider(raw_sources=[RawAnnouncementSourceAdapter('eastmoney',forbidden)])
    news = AggregateNewsProvider(raw_sources=[RawNewsSourceAdapter('sina',forbidden)])
    rest = [SimpleNamespace(raw_sources=[SimpleNamespace(name='eastmoney',provider=forbidden)],fetch_for_security=Mock(side_effect=AssertionError('disabled aggregate called'))) for _ in range(4)]
    service = get_stock_sync_service(session,announcements,news,*rest)
    result = service.sync_security(seeded_security.id,stock_code=seeded_security.code,market=seeded_security.market)
    assert set(result.category_outcomes.values()) == {'disabled'}
    assert result.warnings and result.synced_at is None
    assert session.exec(select(IngestionRun)).all()==[]
    assert session.exec(select(SecurityDataset)).all()==[]
    forbidden.fetch.assert_not_called()


def test_empty_aggregate_cannot_create_fake_success(session,seeded_security):
    service=get_stock_sync_service(session,AggregateAnnouncementProvider(),AggregateNewsProvider(),None,None,None,None)
    result=service.sync_security(seeded_security.id,stock_code=seeded_security.code,market=seeded_security.market,categories=['announcements','news'])
    assert session.exec(select(IngestionRun)).all()==[]
    assert set(result.category_outcomes.values())=={'disabled'}



def test_disabled_preserves_existing_dataset_freshness_and_runs(session,seeded_security):
    from datetime import UTC, datetime
    from app.db.models.data_management import DataQualityIssue
    disable(session,'eastmoney','sina','netease')
    dataset=SecurityDataset(security_id=seeded_security.id,category='announcements',fetched_at=datetime(2025,1,1,tzinfo=UTC))
    session.add(dataset); session.commit()
    issue=DataQualityIssue(dataset_id=dataset.id,code='failed_fetch',severity='warning',message='old evidence')
    session.add(issue); session.commit()
    source=session.exec(select(DataSource).where(DataSource.source_key=='eastmoney')).first()
    run=IngestionRun(dataset_id=dataset.id,source_id=source.id,status='failed',error_message='network_error')
    session.add(run); session.commit()
    provider=AggregateAnnouncementProvider(raw_sources=[RawAnnouncementSourceAdapter('eastmoney',Mock())])
    service=get_stock_sync_service(session,provider,AggregateNewsProvider(),None,None,None,None)
    result=service.sync_security(seeded_security.id,stock_code=seeded_security.code,market=seeded_security.market,categories=['announcements'])
    session.refresh(dataset); session.refresh(issue); session.refresh(source)
    assert result.category_outcomes=={'announcements':'disabled'}
    assert dataset.fetched_at.replace(tzinfo=UTC)==datetime(2025,1,1,tzinfo=UTC) and issue.resolved_at is None
    assert source.enabled is False
    assert [r.id for r in session.exec(select(IngestionRun)).all()]==[run.id]
