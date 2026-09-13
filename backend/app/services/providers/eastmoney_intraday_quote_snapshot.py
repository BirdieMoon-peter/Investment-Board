from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawQuoteSnapshot
from app.services.providers.eastmoney_quote_snapshot import _parse_quote_snapshot

_EASTMONEY_INTRADAY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


class EastmoneyIntradayQuoteSnapshotSource:
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
            response = client.get(
                _EASTMONEY_INTRADAY_KLINE_URL,
                params={
                    "secid": secid,
                    "fields1": "f1,f2,f3,f4,f5,f6,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    "klt": "1",
                    "fqt": "1",
                    "lmt": "2",
                    "beg": "0",
                    "end": "20500101",
                },
            )
            response.raise_for_status()
            payload = response.json()

        rows = _extract_kline_rows(payload)
        if not rows:
            return _fallback_to_quote_snapshot(payload)

        latest = _parse_intraday_kline(rows[-1])
        previous_close = _extract_previous_close(payload)
        change_amount = latest.last_price - previous_close
        if previous_close == 0:
            raise ValueError("Eastmoney intraday quote payload has zero previous close")
        change_percent = (change_amount / previous_close) * Decimal("100")

        return RawQuoteSnapshot(
            last_price=latest.last_price,
            change_amount=change_amount.quantize(Decimal("0.0001")),
            change_percent=change_percent.quantize(Decimal("0.0001")),
            snapshot_time=latest.snapshot_time,
        )


class _IntradayKline:
    def __init__(self, *, snapshot_time: datetime, last_price: Decimal):
        self.snapshot_time = snapshot_time
        self.last_price = last_price



def _extract_kline_rows(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return []

    data = payload.get("data")
    if not isinstance(data, dict):
        return []

    rows = data.get("klines")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, str) and row.strip()]



def _extract_previous_close(payload: object) -> Decimal:
    if not isinstance(payload, dict):
        raise ValueError("Eastmoney intraday quote payload is invalid")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Eastmoney intraday quote payload missing data")

    value = data.get("prePrice") or data.get("preKPrice")
    if not isinstance(value, (int, float, str)):
        raise ValueError("Eastmoney intraday quote payload missing previous close")
    return Decimal(str(value))



def _fallback_to_quote_snapshot(payload: object) -> RawQuoteSnapshot:
    # Only accept a complete quote; prePrice is a previous close, not a live price.
    return _parse_quote_snapshot(payload)



def _parse_intraday_kline(row: str) -> _IntradayKline:
    parts = [part.strip() for part in row.split(",")]
    if len(parts) < 3:
        raise ValueError("Eastmoney intraday quote row is incomplete")

    snapshot_time = datetime.strptime(parts[0], "%Y-%m-%d %H:%M").replace(
        tzinfo=ZoneInfo("Asia/Shanghai")
    ).astimezone(UTC)
    last_price = Decimal(parts[2])
    return _IntradayKline(snapshot_time=snapshot_time, last_price=last_price)



def _secid(market: str, code: str) -> str:
    market_map = {"SZ": "0", "SH": "1"}
    market_prefix = market_map.get(market)
    if market_prefix is None:
        raise ValueError(f"unsupported market: {market}")
    if not code:
        raise ValueError("stock code is required")
    return f"{market_prefix}.{code}"
