from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.models import Announcement, NewsItem
from app.services.providers.announcement_provider import (
    AnnouncementProvider,
    AnnouncementSourceAdapter,
    RawAnnouncementSourceAdapter,
)
from app.services.providers.news_provider import (
    NewsProvider,
    NewsSourceAdapter,
    RawNewsSourceAdapter,
)
from app.services.providers.fetch_provenance import SourceAttempt, safe_error_code
from app.services.providers.raw_types import RawAnnouncement, RawNewsItem


@dataclass(frozen=True)
class AnnouncementFetchResult:
    items: list[Announcement]
    warnings: list[str]
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str | None = None
    price_basis: str = "unknown"
    unit: str | None = None
    frequency: str | None = None


@dataclass(frozen=True)
class NewsFetchResult:
    items: list[NewsItem]
    warnings: list[str]
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str | None = None
    price_basis: str = "unknown"
    unit: str | None = None
    frequency: str | None = None


class AggregateAnnouncementProvider:
    def __init__(
        self,
        *,
        sources: list[AnnouncementSourceAdapter] | None = None,
        raw_sources: list[RawAnnouncementSourceAdapter] | None = None,
    ):
        self.sources = list(sources or [])
        self.raw_sources = list(raw_sources or [])

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str | None = None,
        market: str | None = None,
        since: datetime | None = None,
    ) -> AnnouncementFetchResult:
        items: list[Announcement] = []
        warnings: list[str] = []
        attempts = []

        for source in self.sources:
            started = datetime.now(UTC)
            try:
                fetched = list(source.provider.fetch_for_security(security_id, since=since))
                items.extend(fetched)
                attempts.append(SourceAttempt(source.name, "succeeded" if fetched else "empty", len(fetched), started_at=started, finished_at=datetime.now(UTC)))
            except Exception as exc:
                attempts.append(SourceAttempt(source.name, "failed", error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                warnings.append(_warning_message(source.name, exc))

        if self.raw_sources:
            if stock_code is None or market is None:
                missing = "stock_code and market" if stock_code is None and market is None else (
                    "stock_code" if stock_code is None else "market"
                )
                warnings.append(f"raw announcement sources skipped: missing {missing}")
            else:
                for source in self.raw_sources:
                    started = datetime.now(UTC)
                    try:
                        raw_items = list(source.provider.fetch(stock_code, market, since=since))
                        fetched = [_announcement_from_raw(security_id, raw_item) for raw_item in raw_items]
                        items.extend(fetched)
                        attempts.append(SourceAttempt(source.name, "succeeded" if fetched else "empty", len(fetched), started_at=started, finished_at=datetime.now(UTC)))
                    except Exception as exc:
                        attempts.append(SourceAttempt(source.name, "failed", error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                        warnings.append(_warning_message(source.name, exc, stock_code=stock_code, market=market))

        return AnnouncementFetchResult(
            items=_deduplicate_announcements(items),
            warnings=warnings, attempts=tuple(attempts), source_key=_single_source(attempts),
        )


class AggregateNewsProvider:
    def __init__(
        self,
        *,
        sources: list[NewsSourceAdapter] | None = None,
        raw_sources: list[RawNewsSourceAdapter] | None = None,
    ):
        self.sources = list(sources or [])
        self.raw_sources = list(raw_sources or [])

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str | None = None,
        market: str | None = None,
        since: datetime | None = None,
    ) -> NewsFetchResult:
        items: list[NewsItem] = []
        warnings: list[str] = []
        attempts = []

        for source in self.sources:
            started = datetime.now(UTC)
            try:
                fetched = list(source.provider.fetch_for_security(security_id, since=since))
                items.extend(fetched)
                attempts.append(SourceAttempt(source.name, "succeeded" if fetched else "empty", len(fetched), started_at=started, finished_at=datetime.now(UTC)))
            except Exception as exc:
                attempts.append(SourceAttempt(source.name, "failed", error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                warnings.append(_warning_message(source.name, exc))

        if self.raw_sources:
            if stock_code is None or market is None:
                missing = "stock_code and market" if stock_code is None and market is None else (
                    "stock_code" if stock_code is None else "market"
                )
                warnings.append(f"raw news sources skipped: missing {missing}")
            else:
                for source in self.raw_sources:
                    started = datetime.now(UTC)
                    try:
                        raw_items = list(source.provider.fetch(stock_code, market, since=since))
                        fetched = [_news_from_raw(security_id, raw_item) for raw_item in raw_items]
                        items.extend(fetched)
                        attempts.append(SourceAttempt(source.name, "succeeded" if fetched else "empty", len(fetched), started_at=started, finished_at=datetime.now(UTC)))
                    except Exception as exc:
                        attempts.append(SourceAttempt(source.name, "failed", error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                        warnings.append(_warning_message(source.name, exc, stock_code=stock_code, market=market))

        return NewsFetchResult(items=_deduplicate_news(items), warnings=warnings, attempts=tuple(attempts), source_key=_single_source(attempts))


class AnnouncementItemsProvider:
    def __init__(self, aggregate_provider: AggregateAnnouncementProvider):
        self.aggregate_provider = aggregate_provider

    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> Iterable[Announcement]:
        return self.aggregate_provider.fetch_for_security(security_id, since=since).items


class NewsItemsProvider:
    def __init__(self, aggregate_provider: AggregateNewsProvider):
        self.aggregate_provider = aggregate_provider

    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> Iterable[NewsItem]:
        return self.aggregate_provider.fetch_for_security(security_id, since=since).items


def _warning_message(
    source_name: str,
    exc: Exception,
    *,
    stock_code: str | None = None,
    market: str | None = None,
) -> str:
    context = f" (stock={market}:{stock_code})" if stock_code and market else ""
    return f"{source_name} failed{context}: {safe_error_code(exc)}"


def _announcement_from_raw(security_id: int, item: RawAnnouncement) -> Announcement:
    return Announcement(
        security_id=security_id,
        title=item.title,
        published_at=item.published_at,
        source=item.source,
        url=item.url,
        summary=item.summary,
    )


def _news_from_raw(security_id: int, item: RawNewsItem) -> NewsItem:
    return NewsItem(
        security_id=security_id,
        title=item.title,
        published_at=item.published_at,
        source=item.source,
        url=item.url,
        summary=item.summary,
    )


def _announcement_key(item: Announcement) -> tuple[int, datetime, str]:
    return (item.security_id, item.published_at, item.title)


def _news_key(item: NewsItem) -> tuple[int, datetime, str]:
    return (item.security_id, item.published_at, item.title)


def _deduplicate_announcements(items: list[Announcement]) -> list[Announcement]:
    unique_by_key: dict[tuple[int, datetime, str], Announcement] = {}
    for item in items:
        unique_by_key.setdefault(_announcement_key(item), item)
    return sorted(
        unique_by_key.values(),
        key=lambda item: (item.published_at, item.title, item.source or ""),
        reverse=True,
    )


def _deduplicate_news(items: list[NewsItem]) -> list[NewsItem]:
    unique_by_key: dict[tuple[int, datetime, str], NewsItem] = {}
    for item in items:
        unique_by_key.setdefault(_news_key(item), item)
    return sorted(
        unique_by_key.values(),
        key=lambda item: (item.published_at, item.title, item.source or ""),
        reverse=True,
    )


def _single_source(attempts):
    keys = {a.source_key for a in attempts if a.state == "succeeded"}
    return next(iter(keys)) if len(keys) == 1 else None
