from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

import httpx

from app.services.providers.http_client import build_provider_client, retry_request
from app.services.providers.raw_types import RawQuoteSnapshot

_EASTMONEY_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"


class EastmoneyQuoteSnapshotSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(
        self,
        stock_code: str,
        market: str,
    ) -> RawQuoteSnapshot:
        normalized_code = stock_code.strip()
        normalized_market = market.strip().upper()
        secid = _secid(normalized_market, normalized_code)

        with build_provider_client(transport=self._transport) as client:
            response = retry_request(
                client,
                "GET",
                _EASTMONEY_QUOTE_URL,
                params={
                    "secid": secid,
                    "fields": "f43,f59,f169,f170,f124",
                },
            )
            payload = response.json()

        return _parse_quote_snapshot(payload)


def _secid(market: str, code: str) -> str:
    market_map = {"SZ": "0", "SH": "1"}
    market_prefix = market_map.get(market)
    if market_prefix is None:
        raise ValueError(f"unsupported market: {market}")
    if not code:
        raise ValueError("stock code is required")
    return f"{market_prefix}.{code}"


def _parse_quote_snapshot(payload: object) -> RawQuoteSnapshot:
    if not isinstance(payload, dict):
        raise ValueError("Eastmoney quote payload is invalid")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Eastmoney quote payload missing data")

    last_price_raw = data.get("f43")
    change_amount_raw = data.get("f169")
    change_percent_raw = data.get("f170")
    snapshot_time_raw = data.get("f124")

    if last_price_raw is None or change_amount_raw is None or change_percent_raw is None:
        raise ValueError("Eastmoney quote payload missing quote fields")
    if snapshot_time_raw is None:
        raise ValueError("Eastmoney quote payload missing snapshot time")

    price_scale = _price_scale(data.get("f59", 2))

    return RawQuoteSnapshot(
        last_price=_scaled_decimal(last_price_raw, scale=price_scale),
        change_amount=_scaled_decimal(change_amount_raw, scale=price_scale),
        change_percent=_scaled_decimal(change_percent_raw),
        snapshot_time=_parse_snapshot_time(snapshot_time_raw),
    )


def _parse_snapshot_time(value: object) -> datetime:
    if not isinstance(value, (int, float, str)):
        raise ValueError("Eastmoney quote snapshot time is not numeric")

    normalized = str(value).strip()
    if not normalized or normalized == "0":
        raise ValueError("Eastmoney quote payload missing snapshot time")

    if len(normalized) == 14:
        return datetime.strptime(normalized, "%Y%m%d%H%M%S").replace(
            tzinfo=ZoneInfo("Asia/Shanghai")
        ).astimezone(UTC)

    return datetime.fromtimestamp(int(normalized), tz=UTC)


def _scaled_decimal(value: object, *, scale: Decimal = Decimal("100")) -> Decimal:
    if not isinstance(value, (int, float, str)):
        raise ValueError("Eastmoney quote field is not numeric")
    return Decimal(str(value)) / scale


def _price_scale(precision: object) -> Decimal:
    # f59 is the number of decimal places for prices (funds commonly use three).
    # Legacy payloads without f59 retain two decimals; supplied invalid values fail.
    value = str(precision).strip()
    if not value.isdigit() or len(value) > 1 or not 0 <= int(value) <= 8:
        raise ValueError("Eastmoney quote price precision is invalid")
    return Decimal(10) ** int(value)
