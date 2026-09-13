"""Tencent Finance market index and price history data source."""

from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING

import httpx

from app.services.providers.http_client import retry_request
from app.services.providers.raw_types import RawPriceBar

if TYPE_CHECKING:
    from app.services.homepage_overview import MarketIndexSnapshot

_QT_URL = "https://qt.gtimg.cn/q="

_INDEX_DEFINITIONS = {
    "shanghai_composite": {"name": "上证指数", "market": "SH", "symbol": "sh000001"},
    "shenzhen_component": {"name": "深证成指", "market": "SZ", "symbol": "sz399001"},
    "chinext": {"name": "创业板指", "market": "SZ", "symbol": "sz399006"},
    "csi_300": {"name": "沪深 300", "market": "SH", "symbol": "sh000300"},
}


class TencentMarketIndexSource:
    """Market index source using Tencent qt.gtimg.cn API (batch request)."""

    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self) -> list["MarketIndexSnapshot"]:
        from app.services.homepage_overview import MarketIndexSnapshot

        symbols = ",".join(d["symbol"] for d in _INDEX_DEFINITIONS.values())
        with httpx.Client(
            headers={
                "Referer": "https://stockapp.finance.qq.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=httpx.Timeout(25.0),
            transport=self._transport,
        ) as client:
            response = retry_request(client, "GET", f"{_QT_URL}{symbols}")
            response.raise_for_status()

        results: list[MarketIndexSnapshot] = []
        symbol_to_key = {d["symbol"]: k for k, d in _INDEX_DEFINITIONS.items()}

        for line in response.text.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue

            var_name, _, raw_value = line.partition("=")
            # var_name like v_sh000001
            symbol = var_name.strip().replace("v_", "")
            key = symbol_to_key.get(symbol)
            if key is None:
                continue

            definition = _INDEX_DEFINITIONS[key]
            parts = raw_value.strip('"').split("~")
            if len(parts) < 33:
                continue

            try:
                last_value = Decimal(parts[3]) if parts[3] else None
                change_amount = Decimal(parts[31]) if parts[31] else None
                change_percent = Decimal(parts[32]) if parts[32] else None

                if last_value is None or last_value <= 0:
                    continue

                results.append(
                    MarketIndexSnapshot(
                        key=key,
                        name=parts[1] or definition["name"],
                        market=definition["market"],
                        last_value=last_value,
                        change_amount=change_amount,
                        change_percent=change_percent,
                        snapshot_time=_parse_source_time(parts[30]),
                    )
                )
            except (ValueError, IndexError, ArithmeticError):
                continue

        return results


def _parse_kline_row(symbol: str, row: str) -> RawPriceBar | None:
    """Parse Tencent kline row.

    Format: 20260323,10.50,10.80,10.40,10.70,1000000,10700000
    date,open,high,low,close,volume,amount
    """
    parts = row.split(",")
    if len(parts) < 7:
        return None

    try:
        return RawPriceBar(
            trade_date=date(int(parts[0][:4]), int(parts[0][4:6]), int(parts[0][6:8])),
            open_price=Decimal(parts[1]),
            high_price=Decimal(parts[2]),
            low_price=Decimal(parts[3]),
            close_price=Decimal(parts[4]),
            volume=Decimal(parts[5]),
            amount=Decimal(parts[6]),
        )
    except Exception:
        return None


def _parse_source_time(value: str) -> datetime | None:
    if len(value) != 14 or not value.isdigit():
        return None
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(
            tzinfo=ZoneInfo("Asia/Shanghai")
        ).astimezone(UTC)
    except ValueError:
        return None
