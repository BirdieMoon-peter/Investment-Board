from datetime import date
from decimal import Decimal

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawPriceBar

_EASTMONEY_PRICE_HISTORY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


class EastmoneyPriceHistorySource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        limit: int = 60,
    ) -> list[RawPriceBar]:
        normalized_code = stock_code.strip()
        normalized_market = market.strip().upper()
        secid = _secid(normalized_market, normalized_code)

        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                _EASTMONEY_PRICE_HISTORY_URL,
                params={
                    "secid": secid,
                    "fields1": "f1,f2,f3,f4,f5,f6,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                    "klt": "101",
                    "fqt": "1",
                    "lmt": str(limit),
                    "beg": "0",
                    "end": "20500101",
                },
            )
            response.raise_for_status()
            payload = response.json()

        rows = _extract_kline_rows(payload)
        if not isinstance(rows, list):
            raise ValueError("Eastmoney price history payload missing data.klines")

        return [_parse_kline(row) for row in rows]



def _extract_kline_rows(payload: object) -> object:
    if not isinstance(payload, dict):
        return None

    data = payload.get("data")
    if not isinstance(data, dict):
        return None

    return data.get("klines")



def _secid(market: str, code: str) -> str:
    market_map = {"SZ": "0", "SH": "1"}
    market_prefix = market_map.get(market)
    if market_prefix is None:
        raise ValueError(f"unsupported market: {market}")
    if not code:
        raise ValueError("stock code is required")
    return f"{market_prefix}.{code}"



def _parse_kline(row: object) -> RawPriceBar:
    if not isinstance(row, str):
        raise ValueError("Eastmoney price history row is not a string")

    parts = [part.strip() for part in row.split(",")]
    if len(parts) < 7:
        raise ValueError("Eastmoney price history row is incomplete")

    # Format: date,open,close,high,low,volume,amount[,change_pct]
    # Note: API now returns 8 fields (added change_pct), but we only need first 7
    return RawPriceBar(
        trade_date=date.fromisoformat(parts[0]),
        open_price=Decimal(parts[1]),
        close_price=Decimal(parts[2]),
        high_price=Decimal(parts[3]),
        low_price=Decimal(parts[4]),
        volume=Decimal(parts[5]),
        amount=Decimal(parts[6]),
    )
