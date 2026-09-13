from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from app.services.providers.eastmoney_intraday_quote_snapshot import EastmoneyIntradayQuoteSnapshotSource



def test_eastmoney_intraday_quote_snapshot_derives_latest_snapshot() -> None:
    payload = {
        "data": {
            "prePrice": 103.03,
            "klines": [
                "2026-03-23 09:35,104.95,104.89,105.27,104.89,27977,293895536.00,0.36,0.01,0.01,0.08",
                "2026-03-23 09:36,104.90,105.60,105.60,104.89,15171,159773720.00,0.68,0.68,0.71,0.04",
            ],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    source = EastmoneyIntradayQuoteSnapshotSource(transport=httpx.MockTransport(handler))

    result = source.fetch("002594", "SZ")

    assert result.last_price == Decimal("105.60")
    assert result.change_amount == Decimal("2.5700")
    assert result.change_percent == Decimal("2.4944")
    assert result.snapshot_time == datetime(2026, 3, 23, 1, 36, tzinfo=timezone.utc)



def test_eastmoney_intraday_quote_snapshot_falls_back_to_quote_fields_when_klines_are_missing() -> None:
    payload = {
        "data": {
            "prePrice": 103.03,
            "f43": 842,
            "f169": -36,
            "f170": -410,
            "f124": "20260323150936",
            "klines": [],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    source = EastmoneyIntradayQuoteSnapshotSource(transport=httpx.MockTransport(handler))

    result = source.fetch("002594", "SZ")

    assert result.last_price == Decimal("8.4200")
    assert result.change_amount == Decimal("-0.3600")
    assert result.change_percent == Decimal("-4.1000")
    assert result.snapshot_time == datetime(2026, 3, 23, 7, 9, 36, tzinfo=timezone.utc)


@pytest.mark.parametrize("data", [
    {"prePrice": 103.03, "f169": -36, "f170": -410, "klines": []},
    {"f43": 842, "f169": -36, "f170": -410, "klines": []},
])
def test_intraday_rejects_incoherent_or_undated_fallback(data):
    source = EastmoneyIntradayQuoteSnapshotSource(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"data": data}))
    )
    with pytest.raises(ValueError):
        source.fetch("002594", "SZ")


def test_intraday_complete_quote_fallback_respects_fund_precision():
    source = EastmoneyIntradayQuoteSnapshotSource(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json={"data": {"klines": [], "f43": 1682, "f169": -28, "f170": -164, "f59": 3, "f124": "20260911150000"}}
    )))
    quote = source.fetch("164701", "SZ")
    assert quote.last_price == Decimal("1.682")
    assert quote.change_amount == Decimal("-0.028")
    assert quote.change_percent == Decimal("-1.64")
