from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.db.models import PriceHistory, Security
from app.db.models.data_management import SecurityDataset
from app.db.repositories.data_management_repository import DataManagementRepository
from app.db.repositories.price_history_repository import PriceHistoryRepository
from app.services.providers.raw_types import RawPriceBar
from app.services.providers.stock_data_providers import AggregatePriceHistoryProvider, RawPriceHistorySourceAdapter
from app.services.stock_sync import StockSyncService


def bar(day=1, close='10'):
    return PriceHistory(security_id=1, trade_date=date(2026, 1, day), open_price=Decimal('10'), high_price=Decimal('12'), low_price=Decimal('8'), close_price=Decimal(close), volume=Decimal('100'), amount=Decimal('1000'))


class Provider:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0
    def fetch_for_security(self, *args, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class Repository:
    def get_latest_published_at(self, *args):
        raise AssertionError('unrelated read')
    def upsert_many(self, items, **kwargs):
        return items


def service(provider, repository=None, recorder=None):
    unrelated = Provider(error=AssertionError('unrelated fetch'))
    kwargs = dict(announcement_provider=unrelated, news_provider=unrelated,
                  announcement_repository=Repository(), news_repository=Repository(),
                  price_history_provider=provider, price_history_repository=repository or Repository())
    if recorder is not None:
        kwargs['ingestion_recorder'] = recorder
    return StockSyncService(**kwargs), unrelated


def test_selective_and_invalid_categories_never_call_unrelated_sources():
    provider = Provider([bar()])
    sync, unrelated = service(provider)
    with pytest.raises(ValueError):
        sync.sync_security(1, stock_code='000001', market='SZ', categories=['bad', 'price_history'])
    assert provider.calls == unrelated.calls == 0
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.price_bars_upserted == 1
    assert provider.calls == 1 and unrelated.calls == 0


def test_price_failover_reports_all_attempts_and_safe_error():
    class Raw:
        def __init__(self, items=None, error=None):
            self.items, self.error = items, error
        def fetch(self, *args, **kwargs):
            if self.error:
                raise self.error
            return self.items
    raw = RawPriceBar(date(2026, 1, 1), *(Decimal('10'), Decimal('12'), Decimal('8'), Decimal('11'), Decimal('100'), Decimal('1000')))
    result = AggregatePriceHistoryProvider(raw_sources=[
        RawPriceHistorySourceAdapter('bad', Raw(error=RuntimeError('secret token=https://user:pass@host'))),
        RawPriceHistorySourceAdapter('empty', Raw([])),
        RawPriceHistorySourceAdapter('ok', Raw([raw])),
    ]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert [(x.source_key, x.state, x.count) for x in result.attempts] == [('bad', 'failed', 0), ('empty', 'empty', 0), ('ok', 'succeeded', 1)]
    assert result.source_key == 'ok' and result.price_basis == 'unknown'
    assert result.attempts[0].error_code == 'ingestion_error'
    assert 'secret' not in repr(result)


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Security(id=1, code='000001', market='SZ', name='Test'))
        session.commit()
        yield session


def test_empty_and_failure_refresh_leave_prior_freshness_and_prices(session):
    from app.services.data_ingestion import DataIngestionRecorder
    from app.services.providers.fetch_provenance import SourceAttempt
    from app.services.providers.stock_data_providers import PriceHistoryFetchResult
    dm = DataManagementRepository(session)
    recorder = DataIngestionRecorder(dm)
    repository = PriceHistoryRepository(session)
    repository.upsert_many([bar()])
    old = datetime(2026, 1, 2, tzinfo=UTC)
    dm.upsert_dataset(SecurityDataset(security_id=1, category='price_history', fetched_at=old))
    provider = Provider(PriceHistoryFetchResult([], [], attempts=(SourceAttempt('empty', 'empty', 0),)))
    sync, _ = service(provider, repository, recorder)
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.category_outcomes['price_history'] == 'empty'
    assert dm.get_dataset(1, 'price_history').fetched_at.replace(tzinfo=UTC) == old
    provider.error = RuntimeError('password=secret')
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.category_outcomes['price_history'] == 'failed_fetch'
    assert len(repository.list_recent_by_security_id(1)) == 1
    assert dm.get_dataset(1, 'price_history').fetched_at.replace(tzinfo=UTC) == old
    assert 'secret' not in repr(dm.list_runs(dm.get_dataset(1, 'price_history').id))


def test_news_reports_mixed_sources_without_fake_single_selection():
    from app.services.providers.aggregate_providers import AggregateNewsProvider
    from app.services.providers.news_provider import NewsSourceAdapter
    from app.db.models import NewsItem
    news = NewsItem(security_id=1, title='a', published_at=datetime(2026, 1, 1), source='a')
    result = AggregateNewsProvider(sources=[NewsSourceAdapter('a', Provider([news])), NewsSourceAdapter('b', Provider([news]))]).fetch_for_security(1)
    assert result.source_key is None
    assert [a.count for a in result.attempts] == [1, 1]


def price_result(items, source='eastmoney', basis='forward_adjusted'):
    from app.services.providers.stock_data_providers import PriceHistoryFetchResult
    from app.services.providers.fetch_provenance import SourceAttempt
    return PriceHistoryFetchResult(items, [], attempts=(SourceAttempt(source, 'succeeded', len(items)),), source_key=source, price_basis=basis, unit='CNY', frequency='daily', volume_unit='shares')


def test_clean_first_fetch_and_complete_refresh_prove_stored_basis(session):
    from app.services.data_ingestion import DataIngestionRecorder
    dm = DataManagementRepository(session)
    repository = PriceHistoryRepository(session)
    provider = Provider(price_result([bar(1), bar(2)]))
    sync, _ = service(provider, repository, DataIngestionRecorder(dm))
    sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    dataset = dm.get_dataset(1, 'price_history')
    assert dataset.price_basis == 'forward_adjusted'
    assert dataset.coverage_start == date(2026, 1, 1)
    provider.result = price_result([bar(1, '9'), bar(2, '9'), bar(3, '9')])
    sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert [r.close_price for r in repository.list_recent_by_security_id(1)] == [Decimal('9')] * 3
    assert dm.get_dataset(1, 'price_history').price_basis == 'forward_adjusted'


@pytest.mark.parametrize('old_basis,source,new_basis', [('unknown','eastmoney','forward_adjusted'), ('forward_adjusted','eastmoney','forward_adjusted'), ('forward_adjusted','sina','unknown')])
def test_insufficient_subset_cannot_change_basis_or_freshness(session, old_basis, source, new_basis):
    from app.services.data_ingestion import DataIngestionRecorder
    repository = PriceHistoryRepository(session)
    repository.upsert_many([bar(1), bar(2)])
    dm = DataManagementRepository(session)
    old = datetime(2026, 1, 4, tzinfo=UTC)
    dm.upsert_dataset(SecurityDataset(security_id=1, category='price_history', price_basis=old_basis, fetched_at=old))
    sync, _ = service(Provider(price_result([bar(2, '9')], source, new_basis)), repository, DataIngestionRecorder(dm))
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.price_bars_upserted == 0
    assert [r.close_price for r in repository.list_recent_by_security_id(1)] == [Decimal('10')] * 2
    dataset = dm.get_dataset(1, 'price_history')
    assert dataset.price_basis == old_basis and dataset.fetched_at.replace(tzinfo=UTC) == old
    assert 'incomplete_price_refresh' in [x.code for x in dm.list_quality_issues(dataset.id)]


def test_complete_fetch_can_replace_legacy_unknown_basis(session):
    from app.services.data_ingestion import DataIngestionRecorder
    repository = PriceHistoryRepository(session)
    repository.upsert_many([bar()])
    dm = DataManagementRepository(session)
    sync, _ = service(Provider(price_result([bar(1, '9'), bar(2, '9')])), repository, DataIngestionRecorder(dm))
    sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert dm.get_dataset(1, 'price_history').price_basis == 'forward_adjusted'
    assert repository.list_recent_by_security_id(1)[-1].close_price == Decimal('9')


def test_persistence_failure_rolls_back_rows_and_keeps_success_metadata(session):
    from app.services.data_ingestion import DataIngestionRecorder
    class FailsAfterWrite(PriceHistoryRepository):
        def upsert_many(self, items, **kwargs):
            super().upsert_many(items, **kwargs)
            raise RuntimeError('secret password')
    repository = PriceHistoryRepository(session)
    repository.upsert_many([bar()])
    dm = DataManagementRepository(session)
    old = datetime(2026, 1, 2, tzinfo=UTC)
    dm.upsert_dataset(SecurityDataset(security_id=1, category='price_history', fetched_at=old))
    sync, _ = service(Provider(price_result([bar(1, '9'), bar(2, '9')])), FailsAfterWrite(session), DataIngestionRecorder(dm))
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.category_outcomes['price_history'] == 'failed_persist'
    assert len(repository.list_recent_by_security_id(1)) == 1
    assert repository.list_recent_by_security_id(1)[0].close_price == Decimal('10')
    dataset = dm.get_dataset(1, 'price_history')
    assert dataset.fetched_at.replace(tzinfo=UTC) == old
    runs = dm.list_runs(dataset.id)
    assert runs[0].status == 'failed' and runs[0].records_written == 0
    assert 'secret' not in repr(runs) + repr(result)


def test_source_units_normalized_and_missing_amount_disclosed():
    import httpx
    from app.services.providers.eastmoney_price_history import EastmoneyPriceHistorySource
    from app.services.providers.sina_price_history import SinaPriceHistorySource
    em = EastmoneyPriceHistorySource(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'data':{'klines':['2026-01-01,10,11,12,8,123,1000']}})))
    result = AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('eastmoney', em)]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.items[0].volume == Decimal('12300')
    assert result.volume_unit == 'shares' and result.price_basis == 'forward_adjusted'
    sina = SinaPriceHistorySource(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[dict(day='2026-01-01', open='10', close='11', high='12', low='8', volume='12300')])))
    result = AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('sina', sina)]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.items[0].volume == Decimal('12300')
    assert result.amount_available is False and result.price_basis == 'unknown'


@pytest.mark.parametrize('mutation', ['nan', 'negative', 'ohlc', 'duplicate', 'order'])
def test_invalid_price_series_rejected_before_persist(session, mutation):
    from app.services.data_ingestion import DataIngestionRecorder
    items = [bar(1), bar(2)]
    if mutation == 'nan': items[0].close_price = Decimal('NaN')
    elif mutation == 'negative': items[0].volume = Decimal('-1')
    elif mutation == 'ohlc': items[0].high_price = Decimal('9')
    elif mutation == 'duplicate': items = [bar(1), bar(1, '9')]
    else: items = [bar(2), bar(1), bar(3)]
    dm = DataManagementRepository(session)
    repo = PriceHistoryRepository(session)
    sync, _ = service(Provider(price_result(items)), repo, DataIngestionRecorder(dm))
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.price_bars_upserted == 0
    assert repo.list_recent_by_security_id(1) == []
    assert dm.get_dataset(1, 'price_history').fetched_at is None


def test_aggregate_write_count_not_falsely_attributed(session):
    from app.services.data_ingestion import DataIngestionRecorder
    from app.services.providers.fetch_provenance import SourceAttempt
    fetch = SimpleNamespace(items=[bar()], attempts=(SourceAttempt('a','succeeded',1), SourceAttempt('b','succeeded',1)))
    dm = DataManagementRepository(session)
    recorder = DataIngestionRecorder(dm)
    dataset = recorder.record(1, 'financial_metrics', outcome='partial', fetch=fetch, persisted=[bar()])
    session.commit()
    runs = dm.list_runs(dataset.id)
    sources = {dm.session.get(__import__('app.db.models.data_management', fromlist=['DataSource']).DataSource, r.source_id).source_key: r for r in runs}
    assert sources['a'].records_written == sources['b'].records_written == 0
    assert sources['aggregate:financial_metrics'].records_written == 1
    assert dm.get_dataset(1, 'financial_metrics').source_id is None


def test_skipped_category_does_not_invent_successful_source_attempt(session):
    from app.services.data_ingestion import DataIngestionRecorder
    dm = DataManagementRepository(session)
    dataset = DataIngestionRecorder(dm).record(1, 'company_profile', outcome='not_applicable')
    assert dm.list_runs(dataset.id) == []
    assert dataset.fetched_at is None


def test_repaired_refresh_resolves_old_failures_and_retains_current_unknowns(session):
    from app.services.data_ingestion import DataIngestionRecorder
    dm = DataManagementRepository(session)
    recorder = DataIngestionRecorder(dm)
    dataset = recorder.record(1, 'price_history', outcome='failed_fetch', error_code='timeout')
    session.commit()
    recorder.record(1, 'price_history', outcome='succeeded', fetch=price_result([bar()], basis='unknown'), persisted=[bar()], issues=('price_basis_unknown',))
    session.commit()
    unresolved = dm.list_quality_issues(dataset.id, unresolved_only=True)
    assert [issue.code for issue in unresolved] == ['price_basis_unknown']
    assert dm.list_quality_issues(dataset.id)[-1].resolved_at is not None


@pytest.mark.parametrize('old_source', [None, 'old'])
def test_unknown_source_subset_does_not_promote_whole_series_lineage(session, old_source):
    from app.services.data_ingestion import DataIngestionRecorder
    dm = DataManagementRepository(session)
    recorder = DataIngestionRecorder(dm)
    source_id = recorder.source(old_source).id if old_source else None
    dm.upsert_dataset(SecurityDataset(security_id=1, category='price_history', source_id=source_id))
    repo = PriceHistoryRepository(session)
    repo.upsert_many([bar(1), bar(2)])
    sync, _ = service(Provider(price_result([bar(2, '9')], source='new', basis='unknown')), repo, recorder)
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.price_bars_upserted == 0
    assert dm.get_dataset(1, 'price_history').source_id == source_id
    assert repo.list_recent_by_security_id(1)[0].close_price == Decimal('10')


def test_attempt_times_enclose_actual_fetch(session):
    from app.services.data_ingestion import DataIngestionRecorder
    class Timed(Provider):
        def fetch_for_security(self, *args, **kwargs):
            self.started = datetime.now(UTC)
            result = super().fetch_for_security(*args, **kwargs)
            self.finished = datetime.now(UTC)
            return result
    dm = DataManagementRepository(session)
    provider = Timed(price_result([bar()]))
    sync, _ = service(provider, PriceHistoryRepository(session), DataIngestionRecorder(dm))
    sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    dataset = dm.get_dataset(1, 'price_history')
    run = dm.list_runs(dataset.id)[0]
    assert run.started_at.replace(tzinfo=UTC) <= provider.started
    assert run.finished_at.replace(tzinfo=UTC) >= provider.finished
    assert dataset.fetched_at.replace(tzinfo=UTC) >= provider.finished


def test_rejected_raw_rows_are_counted_and_partial_sina_response_is_not_promoted():
    import httpx
    from app.services.providers.sina_price_history import SinaPriceHistorySource
    sina = SinaPriceHistorySource(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[dict(day='2026-01-01', open='10', close='11', high='12', low='8', volume='123'), {'day':'bad'}])))
    result = AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('sina', sina)]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.items == [] and result.attempts[0].state == 'failed'


def test_invalid_raw_ohlc_counts_received_rows():
    class Raw:
        def fetch(self, *args, **kwargs):
            return [RawPriceBar(date(2026, 1, 1), *(Decimal(x) for x in ['10','9','8','11','100','1000']))]
    result = AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('invalid', Raw())]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.attempts[0].count == 1
    assert result.attempts[0].error_code == 'invalid_data'


def test_duplicate_received_count_differs_from_written_count(session):
    from app.services.data_ingestion import DataIngestionRecorder
    dm = DataManagementRepository(session)
    sync, _ = service(Provider(price_result([bar(), bar()])), PriceHistoryRepository(session), DataIngestionRecorder(dm))
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    run = dm.list_runs(dm.get_dataset(1, 'price_history').id)[0]
    assert result.price_bars_upserted == run.records_written == 1
    assert run.records_received == 2


def test_financial_negative_revenue_preserved_with_warning_and_nonfinite_quote_rejected():
    from app.services.providers.stock_data_providers import AggregateFinancialMetricsProvider, AggregateQuoteSnapshotProvider, RawFinancialMetricsSourceAdapter, RawQuoteSnapshotSourceAdapter
    from app.services.providers.raw_types import RawFinancialMetrics, RawQuoteSnapshot
    class Financial:
        def fetch(self, *args, **kwargs): return [RawFinancialMetrics('2025Q4', revenue=Decimal('-1'), net_profit=Decimal('-2'))]
    result = AggregateFinancialMetricsProvider(raw_sources=[RawFinancialMetricsSourceAdapter('bad', Financial())]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.items[0].revenue == Decimal('-1')
    assert 'negative_revenue' in result.quality_issues
    class Quote:
        def fetch(self, *args, **kwargs): return RawQuoteSnapshot(Decimal('Infinity'), Decimal('0'), Decimal('0'), datetime.now(UTC))
    result = AggregateQuoteSnapshotProvider(raw_sources=[RawQuoteSnapshotSourceAdapter('bad', Quote())]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.item is None and result.attempts[0].error_code == 'invalid_data'


def test_legacy_plain_list_actual_received_count_and_unknown_source(session):
    from app.services.data_ingestion import DataIngestionRecorder
    dm = DataManagementRepository(session)
    sync, _ = service(Provider([bar(), bar(2)]), PriceHistoryRepository(session), DataIngestionRecorder(dm))
    sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    dataset = dm.get_dataset(1, 'price_history')
    assert dataset.price_basis == 'unknown' and dataset.source_id is None
    assert dm.list_runs(dataset.id)[0].records_received == 2


@pytest.mark.parametrize('category', ['financial_metrics', 'quote_snapshot', 'price_history'])
def test_direct_custom_provider_invalid_values_are_acquisition_failure(session, category):
    from app.services.data_ingestion import DataIngestionRecorder
    from app.db.models import FinancialMetrics, QuoteSnapshot
    from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
    from app.db.repositories.quote_snapshot_repository import QuoteSnapshotRepository
    if category == 'financial_metrics':
        item = FinancialMetrics(security_id=1, report_period='2025Q4', revenue=Decimal('NaN'))
        repository = FinancialMetricsRepository(session)
        fetch = SimpleNamespace(items=[item], warnings=[])
    elif category == 'quote_snapshot':
        item = QuoteSnapshot(security_id=1, last_price=Decimal('Infinity'), change_amount=Decimal('0'), change_percent=Decimal('0'), snapshot_time=datetime.now(UTC))
        repository = QuoteSnapshotRepository(session)
        fetch = SimpleNamespace(item=item, warnings=[])
    else:
        item = bar()
        item.security_id = 2
        repository = PriceHistoryRepository(session)
        fetch = SimpleNamespace(items=[item], warnings=[])
    dm = DataManagementRepository(session)
    sync = StockSyncService(announcement_provider=Provider([]), news_provider=Provider([]), announcement_repository=Repository(), news_repository=Repository(), ingestion_recorder=DataIngestionRecorder(dm), **{category + '_provider':Provider(fetch), category + '_repository':repository})
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=[category])
    assert result.category_outcomes[category] == 'failed_fetch'
    assert dm.get_dataset(1, category).fetched_at is None
    assert dm.list_runs(dm.get_dataset(1, category).id)[0].error_message == 'invalid_data'


def test_netease_malformed_page_never_returns_partial_success():
    import httpx
    from app.services.providers.netease_price_history import NetEasePriceHistorySource
    row = ['2026-01-01','10','12','8','11','100','1000']
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={'data':[row] * 500} if len(calls) == 1 else {'error':'unavailable'})
    source = NetEasePriceHistorySource(transport=httpx.MockTransport(handle))
    result = AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('netease',source)]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.items == [] and result.attempts[0].state == 'failed'
    assert result.attempts[0].count == 500


def test_outer_commit_failure_does_not_leave_new_prices_or_false_freshness(session, monkeypatch):
    from app.services.data_ingestion import DataIngestionRecorder
    repository = PriceHistoryRepository(session)
    repository.upsert_many([bar()])
    dm = DataManagementRepository(session)
    old = datetime(2026, 1, 2, tzinfo=UTC)
    dm.upsert_dataset(SecurityDataset(security_id=1, category='price_history', fetched_at=old))
    sync, _ = service(Provider(price_result([bar(1, '9'), bar(2, '9')])), repository, DataIngestionRecorder(dm))
    def fail_commit(): raise RuntimeError('secret commit error')
    monkeypatch.setattr(session, 'commit', fail_commit)
    result = sync.sync_security(1, stock_code='000001', market='SZ', categories=['price_history'])
    assert result.category_outcomes['price_history'] == 'failed_persist' and result.price_bars_upserted == 0
    assert [r.close_price for r in repository.list_recent_by_security_id(1)] == [Decimal('10')]
    assert dm.get_dataset(1, 'price_history').fetched_at.replace(tzinfo=UTC) == old
    assert 'secret' not in repr(result)


@pytest.mark.parametrize('source_name,status,error_code', [('eastmoney',401,'authentication_error'),('sina',429,'rate_limited')])
def test_news_http_error_is_failed_attempt_not_successful_empty(source_name, status, error_code):
    import httpx
    from app.services.providers.aggregate_providers import AggregateNewsProvider
    from app.services.providers.news_provider import RawNewsSourceAdapter
    from app.services.providers.eastmoney_news import EastmoneyNewsSource
    from app.services.providers.sina_news import SinaNewsSource
    source_type = EastmoneyNewsSource if source_name == 'eastmoney' else SinaNewsSource
    source = source_type(transport=httpx.MockTransport(lambda r:httpx.Response(status)))
    result = AggregateNewsProvider(raw_sources=[RawNewsSourceAdapter(source_name,source)]).fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.attempts[0].state == 'failed'
    assert result.attempts[0].error_code == error_code


def test_legitimate_empty_eastmoney_news_is_empty_attempt():
    import httpx
    from app.services.providers.aggregate_providers import AggregateNewsProvider
    from app.services.providers.news_provider import RawNewsSourceAdapter
    from app.services.providers.eastmoney_news import EastmoneyNewsSource
    source = EastmoneyNewsSource(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='cb({"result":{"cmsArticleWebOld":[]}})')))
    result = AggregateNewsProvider(raw_sources=[RawNewsSourceAdapter('eastmoney',source)]).fetch_for_security(1,stock_code='000001',market='SZ')
    assert result.attempts[0].state == 'empty' and result.warnings == []


def test_negative_revenue_warning_tracks_retained_reports_until_corrected(session):
    from app.services.data_ingestion import DataIngestionRecorder
    from app.db.models import FinancialMetrics
    from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
    dm = DataManagementRepository(session)
    provider = Provider()
    repo = FinancialMetricsRepository(session)
    sync = StockSyncService(announcement_provider=Provider([]), news_provider=Provider([]), announcement_repository=Repository(), news_repository=Repository(), financial_metrics_provider=provider, financial_metrics_repository=repo, ingestion_recorder=DataIngestionRecorder(dm))
    def refresh(period, revenue, profit):
        provider.result = SimpleNamespace(items=[FinancialMetrics(security_id=1, report_period=period, revenue=Decimal(revenue), net_profit=Decimal(profit))], warnings=[])
        return sync.sync_security(1, stock_code='000001', market='SZ', categories=['financial_metrics'])
    refresh('2025-12-31', '-1', '-2')
    dataset = dm.get_dataset(1, 'financial_metrics')
    assert 'negative_revenue' in [i.code for i in dm.list_quality_issues(dataset.id, unresolved_only=True)]
    refresh('2026-03-31', '100', '-10')
    assert len(repo.list_recent_by_security_id(1)) == 2
    assert 'negative_revenue' in [i.code for i in dm.list_quality_issues(dataset.id, unresolved_only=True)]
    refresh('2025-12-31', '50', '-2')
    assert 'negative_revenue' not in [i.code for i in dm.list_quality_issues(dataset.id, unresolved_only=True)]
    assert all(i.resolved_at is not None for i in dm.list_quality_issues(dataset.id) if i.code == 'negative_revenue')
    assert any(i.net_profit < 0 for i in repo.list_recent_by_security_id(1))


def test_malformed_eastmoney_rows_count_all_received_and_rejected(session):
    import httpx
    from app.services.providers.eastmoney_price_history import EastmoneyPriceHistorySource
    from app.services.data_ingestion import DataIngestionRecorder
    source = EastmoneyPriceHistorySource(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'data':{'klines':['2026-01-01,10,11,12,8,100,1000', 'malformed']}})))
    provider = AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('eastmoney', source)])
    result = provider.fetch_for_security(1, stock_code='000001', market='SZ')
    assert result.items == []
    assert result.attempts[0].count == 2 and result.attempts[0].error_code == 'invalid_data'
    dm = DataManagementRepository(session)
    sync, _ = service(provider, PriceHistoryRepository(session), DataIngestionRecorder(dm))
    sync.sync_security(1,stock_code='000001',market='SZ',categories=['price_history'])
    run = dm.list_runs(dm.get_dataset(1,'price_history').id)[0]
    assert run.records_received == run.records_rejected == 2
    assert run.records_written == 0 and run.status == 'failed'
