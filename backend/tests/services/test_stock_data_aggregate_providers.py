from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from app.db.models import CompanyProfile, FinancialMetrics, PriceHistory, QuoteSnapshot
from app.services.providers.raw_types import RawCompanyProfile, RawFinancialMetrics, RawPriceBar, RawQuoteSnapshot
from app.services.providers.stock_data_providers import (
    AggregateCompanyProfileProvider,
    AggregateFinancialMetricsProvider,
    AggregatePriceHistoryProvider,
    AggregateQuoteSnapshotProvider,
    RawCompanyProfileSourceAdapter,
    RawFinancialMetricsSourceAdapter,
    RawPriceHistorySourceAdapter,
    RawQuoteSnapshotSourceAdapter,
)


@dataclass
class SuccessfulPriceHistorySource:
    items: list[RawPriceBar]
    expected_stock_code: str
    expected_market: str
    expected_limit: int

    def fetch(self, stock_code: str, market: str, *, limit: int = 60) -> list[RawPriceBar]:
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        assert limit == self.expected_limit
        return self.items


@dataclass
class SuccessfulFinancialMetricsSource:
    items: list[RawFinancialMetrics]
    expected_stock_code: str
    expected_market: str
    expected_limit: int

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        limit: int = 8,
    ) -> list[RawFinancialMetrics]:
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        assert limit == self.expected_limit
        return self.items


@dataclass
class SuccessfulCompanyProfileSource:
    item: RawCompanyProfile
    expected_stock_code: str
    expected_market: str

    def fetch(self, stock_code: str, market: str) -> RawCompanyProfile:
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        return self.item


class FailingPriceHistorySource:
    def fetch(self, stock_code: str, market: str, *, limit: int = 60) -> list[RawPriceBar]:
        raise RuntimeError("upstream price history unavailable")


def test_aggregate_price_history_provider_returns_empty_when_all_sources_fail():
    provider = AggregatePriceHistoryProvider(
        raw_sources=[
            RawPriceHistorySourceAdapter("eastmoney", FailingPriceHistorySource()),
            RawPriceHistorySourceAdapter("backup", FailingPriceHistorySource()),
        ],
        fallback_enabled=False,
    )

    result = provider.fetch_for_security(1, stock_code="000001", market="SZ")

    assert result.items == []
    assert result.warnings == [
        "eastmoney failed (stock=SZ:000001): RuntimeError: upstream price history unavailable",
        "backup failed (stock=SZ:000001): RuntimeError: upstream price history unavailable",
    ]


class FailingFinancialMetricsSource:
    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        limit: int = 8,
    ) -> list[RawFinancialMetrics]:
        raise RuntimeError("upstream financial metrics unavailable")


class FailingCompanyProfileSource:
    def fetch(self, stock_code: str, market: str) -> RawCompanyProfile:
        raise ValueError("upstream company profile unavailable")


@dataclass
class SuccessfulQuoteSnapshotSource:
    item: RawQuoteSnapshot
    expected_stock_code: str
    expected_market: str

    def fetch(self, stock_code: str, market: str) -> RawQuoteSnapshot:
        assert stock_code == self.expected_stock_code
        assert market == self.expected_market
        return self.item


class FailingQuoteSnapshotSource:
    def fetch(self, stock_code: str, market: str) -> RawQuoteSnapshot:
        raise RuntimeError("upstream quote snapshot unavailable")


def test_aggregate_price_history_provider_converts_raw_bars_to_models():
    provider = AggregatePriceHistoryProvider(
        raw_sources=[
            RawPriceHistorySourceAdapter(
                "eastmoney",
                SuccessfulPriceHistorySource(
                    items=[
                        RawPriceBar(
                            trade_date=date(2026, 3, 10),
                            open_price=Decimal("10.5000"),
                            high_price=Decimal("10.8000"),
                            low_price=Decimal("10.4000"),
                            close_price=Decimal("10.7000"),
                            volume=Decimal("1000000.0000"),
                            amount=Decimal("10700000.0000"),
                        )
                    ],
                    expected_stock_code="000001",
                    expected_market="SZ",
                    expected_limit=10000,
                ),
            )
        ],
    )

    result = provider.fetch_for_security(
        1,
        stock_code="000001",
        market="SZ",
        limit=10000,
    )

    assert result.warnings == []
    assert len(result.items) == 1
    item = result.items[0]
    assert item.security_id == 1
    assert item.trade_date == date(2026, 3, 10)
    assert item.open_price == Decimal("10.5000")
    assert item.high_price == Decimal("10.8000")
    assert item.low_price == Decimal("10.4000")
    assert item.close_price == Decimal("10.7000")
    assert item.volume == Decimal("1000000.0000")
    assert item.amount == Decimal("10700000.0000")



def test_aggregate_price_history_provider_stops_after_first_successful_source():
    provider = AggregatePriceHistoryProvider(
        raw_sources=[
            RawPriceHistorySourceAdapter(
                "eastmoney",
                SuccessfulPriceHistorySource(
                    items=[
                        RawPriceBar(
                            trade_date=date(2026, 3, 10),
                            open_price=Decimal("10.5000"),
                            high_price=Decimal("10.8000"),
                            low_price=Decimal("10.4000"),
                            close_price=Decimal("10.7000"),
                            volume=Decimal("1000000.0000"),
                            amount=Decimal("10700000.0000"),
                        )
                    ],
                    expected_stock_code="000001",
                    expected_market="SZ",
                    expected_limit=10000,
                ),
            ),
            RawPriceHistorySourceAdapter("backup", FailingPriceHistorySource()),
        ]
    )

    result = provider.fetch_for_security(1, stock_code="000001", market="SZ")

    assert len(result.items) == 1
    assert result.items[0].close_price == Decimal("10.7000")
    # backup source is never called because primary succeeded
    assert result.warnings == []



def test_aggregate_price_history_provider_falls_through_to_backup_when_primary_fails():
    provider = AggregatePriceHistoryProvider(
        raw_sources=[
            RawPriceHistorySourceAdapter("primary", FailingPriceHistorySource()),
            RawPriceHistorySourceAdapter(
                "backup",
                SuccessfulPriceHistorySource(
                    items=[
                        RawPriceBar(
                            trade_date=date(2026, 3, 10),
                            open_price=Decimal("10.5000"),
                            high_price=Decimal("10.8000"),
                            low_price=Decimal("10.4000"),
                            close_price=Decimal("10.7000"),
                            volume=Decimal("1000000.0000"),
                            amount=Decimal("10700000.0000"),
                        ),
                        RawPriceBar(
                            trade_date=date(2026, 3, 9),
                            open_price=Decimal("10.2000"),
                            high_price=Decimal("10.4000"),
                            low_price=Decimal("10.1000"),
                            close_price=Decimal("10.3000"),
                            volume=Decimal("900000.0000"),
                            amount=Decimal("9270000.0000"),
                        ),
                    ],
                    expected_stock_code="000001",
                    expected_market="SZ",
                    expected_limit=10000,
                ),
            ),
        ]
    )

    result = provider.fetch_for_security(1, stock_code="000001", market="SZ")

    assert [item.trade_date for item in result.items] == [date(2026, 3, 10), date(2026, 3, 9)]
    assert result.items[0].close_price == Decimal("10.7000")
    assert result.warnings == [
        "primary failed (stock=SZ:000001): RuntimeError: upstream price history unavailable"
    ]



def test_aggregate_financial_metrics_provider_converts_raw_metrics_to_models():
    provider = AggregateFinancialMetricsProvider(
        raw_sources=[
            RawFinancialMetricsSourceAdapter(
                "eastmoney",
                SuccessfulFinancialMetricsSource(
                    items=[
                        RawFinancialMetrics(
                            report_period="2025Q4",
                            revenue=Decimal("1000000000.0000"),
                            net_profit=Decimal("100000000.0000"),
                            eps=Decimal("1.2500"),
                            roe=Decimal("0.150000"),
                            debt_to_asset_ratio=Decimal("0.450000"),
                        )
                    ],
                    expected_stock_code="000001",
                    expected_market="SZ",
                    expected_limit=4,
                ),
            )
        ],
    )

    result = provider.fetch_for_security(
        3,
        stock_code="000001",
        market="SZ",
        limit=4,
    )

    assert result.warnings == []
    assert len(result.items) == 1
    item = result.items[0]
    assert item.security_id == 3
    assert item.report_period == "2025Q4"
    assert item.revenue == Decimal("1000000000.0000")
    assert item.net_profit == Decimal("100000000.0000")
    assert item.eps == Decimal("1.2500")
    assert item.roe == Decimal("0.150000")
    assert item.debt_to_asset_ratio == Decimal("0.450000")



def test_aggregate_financial_metrics_provider_keeps_partial_success_and_warnings():
    provider = AggregateFinancialMetricsProvider(
        raw_sources=[
            RawFinancialMetricsSourceAdapter(
                "primary",
                SuccessfulFinancialMetricsSource(
                    items=[
                        RawFinancialMetrics(
                            report_period="2025Q4",
                            revenue=Decimal("1000000000.0000"),
                            net_profit=Decimal("100000000.0000"),
                            eps=Decimal("1.2500"),
                            roe=Decimal("0.150000"),
                            debt_to_asset_ratio=Decimal("0.450000"),
                        )
                    ],
                    expected_stock_code="000001",
                    expected_market="SZ",
                    expected_limit=8,
                ),
            ),
            RawFinancialMetricsSourceAdapter("backup", FailingFinancialMetricsSource()),
        ],
    )

    result = provider.fetch_for_security(3, stock_code="000001", market="SZ")

    assert len(result.items) == 1
    assert result.items[0].report_period == "2025Q4"
    assert result.warnings == [
        "backup failed (stock=SZ:000001): RuntimeError: upstream financial metrics unavailable"
    ]



def test_aggregate_financial_metrics_provider_deduplicates_overlapping_periods_and_sorts_descending():
    provider = AggregateFinancialMetricsProvider(
        raw_sources=[
            RawFinancialMetricsSourceAdapter(
                "primary",
                SuccessfulFinancialMetricsSource(
                    items=[
                        RawFinancialMetrics(
                            report_period="2025Q3",
                            revenue=Decimal("800000000.0000"),
                            net_profit=Decimal("80000000.0000"),
                            eps=Decimal("1.0000"),
                            roe=Decimal("0.120000"),
                            debt_to_asset_ratio=Decimal("0.400000"),
                        )
                    ],
                    expected_stock_code="000001",
                    expected_market="SZ",
                    expected_limit=8,
                ),
            ),
            RawFinancialMetricsSourceAdapter(
                "backup",
                SuccessfulFinancialMetricsSource(
                    items=[
                        RawFinancialMetrics(
                            report_period="2025Q4",
                            revenue=Decimal("1000000000.0000"),
                            net_profit=Decimal("100000000.0000"),
                            eps=Decimal("1.2500"),
                            roe=Decimal("0.150000"),
                            debt_to_asset_ratio=Decimal("0.450000"),
                        ),
                        RawFinancialMetrics(
                            report_period="2025Q3",
                            revenue=Decimal("1800000000.0000"),
                            net_profit=Decimal("180000000.0000"),
                            eps=Decimal("2.0000"),
                            roe=Decimal("0.220000"),
                            debt_to_asset_ratio=Decimal("0.500000"),
                        ),
                    ],
                    expected_stock_code="000001",
                    expected_market="SZ",
                    expected_limit=8,
                ),
            ),
        ],
    )

    result = provider.fetch_for_security(3, stock_code="000001", market="SZ")

    assert [item.report_period for item in result.items] == ["2025Q4", "2025Q3"]
    assert result.items[1].eps == Decimal("1.0000")
    assert result.warnings == []



def test_aggregate_quote_snapshot_provider_uses_fallback_when_primary_snapshot_is_invalid():
    provider = AggregateQuoteSnapshotProvider(
        raw_sources=[
            RawQuoteSnapshotSourceAdapter(
                "primary",
                SuccessfulQuoteSnapshotSource(
                    item=RawQuoteSnapshot(
                        last_price=Decimal("103.03"),
                        change_amount=Decimal("0.72"),
                        change_percent=Decimal("0.70"),
                        snapshot_time=datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc),
                    ),
                    expected_stock_code="002594",
                    expected_market="SZ",
                ),
            ),
            RawQuoteSnapshotSourceAdapter(
                "fallback",
                SuccessfulQuoteSnapshotSource(
                    item=RawQuoteSnapshot(
                        last_price=Decimal("110.04"),
                        change_amount=Decimal("7.01"),
                        change_percent=Decimal("6.80"),
                        snapshot_time=datetime(2026, 3, 23, 10, 7, tzinfo=timezone.utc),
                    ),
                    expected_stock_code="002594",
                    expected_market="SZ",
                ),
            ),
        ],
    )

    result = provider.fetch_for_security(6, stock_code="002594", market="SZ")

    assert result.item is not None
    assert result.item.security_id == 6
    assert result.item.last_price == Decimal("110.04")
    assert result.item.snapshot_time == datetime(2026, 3, 23, 10, 7, tzinfo=timezone.utc)
    assert result.warnings == [
        "primary failed (stock=SZ:002594): ValueError: quote snapshot time is invalid"
    ]



def test_aggregate_quote_snapshot_provider_returns_warning_when_all_sources_fail():
    provider = AggregateQuoteSnapshotProvider(
        raw_sources=[
            RawQuoteSnapshotSourceAdapter("primary", FailingQuoteSnapshotSource()),
            RawQuoteSnapshotSourceAdapter("fallback", FailingQuoteSnapshotSource()),
        ]
    )

    result = provider.fetch_for_security(6, stock_code="002594", market="SZ")

    assert result.item is None
    assert result.warnings == [
        "primary failed (stock=SZ:002594): RuntimeError: upstream quote snapshot unavailable",
        "fallback failed (stock=SZ:002594): RuntimeError: upstream quote snapshot unavailable",
    ]



def test_aggregate_company_profile_provider_converts_raw_profile_to_model():
    provider = AggregateCompanyProfileProvider(
        raw_sources=[
            RawCompanyProfileSourceAdapter(
                "eastmoney",
                SuccessfulCompanyProfileSource(
                    item=RawCompanyProfile(
                        full_name="平安银行股份有限公司",
                        english_name="Ping An Bank Co., Ltd.",
                        registered_capital=Decimal("19405918198.0000"),
                        establishment_date=date(1987, 12, 22),
                        website="https://bank.pingan.com",
                        main_business="商业银行业务",
                        employees=35000,
                    ),
                    expected_stock_code="000001",
                    expected_market="SZ",
                ),
            )
        ],
    )

    result = provider.fetch_for_security(
        5,
        stock_code="000001",
        market="SZ",
    )

    assert result.warnings == []
    assert result.item is not None
    assert result.item.security_id == 5
    assert result.item.full_name == "平安银行股份有限公司"
    assert result.item.english_name == "Ping An Bank Co., Ltd."
    assert result.item.registered_capital == Decimal("19405918198.0000")
    assert result.item.establishment_date == date(1987, 12, 22)
    assert result.item.website == "https://bank.pingan.com"
    assert result.item.main_business == "商业银行业务"
    assert result.item.employees == 35000
    assert not hasattr(result.item, "listing_date")
    assert not hasattr(result.item, "business_scope")



def test_aggregate_company_profile_provider_keeps_first_success_and_collects_later_warnings():
    provider = AggregateCompanyProfileProvider(
        raw_sources=[
            RawCompanyProfileSourceAdapter(
                "primary",
                SuccessfulCompanyProfileSource(
                    item=RawCompanyProfile(
                        full_name="平安银行股份有限公司",
                        english_name="Ping An Bank Co., Ltd.",
                        employees=35000,
                    ),
                    expected_stock_code="000001",
                    expected_market="SZ",
                ),
            ),
            RawCompanyProfileSourceAdapter("backup", FailingCompanyProfileSource()),
        ],
    )

    result = provider.fetch_for_security(5, stock_code="000001", market="SZ")

    assert result.item is not None
    assert result.item.full_name == "平安银行股份有限公司"
    assert result.item.employees == 35000
    assert result.warnings == [
        "backup failed (stock=SZ:000001): ValueError: upstream company profile unavailable"
    ]


    provider = AggregateCompanyProfileProvider(
        raw_sources=[RawCompanyProfileSourceAdapter("eastmoney", FailingCompanyProfileSource())],
    )

    result = provider.fetch_for_security(
        5,
        stock_code="000001",
        market="SZ",
    )

    assert result.item is None
    assert result.warnings == [
        "eastmoney failed (stock=SZ:000001): ValueError: upstream company profile unavailable"
    ]
