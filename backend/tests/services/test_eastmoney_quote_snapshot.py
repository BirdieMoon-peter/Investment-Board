from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from app.services.providers.eastmoney_quote_snapshot import EastmoneyQuoteSnapshotSource



def test_eastmoney_quote_snapshot_parses_compact_datetime_timestamp() -> None:
    payload = {
        "data": {
            "f43": 750,
            "f169": 46,
            "f170": 617,
            "f124": "20260323150936",
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    source = EastmoneyQuoteSnapshotSource(transport=httpx.MockTransport(handler))

    result = source.fetch("601398", "SH")

    assert result.last_price == Decimal("7.5")
    assert result.change_amount == Decimal("0.46")
    assert result.change_percent == Decimal("6.17")
    assert result.snapshot_time == datetime(2026, 3, 23, 7, 9, 36, tzinfo=timezone.utc)



def test_eastmoney_quote_snapshot_parses_unix_timestamp() -> None:
    payload = {
        "data": {
            "f43": 750,
            "f169": 46,
            "f170": 617,
            "f124": 1774249776,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    source = EastmoneyQuoteSnapshotSource(transport=httpx.MockTransport(handler))

    result = source.fetch("601398", "SH")

    assert result.snapshot_time == datetime.fromtimestamp(1774249776, tz=timezone.utc)



@pytest.mark.parametrize("timestamp", [None, "", " ", 0, "0", "0.0", "bad", "20260230150000"])
def test_eastmoney_quote_snapshot_rejects_empty_timestamp(timestamp) -> None:
    payload = {
        "data": {
            "f43": 750,
            "f169": 46,
            "f170": 617,
            "f124": timestamp,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    source = EastmoneyQuoteSnapshotSource(transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError):
        source.fetch("601398", "SH")


@pytest.mark.parametrize("precision, raw_price, raw_change, price, change", [
    (3, 1682, -28, "1.682", "-0.028"),
    ("3", 932, -10, "0.932", "-0.010"),
    (2, 750, 46, "7.50", "0.46"),
])
def test_quote_price_precision_is_requested_and_used(precision, raw_price, raw_change, price, change):
    def handler(request):
        assert "f59" in request.url.params["fields"].split(",")
        return httpx.Response(200, json={"data": {
            "f43": raw_price, "f169": raw_change, "f170": -164,
            "f59": precision, "f124": "20260911150000",
        }})
    result = EastmoneyQuoteSnapshotSource(transport=httpx.MockTransport(handler)).fetch("164701", "SZ")
    assert result.last_price == Decimal(price)
    assert result.change_amount == Decimal(change)
    assert result.change_percent == Decimal("-1.64")


@pytest.mark.parametrize("precision", [None, "", "-", -1, 2.5, "bad", 1000000, True])
def test_quote_rejects_present_but_invalid_precision(precision):
    source = EastmoneyQuoteSnapshotSource(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json={"data": {"f43": 1682, "f169": -28, "f170": -164, "f59": precision, "f124": "20260911150000"}}
    )))
    with pytest.raises(ValueError, match="precision"):
        source.fetch("164701", "SZ")
