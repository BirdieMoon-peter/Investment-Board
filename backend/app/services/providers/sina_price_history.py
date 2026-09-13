"""Sina Finance daily kline price history data source."""

from datetime import date
from decimal import Decimal

import httpx

from app.services.providers.http_client import retry_request
from app.services.providers.raw_types import RawPriceBar

_SINA_KLINE_URL = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php"
    "/CN_MarketData.getKLineData"
)

# Sina uses lowercase market prefix: sz000617, sh515980
_MARKET_MAP = {"SZ": "sz", "SH": "sh"}


class SinaPriceHistorySource:
    """Daily kline source using Sina Finance API.

    Supports up to ~5000 bars (full history for most A-shares, ETFs, LOFs).
    """

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
        prefix = _MARKET_MAP.get(market.strip().upper(), "sh")
        symbol = f"{prefix}{normalized_code}"

        # Sina caps at ~5000 bars per request
        effective_limit = min(limit, 5000)

        with httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn/",
                "Accept": "*/*",
            },
            timeout=httpx.Timeout(30.0),
            transport=self._transport,
        ) as client:
            response = retry_request(
                client,
                "GET",
                _SINA_KLINE_URL,
                params={
                    "symbol": symbol,
                    "scale": "240",  # daily bars
                    "ma": "no",
                    "datalen": str(effective_limit),
                },
            )
            response.raise_for_status()

        text = response.text.strip()
        if not text:
            return []

        import json

        try:
            rows = json.loads(text)
        except json.JSONDecodeError:
            return []

        if not isinstance(rows, list):
            return []

        results: list[RawPriceBar] = []
        for row in rows:
            bar = _parse_row(row)
            if bar is not None:
                results.append(bar)

        return results[:limit]


def _parse_row(row: dict) -> RawPriceBar | None:
    """Parse Sina kline JSON row.

    Format: {"day":"2024-02-28","open":"5.950","high":"6.370","low":"5.940",
             "close":"6.080","volume":"276349299"}
    """
    try:
        if not isinstance(row, dict):
            return None

        day_str = row.get("day")
        if not day_str:
            return None

        trade_date = date.fromisoformat(str(day_str).strip())
        open_price = Decimal(str(row["open"])) if row.get("open") else Decimal("0")
        high_price = Decimal(str(row["high"])) if row.get("high") else Decimal("0")
        low_price = Decimal(str(row["low"])) if row.get("low") else Decimal("0")
        close_price = Decimal(str(row["close"])) if row.get("close") else Decimal("0")

        # Sina volume is in shares (not lots)
        volume_raw = row.get("volume", "0")
        volume = Decimal(str(volume_raw)) if volume_raw else Decimal("0")

        return RawPriceBar(
            trade_date=trade_date,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            amount=Decimal("0"),  # Sina doesn't provide amount in this API
        )
    except Exception:
        return None
