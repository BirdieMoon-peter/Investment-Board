from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.db.models.timestamps import utc_now
from app.db.repositories.announcement_repository import AnnouncementRepository
from app.db.repositories.company_profile_repository import CompanyProfileRepository
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
from app.db.repositories.news_repository import NewsRepository
from app.db.repositories.price_history_repository import PriceHistoryRepository
from app.services.providers.announcement_provider import AnnouncementProvider
from app.services.providers.news_provider import NewsProvider


@dataclass(frozen=True)
class StockSyncResult:
    synced: bool
    announcements_upserted: int
    news_items_upserted: int
    price_bars_upserted: int = 0
    financial_metrics_upserted: int = 0
    company_profile_updated: bool = False
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
        price_history_provider: Any | None = None,
        financial_metrics_provider: Any | None = None,
        company_profile_provider: Any | None = None,
        price_history_repository: PriceHistoryRepository | None = None,
        financial_metrics_repository: FinancialMetricsRepository | None = None,
        company_profile_repository: CompanyProfileRepository | None = None,
    ):
        self.announcement_provider = announcement_provider
        self.news_provider = news_provider
        self.announcement_repository = announcement_repository
        self.news_repository = news_repository
        self.price_history_provider = price_history_provider
        self.financial_metrics_provider = financial_metrics_provider
        self.company_profile_provider = company_profile_provider
        self.price_history_repository = price_history_repository
        self.financial_metrics_repository = financial_metrics_repository
        self.company_profile_repository = company_profile_repository

    def sync_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        synced_at: datetime | None = None,
    ) -> StockSyncResult:
        latest_announcement_at = self._normalize_since_utc(
            self.announcement_repository.get_latest_published_at(security_id)
        )
        latest_news_at = self._normalize_since_utc(self.news_repository.get_latest_published_at(security_id))

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

        price_history_fetch = self._normalize_fetch_result(
            self.price_history_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
            )
        ) if self.price_history_provider is not None else {"items": [], "warnings": []}
        financial_metrics_fetch = self._normalize_fetch_result(
            self.financial_metrics_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
            )
        ) if self.financial_metrics_provider is not None else {"items": [], "warnings": []}
        company_profile_fetch = self._normalize_single_fetch_result(
            self.company_profile_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
            )
        ) if self.company_profile_provider is not None else {"item": None, "warnings": []}

        persisted_price_history = (
            self.price_history_repository.upsert_many(price_history_fetch["items"])
            if self.price_history_repository is not None and price_history_fetch["items"]
            else []
        )
        persisted_financial_metrics = (
            self.financial_metrics_repository.upsert_many(financial_metrics_fetch["items"])
            if self.financial_metrics_repository is not None and financial_metrics_fetch["items"]
            else []
        )
        persisted_company_profile = (
            self.company_profile_repository.upsert(company_profile_fetch["item"])
            if self.company_profile_repository is not None and company_profile_fetch["item"] is not None
            else None
        )

        return StockSyncResult(
            synced=True,
            announcements_upserted=len(persisted_announcements),
            news_items_upserted=len(persisted_news_items),
            price_bars_upserted=len(persisted_price_history),
            financial_metrics_upserted=len(persisted_financial_metrics),
            company_profile_updated=persisted_company_profile is not None,
            warnings=[
                *announcement_fetch["warnings"],
                *news_fetch["warnings"],
                *price_history_fetch["warnings"],
                *financial_metrics_fetch["warnings"],
                *company_profile_fetch["warnings"],
            ],
            synced_at=synced_at or utc_now(),
        )

    @staticmethod
    def _normalize_since_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _normalize_fetch_result(fetch_result: Any) -> dict[str, list[Any]]:
        items = getattr(fetch_result, "items", fetch_result)
        warnings = getattr(fetch_result, "warnings", [])
        return {
            "items": list(items),
            "warnings": list(warnings),
        }

    @staticmethod
    def _normalize_single_fetch_result(fetch_result: Any) -> dict[str, Any]:
        item = getattr(fetch_result, "item", fetch_result)
        warnings = getattr(fetch_result, "warnings", [])
        return {
            "item": item,
            "warnings": list(warnings),
        }
