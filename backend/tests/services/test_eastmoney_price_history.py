from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.providers.eastmoney_price_history import EastmoneyPriceHistorySource
from app.services.providers.raw_types import RawPriceBar



def test_eastmoney_price_history_source_maps_klines_to_raw_price_bars():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "klines": [
                        "2026-03-11,10.5000,10.7000,10.8000,10.4000,1000000,10700000",
                        "2026-03-10,10.1000,10.2000,10.3000,10.0000,900000,9180000",
                    ]
                }
            },
        )
    )

    source = EastmoneyPriceHistorySource(transport=transport)

    result = source.fetch(" 600519 ", " sh ")

    assert result == [
        RawPriceBar(
            trade_date=date(2026, 3, 11),
            open_price=Decimal("10.5000"),
            high_price=Decimal("10.8000"),
            low_price=Decimal("10.4000"),
            close_price=Decimal("10.7000"),
            volume=Decimal("1000000"),
            amount=Decimal("10700000"),
        ),
        RawPriceBar(
            trade_date=date(2026, 3, 10),
            open_price=Decimal("10.1000"),
            high_price=Decimal("10.3000"),
            low_price=Decimal("10.0000"),
            close_price=Decimal("10.2000"),
            volume=Decimal("900000"),
            amount=Decimal("9180000"),
        ),
    ]



def test_eastmoney_price_history_source_raises_clear_error_for_missing_klines():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": {}})
    )

    source = EastmoneyPriceHistorySource(transport=transport)

    with pytest.raises(ValueError, match="price history payload missing data.klines"):
        source.fetch("600519", "sh")



def test_eastmoney_price_history_source_raises_clear_error_for_null_data():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": None})
    )

    source = EastmoneyPriceHistorySource(transport=transport)

    with pytest.raises(ValueError, match="price history payload missing data.klines"):
        source.fetch("600519", "sh")
