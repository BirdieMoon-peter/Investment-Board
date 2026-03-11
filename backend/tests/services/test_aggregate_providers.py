from dataclasses import dataclass
from datetime import datetime

from app.db.models import Announcement, NewsItem
from app.services.providers.aggregate_providers import (
    AggregateAnnouncementProvider,
    AggregateNewsProvider,
)
from app.services.providers.announcement_provider import AnnouncementSourceAdapter
from app.services.providers.news_provider import NewsSourceAdapter


@dataclass
class AnnouncementSourceSuccess:
    items: list[Announcement]

    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> list[Announcement]:
        assert all(item.security_id == security_id for item in self.items)
        return self.items


class AnnouncementSourceFailure:
    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> list[Announcement]:
        raise RuntimeError("upstream announcement source unavailable")


@dataclass
class NewsSourceSuccess:
    items: list[NewsItem]

    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> list[NewsItem]:
        assert all(item.security_id == security_id for item in self.items)
        return self.items


class NewsSourceFailure:
    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> list[NewsItem]:
        raise RuntimeError("upstream news source unavailable")



def test_aggregate_announcement_provider_merges_sources_without_duplicates():
    security_id = 7
    duplicate = Announcement(
        security_id=security_id,
        title="Board resolution",
        source="Exchange",
        url="https://example.com/announcements/board-resolution",
        summary="Duplicate item across sources",
        published_at=datetime(2026, 3, 11, 9, 0),
    )
    unique = Announcement(
        security_id=security_id,
        title="Earnings forecast",
        source="Vendor",
        url="https://example.com/announcements/earnings-forecast",
        summary="Unique item",
        published_at=datetime(2026, 3, 11, 10, 0),
    )
    provider = AggregateAnnouncementProvider(
        sources=[
            AnnouncementSourceAdapter("source-a", AnnouncementSourceSuccess([duplicate])),
            AnnouncementSourceAdapter("source-b", AnnouncementSourceSuccess([duplicate, unique])),
        ]
    )

    result = provider.fetch_for_security(security_id)

    assert result.warnings == []
    assert [(item.title, item.published_at) for item in result.items] == [
        ("Earnings forecast", datetime(2026, 3, 11, 10, 0)),
        ("Board resolution", datetime(2026, 3, 11, 9, 0)),
    ]



def test_aggregate_announcement_provider_returns_warnings_for_failed_sources():
    security_id = 7
    surviving_item = Announcement(
        security_id=security_id,
        title="Trading update",
        source="Exchange",
        url="https://example.com/announcements/trading-update",
        summary="Still returned from healthy source",
        published_at=datetime(2026, 3, 11, 11, 0),
    )
    provider = AggregateAnnouncementProvider(
        sources=[
            AnnouncementSourceAdapter("exchange", AnnouncementSourceFailure()),
            AnnouncementSourceAdapter("vendor", AnnouncementSourceSuccess([surviving_item])),
        ]
    )

    result = provider.fetch_for_security(security_id)

    assert result.items == [surviving_item]
    assert result.warnings == ["upstream announcement source unavailable"]



def test_aggregate_news_provider_merges_sources_without_duplicates():
    security_id = 9
    duplicate = NewsItem(
        security_id=security_id,
        title="Sector opens higher",
        source="Newswire",
        url="https://example.com/news/sector-opens-higher",
        summary="Duplicate item across sources",
        published_at=datetime(2026, 3, 11, 9, 15),
    )
    unique = NewsItem(
        security_id=security_id,
        title="Broker raises target",
        source="BrokerDesk",
        url="https://example.com/news/broker-raises-target",
        summary="Unique item",
        published_at=datetime(2026, 3, 11, 10, 30),
    )
    provider = AggregateNewsProvider(
        sources=[
            NewsSourceAdapter("source-a", NewsSourceSuccess([duplicate])),
            NewsSourceAdapter("source-b", NewsSourceSuccess([duplicate, unique])),
        ]
    )

    result = provider.fetch_for_security(security_id)

    assert result.warnings == []
    assert [(item.title, item.published_at) for item in result.items] == [
        ("Broker raises target", datetime(2026, 3, 11, 10, 30)),
        ("Sector opens higher", datetime(2026, 3, 11, 9, 15)),
    ]



def test_aggregate_news_provider_returns_warnings_for_failed_sources():
    security_id = 9
    surviving_item = NewsItem(
        security_id=security_id,
        title="Midday recap",
        source="Newswire",
        url="https://example.com/news/midday-recap",
        summary="Still returned from healthy source",
        published_at=datetime(2026, 3, 11, 12, 0),
    )
    provider = AggregateNewsProvider(
        sources=[
            NewsSourceAdapter("wire", NewsSourceFailure()),
            NewsSourceAdapter("backup", NewsSourceSuccess([surviving_item])),
        ]
    )

    result = provider.fetch_for_security(security_id)

    assert result.items == [surviving_item]
    assert result.warnings == ["upstream news source unavailable"]
