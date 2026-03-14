from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

import app.services.providers.raw_types as raw_types


def test_raw_price_bar_is_frozen_and_preserves_decimal_values():
    assert hasattr(raw_types, "RawPriceBar")

    bar = raw_types.RawPriceBar(
        trade_date=date(2026, 3, 10),
        open_price=Decimal("10.5000"),
        high_price=Decimal("10.8000"),
        low_price=Decimal("10.4000"),
        close_price=Decimal("10.7000"),
        volume=Decimal("1000000.0000"),
        amount=Decimal("10700000.0000"),
    )

    assert bar.trade_date == date(2026, 3, 10)
    assert bar.close_price == Decimal("10.7000")
    assert bar.volume == Decimal("1000000.0000")

    with pytest.raises(FrozenInstanceError):
        bar.close_price = Decimal("10.9000")


def test_raw_financial_metrics_is_frozen_and_supports_optional_decimals():
    assert hasattr(raw_types, "RawFinancialMetrics")

    metrics = raw_types.RawFinancialMetrics(
        report_period="2025Q4",
        revenue=Decimal("1000000000.0000"),
        net_profit=Decimal("100000000.0000"),
        eps=Decimal("1.2500"),
        roe=Decimal("0.150000"),
        debt_to_asset_ratio=None,
    )

    assert metrics.report_period == "2025Q4"
    assert metrics.eps == Decimal("1.2500")
    assert metrics.debt_to_asset_ratio is None

    with pytest.raises(FrozenInstanceError):
        metrics.report_period = "2024Q4"


def test_raw_company_profile_matches_current_backend_model_fields():
    assert hasattr(raw_types, "RawCompanyProfile")

    profile = raw_types.RawCompanyProfile(
        full_name="平安银行股份有限公司",
        english_name="Ping An Bank Co., Ltd.",
        registered_capital=Decimal("19405918198.0000"),
        establishment_date=date(1987, 12, 22),
        website="https://bank.pingan.com",
        main_business="商业银行业务",
        employees=35000,
    )

    assert profile.full_name == "平安银行股份有限公司"
    assert profile.website == "https://bank.pingan.com"
    assert profile.establishment_date == date(1987, 12, 22)
    assert not hasattr(profile, "listing_date")
    assert not hasattr(profile, "business_scope")

    with pytest.raises(FrozenInstanceError):
        profile.website = "https://example.com"
