from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.db.models.timestamps import utc_now
from app.db.repositories.announcement_repository import AnnouncementRepository
from app.db.repositories.company_profile_repository import CompanyProfileRepository
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
from app.db.repositories.news_repository import NewsRepository
from app.db.repositories.price_history_repository import PriceHistoryRepository
from app.db.repositories.quote_snapshot_repository import QuoteSnapshotRepository
from app.services.providers.announcement_provider import AnnouncementProvider
from app.services.providers.news_provider import NewsProvider


@dataclass(frozen=True)
class StockSyncResult:
    synced: bool
    announcements_upserted: int
    news_items_upserted: int
    price_bars_upserted: int = 0
    financial_metrics_upserted: int = 0
    quote_snapshot_updated: bool = False
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
        quote_snapshot_provider: Any | None = None,
        company_profile_provider: Any | None = None,
        price_history_repository: PriceHistoryRepository | None = None,
        financial_metrics_repository: FinancialMetricsRepository | None = None,
        quote_snapshot_repository: QuoteSnapshotRepository | None = None,
        company_profile_repository: CompanyProfileRepository | None = None,
    ):
        self.announcement_provider = announcement_provider
        self.news_provider = news_provider
        self.announcement_repository = announcement_repository
        self.news_repository = news_repository
        self.price_history_provider = price_history_provider
        self.financial_metrics_provider = financial_metrics_provider
        self.quote_snapshot_provider = quote_snapshot_provider
        self.company_profile_provider = company_profile_provider
        self.price_history_repository = price_history_repository
        self.financial_metrics_repository = financial_metrics_repository
        self.quote_snapshot_repository = quote_snapshot_repository
        self.company_profile_repository = company_profile_repository

    def sync_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        industry: str | None = None,
        synced_at: datetime | None = None,
    ) -> StockSyncResult:
        warnings: list[str] = []
        is_fund_like = self._is_fund_like(industry)

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
        ) if not is_fund_like else {"items": [], "warnings": []}
        news_fetch = self._normalize_fetch_result(
            self.news_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
                since=latest_news_at,
            )
        ) if not is_fund_like else {"items": [], "warnings": []}
        warnings.extend(announcement_fetch["warnings"])
        warnings.extend(news_fetch["warnings"])

        persisted_announcements = self._persist_many(
            repository=self.announcement_repository,
            items=announcement_fetch["items"],
            warning_prefix="announcement persistence failed",
            warnings=warnings,
            commit=False,
        )
        persisted_news_items = self._persist_many(
            repository=self.news_repository,
            items=news_fetch["items"],
            warning_prefix="news persistence failed",
            warnings=warnings,
            commit=False,
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
        ) if self.financial_metrics_provider is not None and not is_fund_like else {"items": [], "warnings": []}
        quote_snapshot_fetch = self._normalize_single_fetch_result(
            self.quote_snapshot_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
            )
        ) if self.quote_snapshot_provider is not None else {"item": None, "warnings": []}
        company_profile_fetch = self._normalize_single_fetch_result(
            self.company_profile_provider.fetch_for_security(
                security_id,
                stock_code=stock_code,
                market=market,
            )
        ) if self.company_profile_provider is not None and not is_fund_like else {"item": None, "warnings": []}
        warnings.extend(price_history_fetch["warnings"])
        warnings.extend(financial_metrics_fetch["warnings"])
        warnings.extend(quote_snapshot_fetch["warnings"])
        warnings.extend(company_profile_fetch["warnings"])

        persisted_price_history = self._persist_many(
            repository=self.price_history_repository,
            items=price_history_fetch["items"],
            warning_prefix="price history persistence failed",
            warnings=warnings,
            commit=False,
        )
        persisted_financial_metrics = self._persist_many(
            repository=self.financial_metrics_repository,
            items=financial_metrics_fetch["items"],
            warning_prefix="financial metrics persistence failed",
            warnings=warnings,
            commit=False,
        )
        persisted_quote_snapshot = self._persist_many(
            repository=self.quote_snapshot_repository,
            items=[quote_snapshot_fetch["item"]] if quote_snapshot_fetch["item"] is not None else [],
            warning_prefix="quote snapshot persistence failed",
            warnings=warnings,
            commit=False,
        )
        persisted_company_profile = self._persist_one(
            repository=self.company_profile_repository,
            item=company_profile_fetch["item"],
            warning_prefix="company profile persistence failed",
            warnings=warnings,
            commit=False,
        )
        self._commit_repositories(
            self.announcement_repository,
            self.news_repository,
            self.price_history_repository,
            self.financial_metrics_repository,
            self.quote_snapshot_repository,
            self.company_profile_repository,
        )

        return StockSyncResult(
            synced=True,
            announcements_upserted=len(persisted_announcements),
            news_items_upserted=len(persisted_news_items),
            price_bars_upserted=len(persisted_price_history),
            financial_metrics_upserted=len(persisted_financial_metrics),
            quote_snapshot_updated=len(persisted_quote_snapshot) > 0,
            company_profile_updated=persisted_company_profile is not None,
            warnings=warnings,
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

    @staticmethod
    def _persist_many(
        *,
        repository: Any | None,
        items: list[Any],
        warning_prefix: str,
        warnings: list[str],
        commit: bool,
    ) -> list[Any]:
        if repository is None or not items:
            return []

        session = getattr(repository, "session", None)
        transaction = session.begin_nested() if session is not None and not commit else nullcontext()
        try:
            with transaction:
                return list(repository.upsert_many(items, commit=commit))
        except Exception as exc:
            warnings.append(f"{warning_prefix}: {type(exc).__name__}: {exc}")
            return []

    @staticmethod
    def _persist_one(
        *,
        repository: Any | None,
        item: Any,
        warning_prefix: str,
        warnings: list[str],
        commit: bool,
    ) -> Any | None:
        if repository is None or item is None:
            return None

        session = getattr(repository, "session", None)
        transaction = session.begin_nested() if session is not None and not commit else nullcontext()
        try:
            with transaction:
                return repository.upsert(item, commit=commit)
        except Exception as exc:
            warnings.append(f"{warning_prefix}: {type(exc).__name__}: {exc}")
            return None

    @staticmethod
    def _commit_repositories(*repositories: Any | None) -> None:
        for repository in repositories:
            session = getattr(repository, "session", None)
            if session is not None:
                session.commit()
                return

    @staticmethod
    def _is_fund_like(industry: str | None) -> bool:
        if industry is None:
            return False
        normalized = industry.strip()
        return normalized in {"基金", "指数"}

    @staticmethod
    def _is_index(industry: str | None) -> bool:
        if industry is None:
            return False
        return industry.strip() == "指数"
