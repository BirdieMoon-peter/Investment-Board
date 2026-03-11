from dataclasses import dataclass
from datetime import datetime

from app.db.models import Announcement, NewsItem
from app.services.providers.aggregate_providers import AnnouncementFetchResult, NewsFetchResult
from app.services.stock_sync import StockSyncService


@dataclass
class StubAnnouncementProvider:
    items: list[Announcement]
    expected_since: datetime | None
    expected_stock_code: str
    expected_market: str

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        since: datetime | None = None,
    ) -> list[Announcement]:
        assert since == self.expected_since
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        return self.items


@dataclass
class StubNewsProvider:
    items: list[NewsItem]
    expected_since: datetime | None
    expected_stock_code: str
    expected_market: str

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        since: datetime | None = None,
    ) -> list[NewsItem]:
        assert since == self.expected_since
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        return self.items


@dataclass
class StubAggregateAnnouncementProvider:
    result: AnnouncementFetchResult
    expected_since: datetime | None
    expected_stock_code: str
    expected_market: str

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        since: datetime | None = None,
    ) -> AnnouncementFetchResult:
        assert since == self.expected_since
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        return self.result


@dataclass
class StubAggregateNewsProvider:
    result: NewsFetchResult
    expected_since: datetime | None
    expected_stock_code: str
    expected_market: str

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        since: datetime | None = None,
    ) -> NewsFetchResult:
        assert since == self.expected_since
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        return self.result


class RecordingAnnouncementRepository:
    def __init__(self, latest_published_at: datetime | None = None):
        self.latest_published_at = latest_published_at
        self.upsert_calls: list[list[Announcement]] = []

    def get_latest_published_at(self, security_id: int) -> datetime | None:
        return self.latest_published_at

    def upsert_many(self, items: list[Announcement]) -> list[Announcement]:
        self.upsert_calls.append(items)
        return items


class RecordingNewsRepository:
    def __init__(self, latest_published_at: datetime | None = None):
        self.latest_published_at = latest_published_at
        self.upsert_calls: list[list[NewsItem]] = []

    def get_latest_published_at(self, security_id: int) -> datetime | None:
        return self.latest_published_at

    def upsert_many(self, items: list[NewsItem]) -> list[NewsItem]:
        self.upsert_calls.append(items)
        return items


def test_sync_security_uses_incremental_cutoffs_and_persists_provider_rows():
    security_id = 7
    stock_code = "600519"
    market = "sh"
    announcement = Announcement(
        security_id=security_id,
        title="Board resolution",
        source="Exchange",
        url="https://example.com/announcements/7",
        summary="Board summary",
        published_at=datetime(2026, 3, 11, 8, 0),
    )
    news_item = NewsItem(
        security_id=security_id,
        title="Morning briefing",
        source="Newswire",
        url="https://example.com/news/7",
        summary="Morning summary",
        published_at=datetime(2026, 3, 11, 8, 30),
    )
    announcement_repository = RecordingAnnouncementRepository(
        latest_published_at=datetime(2026, 3, 10, 9, 0)
    )
    news_repository = RecordingNewsRepository(latest_published_at=datetime(2026, 3, 10, 9, 0))
    service = StockSyncService(
        announcement_provider=StubAnnouncementProvider(
            [announcement],
            datetime(2026, 3, 10, 9, 0),
            stock_code,
            market,
        ),
        news_provider=StubNewsProvider(
            [news_item],
            datetime(2026, 3, 10, 9, 0),
            stock_code,
            market,
        ),
        announcement_repository=announcement_repository,
        news_repository=news_repository,
    )

    result = service.sync_security(security_id, stock_code=stock_code, market=market)

    assert announcement_repository.upsert_calls == [[announcement]]
    assert news_repository.upsert_calls == [[news_item]]
    assert result.announcements_upserted == 1
    assert result.news_items_upserted == 1


def test_sync_security_passes_security_metadata_to_providers():
    security_id = 21
    stock_code = "000001"
    market = "sz"
    service = StockSyncService(
        announcement_provider=StubAnnouncementProvider([], None, stock_code, market),
        news_provider=StubNewsProvider([], None, stock_code, market),
        announcement_repository=RecordingAnnouncementRepository(),
        news_repository=RecordingNewsRepository(),
    )

    result = service.sync_security(security_id, stock_code=stock_code, market=market)

    assert result.synced is True
    assert result.announcements_upserted == 0
    assert result.news_items_upserted == 0


def test_sync_security_keeps_warning_aware_partial_success_with_real_aggregate_results():
    security_id = 15
    stock_code = "600000"
    market = "sh"
    synced_at = datetime(2026, 3, 11, 14, 0)
    announcement = Announcement(
        security_id=security_id,
        title="Recovered filing",
        source="Exchange",
        url="https://example.com/announcements/15",
        summary="Recovered from healthy source",
        published_at=datetime(2026, 3, 11, 13, 30),
    )
    service = StockSyncService(
        announcement_provider=StubAggregateAnnouncementProvider(
            AnnouncementFetchResult(
                items=[announcement],
                warnings=["announcement source B failed"],
            ),
            None,
            stock_code,
            market,
        ),
        news_provider=StubAggregateNewsProvider(
            NewsFetchResult(items=[], warnings=["news source A timeout"]),
            None,
            stock_code,
            market,
        ),
        announcement_repository=RecordingAnnouncementRepository(),
        news_repository=RecordingNewsRepository(),
    )

    result = service.sync_security(
        security_id,
        stock_code=stock_code,
        market=market,
        synced_at=synced_at,
    )

    assert result.synced is True
    assert result.synced_at == synced_at
    assert result.warnings == ["announcement source B failed", "news source A timeout"]
    assert result.announcements_upserted == 1
    assert result.news_items_upserted == 0


def test_sync_security_skips_repository_writes_when_providers_return_no_rows():
    security_id = 11
    stock_code = "300750"
    market = "sz"
    announcement_repository = RecordingAnnouncementRepository()
    news_repository = RecordingNewsRepository()
    service = StockSyncService(
        announcement_provider=StubAnnouncementProvider([], None, stock_code, market),
        news_provider=StubNewsProvider([], None, stock_code, market),
        announcement_repository=announcement_repository,
        news_repository=news_repository,
    )

    result = service.sync_security(security_id, stock_code=stock_code, market=market)

    assert announcement_repository.upsert_calls == []
    assert news_repository.upsert_calls == []
    assert result.announcements_upserted == 0
    assert result.news_items_upserted == 0
