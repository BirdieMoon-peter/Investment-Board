from dataclasses import dataclass
from datetime import datetime

from app.db.models import Announcement, NewsItem
from app.services.providers.aggregate_providers import AnnouncementFetchResult, NewsFetchResult
from app.services.stock_sync import StockSyncService


@dataclass
class RecordingAggregateAnnouncementProvider:
    result: AnnouncementFetchResult
    calls: list[dict[str, object]]

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str | None = None,
        market: str | None = None,
        since: datetime | None = None,
    ) -> AnnouncementFetchResult:
        self.calls.append(
            {
                "security_id": security_id,
                "stock_code": stock_code,
                "market": market,
                "since": since,
            }
        )
        return self.result


@dataclass
class RecordingAggregateNewsProvider:
    result: NewsFetchResult
    calls: list[dict[str, object]]

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str | None = None,
        market: str | None = None,
        since: datetime | None = None,
    ) -> NewsFetchResult:
        self.calls.append(
            {
                "security_id": security_id,
                "stock_code": stock_code,
                "market": market,
                "since": since,
            }
        )
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


def test_sync_security_passes_security_metadata_to_providers():
    security_id = 21
    stock_code = "000001"
    market = "sz"
    announcement_calls: list[dict[str, object]] = []
    news_calls: list[dict[str, object]] = []
    service = StockSyncService(
        announcement_provider=RecordingAggregateAnnouncementProvider(
            AnnouncementFetchResult(items=[], warnings=[]),
            announcement_calls,
        ),
        news_provider=RecordingAggregateNewsProvider(
            NewsFetchResult(items=[], warnings=[]),
            news_calls,
        ),
        announcement_repository=RecordingAnnouncementRepository(),
        news_repository=RecordingNewsRepository(),
    )

    result = service.sync_security(security_id, stock_code=stock_code, market=market)

    assert result.synced is True
    assert announcement_calls == [
        {
            "security_id": security_id,
            "stock_code": stock_code,
            "market": market,
            "since": None,
        }
    ]
    assert news_calls == [
        {
            "security_id": security_id,
            "stock_code": stock_code,
            "market": market,
            "since": None,
        }
    ]


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
    announcement_repository = RecordingAnnouncementRepository()
    news_repository = RecordingNewsRepository()
    service = StockSyncService(
        announcement_provider=RecordingAggregateAnnouncementProvider(
            AnnouncementFetchResult(
                items=[announcement],
                warnings=["announcement source B failed"],
            ),
            [],
        ),
        news_provider=RecordingAggregateNewsProvider(
            NewsFetchResult(items=[], warnings=["news source A timeout"]),
            [],
        ),
        announcement_repository=announcement_repository,
        news_repository=news_repository,
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
    assert announcement_repository.upsert_calls == [[announcement]]
    assert news_repository.upsert_calls == []
