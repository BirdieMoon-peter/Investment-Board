"""NetEase Finance price history data source."""

from datetime import date
from decimal import Decimal

import httpx

from app.services.providers.http_client import retry_request
from app.services.providers.raw_types import RawPriceBar

_NETEASE_HISTORY_URL = "https://api.money.126.net/data/history/"

# 00=SZ, 01=SH
_MARKET_MAP = {"SZ": "0", "SH": "01"}


class NetEasePriceHistorySource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        limit: int = 10000,
    ) -> list[RawPriceBar]:
        normalized_code = stock_code.strip()
        normalized_market = _MARKET_MAP.get(market.strip().upper(), "01")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://money.163.com/",
            "Accept": "*/*",
        }

        with httpx.Client(
            headers=headers,
            timeout=httpx.Timeout(30.0),
            transport=self._transport,
        ) as client:
            symbol = normalized_market + normalized_code
            results: list[RawPriceBar] = []
            offset = 0
            page_size = 500

            while offset < limit:
                response = retry_request(
                    client,
                    "GET",
                    f"{_NETEASE_HISTORY_URL}{symbol}/day.json",
                    params={"size": page_size, "offset": offset},
                    headers=headers,
                )
                response.raise_for_status()

                payload = response.json()
                if not isinstance(payload, dict) or "data" not in payload:
                    break

                data = payload["data"]
                if not isinstance(data, list) or not data:
                    break

                page_items = []
                for row in data:
                    bar = _parse_row(symbol, row)
                    if bar is not None:
                        page_items.append(bar)

                if not page_items:
                    break

                results.extend(page_items)

                if len(data) < page_size:
                    break
                offset += page_size

            return results[:limit]


def _parse_row(symbol: str, row: list) -> RawPriceBar | None:
    """Parse NetEase history row.

    Format: ["2026-03-23", "10.50", "10.80", "10.40", "10.70", "1000000", "10700000", "5.15"]
    [date, open, high, low, close, volume, amount, change_pct]
    """
    try:
        if not isinstance(row, list) or len(row) < 5:
            return None

        trade_date = date.fromisoformat(str(row[0]).replace("/", "-"))
        open_price = Decimal(str(row[1])) if row[1] else Decimal("0")
        high_price = Decimal(str(row[2])) if row[2] else Decimal("0")
        low_price = Decimal(str(row[3])) if row[3] else Decimal("0")
        close_price = Decimal(str(row[4])) if row[4] else Decimal("0")
        volume = Decimal(str(row[5])) if len(row) > 5 and row[5] else Decimal("0")
        amount = Decimal(str(row[6])) if len(row) > 6 and row[6] else Decimal("0")

        return RawPriceBar(
            trade_date=trade_date,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            amount=amount,
        )
    except Exception:
        return None
