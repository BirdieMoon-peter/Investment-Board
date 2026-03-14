from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime, timezone

import pytest

from app.db.models import Announcement, NewsItem
from app.services.providers import (
    AggregateAnnouncementProvider,
    AggregateNewsProvider,
    AnnouncementSourceAdapter,
    NewsSourceAdapter,
    RawAnnouncement,
    RawAnnouncementSource,
    RawAnnouncementSourceAdapter,
    RawNewsItem,
    RawNewsSource,
    RawNewsSourceAdapter,
    build_provider_client,
)


@dataclass
class SuccessfulRawAnnouncementSource:
    items: list[RawAnnouncement]
    expected_stock_code: str
    expected_market: str
    expected_since: datetime | None

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> list[RawAnnouncement]:
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        assert since == self.expected_since
        return self.items


class FailingRawAnnouncementSource:
    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> list[RawAnnouncement]:
        raise RuntimeError("upstream announcement source unavailable")


@dataclass
class SuccessfulRawNewsSource:
    items: list[RawNewsItem]
    expected_stock_code: str
    expected_market: str
    expected_since: datetime | None

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> list[RawNewsItem]:
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        assert since == self.expected_since
        return self.items


class FailingRawNewsSource:
    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> list[RawNewsItem]:
        raise RuntimeError("upstream news source unavailable")


@dataclass
class ExistingAnnouncementProvider:
    items: list[Announcement]

    def fetch_for_security(
        self,
        security_id: int,
        *,
        since: datetime | None = None,
    ) -> list[Announcement]:
        assert all(item.security_id == security_id for item in self.items)
        return self.items


@dataclass
class ExistingNewsProvider:
    items: list[NewsItem]

    def fetch_for_security(
        self,
        security_id: int,
        *,
        since: datetime | None = None,
    ) -> list[NewsItem]:
        assert all(item.security_id == security_id for item in self.items)
        return self.items


class StubAnnouncementProvider:
    def fetch_for_security(
        self,
        security_id: int,
        *,
        since: datetime | None = None,
    ) -> list[object]:
        return []


class StubNewsProvider:
    def fetch_for_security(
        self,
        security_id: int,
        *,
        since: datetime | None = None,
    ) -> list[object]:
        return []


def test_aggregate_announcement_provider_converts_raw_items_to_models_and_deduplicates():
    security_id = 7
    since = datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc)
    duplicate_raw = RawAnnouncement(
        title="Board resolution",
        published_at=datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc),
        source="Eastmoney",
        url="https://example.com/raw/board-resolution",
        summary="Duplicate item across raw sources",
    )
    unique_raw = RawAnnouncement(
        title="Earnings forecast",
        published_at=datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc),
        source="Sina",
        url="https://example.com/raw/earnings-forecast",
        summary="Unique raw item",
    )
    existing_item = Announcement(
        security_id=security_id,
        title="Legacy filing",
        source="Archive",
        url="https://example.com/existing/legacy-filing",
        summary="Existing provider item",
        published_at=datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc),
    )
    provider = AggregateAnnouncementProvider(
        sources=[AnnouncementSourceAdapter("existing", ExistingAnnouncementProvider([existing_item]))],
        raw_sources=[
            RawAnnouncementSourceAdapter(
                "eastmoney",
                SuccessfulRawAnnouncementSource(
                    [duplicate_raw],
                    expected_stock_code="600519",
                    expected_market="sh",
                    expected_since=since,
                ),
            ),
            RawAnnouncementSourceAdapter(
                "sina",
                SuccessfulRawAnnouncementSource(
                    [duplicate_raw, unique_raw],
                    expected_stock_code="600519",
                    expected_market="sh",
                    expected_since=since,
                ),
            ),
        ],
    )

    result = provider.fetch_for_security(
        security_id,
        stock_code="600519",
        market="sh",
        since=since,
    )

    assert result.warnings == []
    assert [(item.title, item.published_at) for item in result.items] == [
        ("Earnings forecast", datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc)),
        ("Board resolution", datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc)),
        ("Legacy filing", datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc)),
    ]
    assert all(item.security_id == security_id for item in result.items)
    converted = next(item for item in result.items if item.title == "Board resolution")
    assert converted.url == duplicate_raw.url
    assert converted.summary == duplicate_raw.summary


def test_aggregate_news_provider_collects_source_errors_as_warnings():
    security_id = 9
    since = datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc)
    surviving_raw = RawNewsItem(
        title="Midday recap",
        published_at=datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc),
        source="Sina",
        url="https://example.com/news/midday-recap",
        summary="Still returned from healthy source",
    )
    provider = AggregateNewsProvider(
        raw_sources=[
            RawNewsSourceAdapter("wire", FailingRawNewsSource()),
            RawNewsSourceAdapter(
                "backup",
                SuccessfulRawNewsSource(
                    [surviving_raw],
                    expected_stock_code="000001",
                    expected_market="sz",
                    expected_since=since,
                ),
            ),
        ]
    )

    result = provider.fetch_for_security(
        security_id,
        stock_code="000001",
        market="sz",
        since=since,
    )

    assert len(result.items) == 1
    assert result.items[0].security_id == security_id
    assert result.items[0].title == "Midday recap"
    assert len(result.warnings) == 1
    assert "wire failed (stock=sz:000001): RuntimeError: upstream news source unavailable" == result.warnings[0]


def test_provider_modules_export_real_source_primitives():
    published_at = datetime(2026, 3, 11, 9, 30, tzinfo=timezone.utc)
    raw_announcement = RawAnnouncement(
        title="Board resolution",
        published_at=published_at,
        source="exchange",
    )
    raw_news_item = RawNewsItem(
        title="Morning briefing",
        published_at=published_at,
        source="wire",
    )

    with pytest.raises(FrozenInstanceError):
        raw_announcement.title = "Updated"

    with pytest.raises(FrozenInstanceError):
        raw_news_item.title = "Updated"

    announcement_source: RawAnnouncementSource = SuccessfulRawAnnouncementSource(
        [
            RawAnnouncement(
                title="sh:600519",
                published_at=published_at,
                source="stub-announcement",
            )
        ],
        expected_stock_code="600519",
        expected_market="sh",
        expected_since=published_at,
    )
    news_source: RawNewsSource = SuccessfulRawNewsSource(
        [
            RawNewsItem(
                title="sz:000001",
                published_at=published_at,
                source="stub-news",
            )
        ],
        expected_stock_code="000001",
        expected_market="sz",
        expected_since=published_at,
    )

    announcement_adapter = RawAnnouncementSourceAdapter(
        name="eastmoney",
        provider=announcement_source,
    )
    news_adapter = RawNewsSourceAdapter(name="ifeng", provider=news_source)

    assert announcement_adapter.provider.fetch("600519", "sh", since=published_at) == [
        RawAnnouncement(
            title="sh:600519",
            published_at=published_at,
            source="stub-announcement",
        )
    ]
    assert news_adapter.provider.fetch("000001", "sz", since=published_at) == [
        RawNewsItem(
            title="sz:000001",
            published_at=published_at,
            source="stub-news",
        )
    ]

    assert AnnouncementSourceAdapter("existing", StubAnnouncementProvider()).name == "existing"
    assert NewsSourceAdapter("existing", StubNewsProvider()).name == "existing"

    client = build_provider_client()
    try:
        assert client.headers["user-agent"].startswith("Mozilla/5.0")
        assert client.timeout.connect == pytest.approx(10.0)
        assert client.timeout.read == pytest.approx(10.0)
        assert client.timeout.write == pytest.approx(10.0)
        assert client.timeout.pool == pytest.approx(10.0)
    finally:
        client.close()


def test_aggregate_announcement_provider_includes_context_in_warnings():
    security_id = 7
    stock_code = "600519"
    market = "sh"

    class FailingSource:
        def fetch(self, stock_code: str, market: str, *, since=None):
            raise ValueError("upstream unavailable")

    provider = AggregateAnnouncementProvider(
        raw_sources=[RawAnnouncementSourceAdapter("test-source", FailingSource())]
    )

    result = provider.fetch_for_security(
        security_id, stock_code=stock_code, market=market
    )

    assert len(result.warnings) == 1
    assert "test-source" in result.warnings[0]
    assert "sh:600519" in result.warnings[0]
    assert "ValueError" in result.warnings[0]
