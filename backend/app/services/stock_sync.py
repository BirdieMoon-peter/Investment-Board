from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from app.services.providers.fetch_provenance import SourceAttempt, safe_error_code
from app.services.providers.stock_data_providers import _validate_price_history, _validate_quote_snapshot, _validate_financial_metrics
from app.db.models import PriceHistory, FinancialMetrics, QuoteSnapshot, CompanyProfile
from app.db.models.data_management import DataSource

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
    category_outcomes: dict[str, str] = field(default_factory=dict)


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
        ingestion_recorder: Any | None = None,
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
        self.ingestion_recorder = ingestion_recorder

    CATEGORIES = ("announcements", "news", "price_history", "financial_metrics", "quote_snapshot", "company_profile")

    def sync_security(
        self, security_id: int, *, stock_code: str, market: str,
        industry: str | None = None, synced_at: datetime | None = None,
        categories: list[str] | tuple[str, ...] | None = None,
    ) -> StockSyncResult:
        if categories is not None and (isinstance(categories, (str, bytes)) or any(c not in self.CATEGORIES for c in categories)):
            raise ValueError("Invalid sync category")
        requested = self.CATEGORIES if categories is None else tuple(dict.fromkeys(categories))
        warnings, outcomes, counts = [], {}, {}
        now = synced_at or utc_now()
        touched_sessions = []
        for category in requested:
            prefix = {"announcements": "announcement", "news": "news", "price_history": "price history", "financial_metrics": "financial metrics", "quote_snapshot": "quote snapshot", "company_profile": "company profile"}[category]
            attribute = {"announcements": "announcement", "news": "news"}.get(category, category)
            provider = getattr(self, attribute + "_provider")
            repository = getattr(self, attribute + "_repository")
            fetch, persisted, issues, basis, error = None, [], [], None, None
            outcome = "skipped"
            started = utc_now()
            finished = started
            applicable = not (self._is_fund_like(industry) and category in {"announcements", "news", "financial_metrics", "company_profile"})
            if not applicable:
                outcome = "not_applicable"
            elif provider is not None:
                try:
                    kwargs = dict(stock_code=stock_code, market=market)
                    if category in {"announcements", "news"}:
                        kwargs["since"] = self._normalize_since_utc(repository.get_latest_published_at(security_id))
                    fetch = provider.fetch_for_security(security_id, **kwargs)
                    finished = utc_now()
                    warnings.extend(getattr(fetch, "warnings", []))
                    issues.extend(getattr(fetch, "quality_issues", ()))
                    if category in {"quote_snapshot", "company_profile"}:
                        item = getattr(fetch, "item", fetch)
                        items = [item] if item is not None else []
                    else:
                        items = list(getattr(fetch, "items", fetch))
                    attempts = tuple(getattr(fetch, "attempts", ()))
                    outcome = "empty" if not items else "succeeded"
                    if not items and any(a.state == "failed" for a in attempts):
                        outcome, error = "failed_fetch", "provider_unavailable"
                    elif items and any(a.state == "failed" for a in attempts):
                        outcome = "partial"
                except Exception as exc:
                    finished = utc_now()
                    outcome, error = "failed_fetch", safe_error_code(exc)
                    warnings.append(f"{prefix} fetch failed: {error}")
                    items = []
            else:
                items = []
            if outcome in {"succeeded", "partial"}:
                try:
                    for row in items:
                        if hasattr(row, "security_id") and row.security_id != security_id:
                            raise ValueError("Security mismatch")
                    if category == "price_history" and items and isinstance(items[0], PriceHistory):
                        _validate_price_history(items)
                    elif category == "quote_snapshot" and isinstance(items[0], QuoteSnapshot):
                        _validate_quote_snapshot(items[0])
                    elif category == "financial_metrics" and isinstance(items[0], FinancialMetrics):
                        _validate_financial_metrics(items)
                        if any(item.revenue is not None and item.revenue < 0 for item in items):
                            issues.append("negative_revenue")
                    elif category == "company_profile" and isinstance(items[0], CompanyProfile):
                        fields = ("full_name", "english_name", "registered_capital", "establishment_date", "website", "main_business", "employees")
                        if all(getattr(items[0], field) is None for field in fields):
                            raise ValueError("Empty company profile")
                except Exception:
                    outcome, error = "failed_fetch", "invalid_data"
                    warnings.append(f"{prefix} fetch failed: invalid_data")
            if outcome in {"succeeded", "partial"}:
                session = getattr(repository, "session", None)
                if session is not None and session not in touched_sessions:
                    touched_sessions.append(session)
                try:
                    if repository is None:
                        raise ValueError("Missing persistence repository")
                    if category == "price_history" and items and isinstance(items[0], PriceHistory):
                        items = list({i.trade_date: i for i in items}.values())
                        basis, price_issues = self._price_integrity(security_id, repository, fetch, items)
                        issues.extend(price_issues)
                        if "incomplete_price_refresh" in issues:
                            raise ValueError("Incomplete price refresh")
                    if session is not None:
                        connection = session.connection()
                        if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
                            connection.exec_driver_sql("BEGIN")
                    with session.begin_nested() if session is not None else nullcontext():
                        if category == "company_profile":
                            row = repository.upsert(items[0], commit=False)
                            persisted = [row] if row is not None else []
                        else:
                            persisted = list(repository.upsert_many(items, commit=False))
                        if len(persisted) != len(items):
                            raise ValueError("Incomplete persistence")
                        if self.ingestion_recorder is not None:
                            self.ingestion_recorder.record(security_id, category, outcome=outcome,
                                fetch=fetch, persisted=persisted, fetched_at=finished, price_basis=basis, issues=tuple(issues), started_at=started, finished_at=finished)
                except Exception as exc:
                    persisted = []
                    outcome, error = "failed_persist", safe_error_code(exc)
                    warnings.append(f"{prefix} persistence failed: {error}")
            if self.ingestion_recorder is not None and not persisted:
                self.ingestion_recorder.record(security_id, category, outcome=outcome,
                    fetch=fetch, fetched_at=finished, issues=tuple(issues), error_code=error, started_at=started, finished_at=finished)
            outcomes[category], counts[category] = outcome, len(persisted)
        if self.ingestion_recorder is not None:
            recorder_session = self.ingestion_recorder.repository.session
            if recorder_session not in touched_sessions:
                touched_sessions.append(recorder_session)
        for session in touched_sessions:
            try:
                session.commit()
            except Exception as exc:
                session.rollback()
                warnings.append(f"sync persistence failed: {safe_error_code(exc)}")
                for category in requested:
                    if counts.get(category):
                        counts[category], outcomes[category] = 0, "failed_persist"
        return StockSyncResult(synced=True,
            announcements_upserted=counts.get("announcements", 0), news_items_upserted=counts.get("news", 0),
            price_bars_upserted=counts.get("price_history", 0), financial_metrics_upserted=counts.get("financial_metrics", 0),
            quote_snapshot_updated=bool(counts.get("quote_snapshot")), company_profile_updated=bool(counts.get("company_profile")),
            warnings=warnings, synced_at=now, category_outcomes=outcomes)

    def _price_integrity(self, security_id, repository, fetch, items):
        basis = getattr(fetch, "price_basis", "unknown")
        issues = []
        if getattr(fetch, "volume_unit", None) != "shares":
            issues.append("volume_unit_unknown")
        if getattr(fetch, "amount_available", None) is False:
            issues.append("amount_unavailable")
        reader = getattr(repository, "list_recent_by_security_id", None)
        existing = reader(security_id, limit=1000000) if reader else []
        old_dataset = self.ingestion_recorder.repository.get_dataset(security_id, "price_history") if self.ingestion_recorder else None
        old_basis = old_dataset.price_basis if old_dataset else "unknown"
        new_dates = {i.trade_date for i in items}
        covers_existing = all(i.trade_date in new_dates for i in existing)
        if not covers_existing:
            # Corporate actions can revise every historical forward-adjusted value.
            # Subsets cannot certify untouched old rows, even from the same source.
            selected = getattr(fetch, "source_key", None)
            old_source = self.ingestion_recorder.repository.session.get(DataSource, old_dataset.source_id) if self.ingestion_recorder and old_dataset and old_dataset.source_id else None
            source_changed = selected is not None and (old_source is None or old_source.source_key != selected)
            if old_basis != "unknown" or basis != "unknown" or source_changed:
                issues.append("incomplete_price_refresh")
            basis = "unknown"
        if basis == "unknown":
            issues.append("price_basis_unknown")
        return basis, issues

    @staticmethod
    def _normalize_since_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

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
