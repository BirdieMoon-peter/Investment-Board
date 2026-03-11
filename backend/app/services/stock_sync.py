from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.db.models.timestamps import utc_now
from app.db.repositories.announcement_repository import AnnouncementRepository
from app.db.repositories.news_repository import NewsRepository
from app.services.providers.announcement_provider import AnnouncementProvider
from app.services.providers.news_provider import NewsProvider


@dataclass(frozen=True)
class StockSyncResult:
    synced: bool
    announcements_upserted: int
    news_items_upserted: int
    warnings: list[str] = field(default_factory=list)
    synced_at: datetime | None = None


class StockSyncService:
    def __init__(
        self,
        *,
        announcement_provider: AnnouncementProvider,
        news_provider: NewsProvider,
        announcement_repository: AnnouncementRepository,
        news_repository: NewsRepository,
    ):
        self.announcement_provider = announcement_provider
        self.news_provider = news_provider
        self.announcement_repository = announcement_repository
        self.news_repository = news_repository

    def sync_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        synced_at: datetime | None = None,
    ) -> StockSyncResult:
        latest_announcement_at = self.announcement_repository.get_latest_published_at(security_id)
        latest_news_at = self.news_repository.get_latest_published_at(security_id)

        announcement_fetch = self._normalize_fetch_result(
            self.announcement_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
                since=latest_announcement_at,
            )
        )
        news_fetch = self._normalize_fetch_result(
            self.news_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
                since=latest_news_at,
            )
        )

        persisted_announcements = (
            self.announcement_repository.upsert_many(announcement_fetch["items"])
            if announcement_fetch["items"]
            else []
        )
        persisted_news_items = (
            self.news_repository.upsert_many(news_fetch["items"])
            if news_fetch["items"]
            else []
        )

        return StockSyncResult(
            synced=True,
            announcements_upserted=len(persisted_announcements),
            news_items_upserted=len(persisted_news_items),
            warnings=[*announcement_fetch["warnings"], *news_fetch["warnings"]],
            synced_at=synced_at or utc_now(),
        )

    @staticmethod
    def _normalize_fetch_result(fetch_result: Any) -> dict[str, list[Any]]:
        items = getattr(fetch_result, "items", fetch_result)
        warnings = getattr(fetch_result, "warnings", [])
        return {
            "items": list(items),
            "warnings": list(warnings),
        }
