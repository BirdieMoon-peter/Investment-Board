from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from app.db.models import CompanyProfile, FinancialMetrics, PriceHistory, QuoteSnapshot
from app.services.providers.fetch_provenance import SourceAttempt, safe_error_code
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
    price_basis: str = "unknown"
    volume_unit: str | None = None
    amount_available: bool | None = None


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
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str | None = None
    price_basis: str = "unknown"
    unit: str | None = None
    frequency: str | None = None
    volume_unit: str | None = None
    amount_available: bool | None = None


@dataclass(frozen=True)
class FinancialMetricsFetchResult:
    items: list[FinancialMetrics]
    warnings: list[str]
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str | None = None
    price_basis: str = "unknown"
    unit: str | None = None
    frequency: str | None = None
    volume_unit: str | None = None
    amount_available: bool | None = None
    quality_issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class QuoteSnapshotFetchResult:
    item: QuoteSnapshot | None
    warnings: list[str]
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str | None = None
    price_basis: str = "unknown"
    unit: str | None = None
    frequency: str | None = None
    volume_unit: str | None = None
    amount_available: bool | None = None


@dataclass(frozen=True)
class CompanyProfileFetchResult:
    item: CompanyProfile | None
    warnings: list[str]
    attempts: tuple[SourceAttempt, ...] = ()
    source_key: str | None = None
    price_basis: str = "unknown"
    unit: str | None = None
    frequency: str | None = None
    volume_unit: str | None = None
    amount_available: bool | None = None


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
        attempts = []
        selected = None
        basis, volume_unit, amount_available = "unknown", None, None
        for source in self.raw_sources:
            received = 0
            started = datetime.now(UTC)
            try:
                raw_items = list(source.provider.fetch(stock_code, market, limit=limit))
                received = len(raw_items)
                new_items = [_price_history_from_raw(security_id, item) for item in raw_items]
                _validate_price_history(new_items)
                unit = source.volume_unit or getattr(source.provider, "volume_unit", None)
                if unit == "lots":
                    for item in new_items:
                        item.volume *= 100
                    unit = "shares"
                attempts.append(SourceAttempt(source.name, "succeeded" if new_items else "empty", len(new_items), started_at=started, finished_at=datetime.now(UTC)))
                if new_items:
                    items = new_items
                    selected = source.name
                    basis = source.price_basis if source.price_basis != "unknown" else getattr(source.provider, "price_basis", "unknown")
                    volume_unit = unit
                    amount_available = source.amount_available if source.amount_available is not None else getattr(source.provider, "amount_available", None)
                    break
            except Exception as exc:
                attempts.append(SourceAttempt(source.name, "failed", count=getattr(exc, "received_count", received), error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                warnings.append(_warning_message(source.name, exc, stock_code=stock_code, market=market))
        return PriceHistoryFetchResult(_deduplicate_price_history(items), warnings,
            attempts=tuple(attempts), source_key=selected, price_basis=basis,
            unit="CNY", frequency="daily", volume_unit=volume_unit, amount_available=amount_available)


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
        attempts = []
        for source in self.raw_sources:
            received = 0
            started = datetime.now(UTC)
            try:
                raw_items = list(source.provider.fetch(stock_code, market, limit=limit))
                received = len(raw_items)
                new_items = [_financial_metrics_from_raw(security_id, item) for item in raw_items]
                _validate_financial_metrics(new_items)
                items.extend(new_items)
                attempts.append(SourceAttempt(source.name, "succeeded" if new_items else "empty", len(new_items), started_at=started, finished_at=datetime.now(UTC)))
            except Exception as exc:
                attempts.append(SourceAttempt(source.name, "failed", count=getattr(exc, "received_count", received), error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                warnings.append(_warning_message(source.name, exc, stock_code=stock_code, market=market))
        successful = [x.source_key for x in attempts if x.state == "succeeded"]
        return FinancialMetricsFetchResult(_deduplicate_financial_metrics(items), warnings,
            attempts=tuple(attempts), source_key=successful[0] if len(successful) == 1 else None,
            frequency="quarterly", quality_issues=("negative_revenue",) if any(item.revenue is not None and item.revenue < 0 for item in items) else ())


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
        attempts = []
        selected = None

        for source in self.raw_sources:
            received = 0
            started = datetime.now(UTC)
            try:
                raw_item = source.provider.fetch(stock_code, market)
                received = int(raw_item is not None)
                if raw_item is None:
                    attempts.append(SourceAttempt(source.name, "empty", started_at=started, finished_at=datetime.now(UTC)))
                    continue
                candidate = _quote_snapshot_from_raw(security_id, raw_item)
                _validate_quote_snapshot(candidate)
                attempts.append(SourceAttempt(source.name, "succeeded", 1, observed_at=candidate.snapshot_time, started_at=started, finished_at=datetime.now(UTC)))
                if item is None:
                    item = candidate
                    selected = source.name
            except Exception as exc:
                attempts.append(SourceAttempt(source.name, "failed", count=getattr(exc, "received_count", received), error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                warnings.append(
                    _warning_message(source.name, exc, stock_code=stock_code, market=market)
                )

        return QuoteSnapshotFetchResult(item=item, warnings=warnings, attempts=tuple(attempts), source_key=selected, unit="CNY", frequency="intraday")


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
        attempts = []
        selected = None

        for source in self.raw_sources:
            received = 0
            started = datetime.now(UTC)
            try:
                raw_item = source.provider.fetch(stock_code, market)
                received = int(raw_item is not None)
                if raw_item is None or all(getattr(raw_item, field) is None for field in raw_item.__dataclass_fields__):
                    attempts.append(SourceAttempt(source.name, "empty", started_at=started, finished_at=datetime.now(UTC)))
                    continue
                candidate = _company_profile_from_raw(security_id, raw_item)
                attempts.append(SourceAttempt(source.name, "succeeded", 1, started_at=started, finished_at=datetime.now(UTC)))
                if item is None:
                    item = candidate
                    selected = source.name
            except Exception as exc:
                attempts.append(SourceAttempt(source.name, "failed", count=getattr(exc, "received_count", received), error_code=safe_error_code(exc), started_at=started, finished_at=datetime.now(UTC)))
                warnings.append(
                    _warning_message(source.name, exc, stock_code=stock_code, market=market)
                )

        return CompanyProfileFetchResult(item=item, warnings=warnings, attempts=tuple(attempts), source_key=selected)


def _warning_message(
    source_name: str,
    exc: Exception,
    *,
    stock_code: str,
    market: str,
) -> str:
    return f"{source_name} failed (stock={market}:{stock_code}): {safe_error_code(exc)}"


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
    if any(not Decimal(str(value)).is_finite() for value in (item.last_price, item.change_amount, item.change_percent)) or item.last_price <= 0:
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


def _validate_price_history(items: list[PriceHistory]) -> None:
    by_date = {}
    dates = [item.trade_date for item in items]
    if dates != sorted(dates) and dates != sorted(dates, reverse=True):
        raise ValueError("Unordered price history")
    for item in items:
        prices = [item.open_price, item.high_price, item.low_price, item.close_price]
        if not isinstance(item.trade_date, date) or item.trade_date > datetime.now(UTC).date():
            raise ValueError("Invalid trade date")
        if any(not Decimal(str(value)).is_finite() or value <= 0 for value in prices):
            raise ValueError("Invalid price")
        if item.low_price > min(item.open_price, item.close_price) or item.high_price < max(item.open_price, item.close_price) or item.low_price > item.high_price:
            raise ValueError("Invalid OHLC")
        if any(not Decimal(str(value)).is_finite() or value < 0 for value in (item.volume, item.amount)):
            raise ValueError("Invalid volume or amount")
        values = tuple(prices + [item.volume, item.amount])
        if item.trade_date in by_date and by_date[item.trade_date] != values:
            raise ValueError("Conflicting duplicate trade date")
        by_date[item.trade_date] = values


def _validate_financial_metrics(items: list[FinancialMetrics]) -> None:
    for item in items:
        values = (item.revenue, item.net_profit, item.eps, item.roe, item.debt_to_asset_ratio)
        if not item.report_period or any(v is not None and not Decimal(str(v)).is_finite() for v in values):
            raise ValueError("Invalid financial metrics")
