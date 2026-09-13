from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from app.db.models import CompanyProfile, FinancialMetrics, PriceHistory, QuoteSnapshot
from app.services.providers.raw_types import RawCompanyProfile, RawFinancialMetrics, RawPriceBar, RawQuoteSnapshot


class RawPriceHistorySource(Protocol):
    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        limit: int = 10000,
    ) -> Iterable[RawPriceBar]: ...


class RawFinancialMetricsSource(Protocol):
    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        limit: int = 8,
    ) -> Iterable[RawFinancialMetrics]: ...


class RawQuoteSnapshotSource(Protocol):
    def fetch(
        self,
        stock_code: str,
        market: str,
    ) -> RawQuoteSnapshot: ...


class RawCompanyProfileSource(Protocol):
    def fetch(
        self,
        stock_code: str,
        market: str,
    ) -> RawCompanyProfile: ...


@dataclass(frozen=True)
class RawPriceHistorySourceAdapter:
    name: str
    provider: RawPriceHistorySource


@dataclass(frozen=True)
class RawFinancialMetricsSourceAdapter:
    name: str
    provider: RawFinancialMetricsSource


@dataclass(frozen=True)
class RawQuoteSnapshotSourceAdapter:
    name: str
    provider: RawQuoteSnapshotSource


@dataclass(frozen=True)
class RawCompanyProfileSourceAdapter:
    name: str
    provider: RawCompanyProfileSource


@dataclass(frozen=True)
class PriceHistoryFetchResult:
    items: list[PriceHistory]
    warnings: list[str]


@dataclass(frozen=True)
class FinancialMetricsFetchResult:
    items: list[FinancialMetrics]
    warnings: list[str]


@dataclass(frozen=True)
class QuoteSnapshotFetchResult:
    item: QuoteSnapshot | None
    warnings: list[str]


@dataclass(frozen=True)
class CompanyProfileFetchResult:
    item: CompanyProfile | None
    warnings: list[str]


class AggregatePriceHistoryProvider:
    def __init__(
        self,
        *,
        raw_sources: list[RawPriceHistorySourceAdapter] | None = None,
        fallback_enabled: bool = False,
    ):
        self.raw_sources = list(raw_sources or [])
        self._fallback_enabled = fallback_enabled

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        limit: int = 10000,
    ) -> PriceHistoryFetchResult:
        items: list[PriceHistory] = []
        warnings: list[str] = []

        for source in self.raw_sources:
            try:
                raw_items = source.provider.fetch(stock_code, market, limit=limit)
                new_items = [_price_history_from_raw(security_id, item) for item in raw_items]
                if new_items:
                    items.extend(new_items)
                    break  # first successful source is enough
            except Exception as exc:
                warnings.append(
                    _warning_message(source.name, exc, stock_code=stock_code, market=market)
                )

        return PriceHistoryFetchResult(items=_deduplicate_price_history(items), warnings=warnings)


class AggregateFinancialMetricsProvider:
    def __init__(
        self,
        *,
        raw_sources: list[RawFinancialMetricsSourceAdapter] | None = None,
    ):
        self.raw_sources = list(raw_sources or [])

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        limit: int = 8,
    ) -> FinancialMetricsFetchResult:
        items: list[FinancialMetrics] = []
        warnings: list[str] = []

        for source in self.raw_sources:
            try:
                raw_items = source.provider.fetch(stock_code, market, limit=limit)
                items.extend(_financial_metrics_from_raw(security_id, item) for item in raw_items)
            except Exception as exc:
                warnings.append(
                    _warning_message(source.name, exc, stock_code=stock_code, market=market)
                )

        return FinancialMetricsFetchResult(
            items=_deduplicate_financial_metrics(items),
            warnings=warnings,
        )


class AggregateQuoteSnapshotProvider:
    def __init__(
        self,
        *,
        raw_sources: list[RawQuoteSnapshotSourceAdapter] | None = None,
    ):
        self.raw_sources = list(raw_sources or [])

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
    ) -> QuoteSnapshotFetchResult:
        item: QuoteSnapshot | None = None
        warnings: list[str] = []

        for source in self.raw_sources:
            try:
                raw_item = source.provider.fetch(stock_code, market)
                candidate = _quote_snapshot_from_raw(security_id, raw_item)
                _validate_quote_snapshot(candidate)
                if item is None:
                    item = candidate
            except Exception as exc:
                warnings.append(
                    _warning_message(source.name, exc, stock_code=stock_code, market=market)
                )

        return QuoteSnapshotFetchResult(item=item, warnings=warnings)


class AggregateCompanyProfileProvider:
    def __init__(
        self,
        *,
        raw_sources: list[RawCompanyProfileSourceAdapter] | None = None,
    ):
        self.raw_sources = list(raw_sources or [])

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
    ) -> CompanyProfileFetchResult:
        item: CompanyProfile | None = None
        warnings: list[str] = []

        for source in self.raw_sources:
            try:
                raw_item = source.provider.fetch(stock_code, market)
                if item is None:
                    item = _company_profile_from_raw(security_id, raw_item)
            except Exception as exc:
                warnings.append(
                    _warning_message(source.name, exc, stock_code=stock_code, market=market)
                )

        return CompanyProfileFetchResult(item=item, warnings=warnings)


def _warning_message(
    source_name: str,
    exc: Exception,
    *,
    stock_code: str,
    market: str,
) -> str:
    exc_msg = str(exc) or "unknown error"
    return f"{source_name} failed (stock={market}:{stock_code}): {type(exc).__name__}: {exc_msg}"


def _price_history_from_raw(security_id: int, item: RawPriceBar) -> PriceHistory:
    return PriceHistory(
        security_id=security_id,
        trade_date=item.trade_date,
        open_price=item.open_price,
        high_price=item.high_price,
        low_price=item.low_price,
        close_price=item.close_price,
        volume=item.volume,
        amount=item.amount,
    )


def _financial_metrics_from_raw(security_id: int, item: RawFinancialMetrics) -> FinancialMetrics:
    return FinancialMetrics(
        security_id=security_id,
        report_period=item.report_period,
        revenue=item.revenue,
        net_profit=item.net_profit,
        eps=item.eps,
        roe=item.roe,
        debt_to_asset_ratio=item.debt_to_asset_ratio,
    )


def _quote_snapshot_from_raw(security_id: int, item: RawQuoteSnapshot) -> QuoteSnapshot:
    return QuoteSnapshot(
        security_id=security_id,
        last_price=item.last_price,
        change_amount=item.change_amount,
        change_percent=item.change_percent,
        snapshot_time=item.snapshot_time,
    )



def _validate_quote_snapshot(item: QuoteSnapshot) -> None:
    if item.last_price <= 0:
        raise ValueError("quote snapshot last price must be positive")

    snapshot_time = item.snapshot_time
    if snapshot_time.tzinfo is None:
        snapshot_time = snapshot_time.replace(tzinfo=UTC)
    else:
        snapshot_time = snapshot_time.astimezone(UTC)

    if snapshot_time <= datetime(2000, 1, 1, tzinfo=UTC):
        raise ValueError("quote snapshot time is invalid")



def _company_profile_from_raw(security_id: int, item: RawCompanyProfile) -> CompanyProfile:
    return CompanyProfile(
        security_id=security_id,
        full_name=item.full_name,
        english_name=item.english_name,
        registered_capital=item.registered_capital,
        establishment_date=item.establishment_date,
        website=item.website,
        main_business=item.main_business,
        employees=item.employees,
    )



def _price_history_key(item: PriceHistory) -> tuple[int, object]:
    return (item.security_id, item.trade_date)



def _financial_metrics_key(item: FinancialMetrics) -> tuple[int, str]:
    return (item.security_id, item.report_period)



def _deduplicate_price_history(items: list[PriceHistory]) -> list[PriceHistory]:
    unique_by_key: dict[tuple[int, object], PriceHistory] = {}
    for item in items:
        unique_by_key.setdefault(_price_history_key(item), item)
    return sorted(
        unique_by_key.values(),
        key=lambda item: (item.trade_date, item.id or 0),
        reverse=True,
    )



def _deduplicate_financial_metrics(items: list[FinancialMetrics]) -> list[FinancialMetrics]:
    unique_by_key: dict[tuple[int, str], FinancialMetrics] = {}
    for item in items:
        unique_by_key.setdefault(_financial_metrics_key(item), item)
    return sorted(
        unique_by_key.values(),
        key=lambda item: (item.report_period, item.id or 0),
        reverse=True,
    )
