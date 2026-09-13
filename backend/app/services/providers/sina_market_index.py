"""Sina Finance market index data source using hq.sinajs.cn batch API."""

from decimal import Decimal

import httpx

from app.services.homepage_overview import MarketIndexSnapshot
from app.services.providers.http_client import retry_request

_SINA_HQ_URL = "https://hq.sinajs.cn/list="

# s_ prefix gives simplified format: name,price,change_amount,change_percent,volume,amount
_INDEX_DEFINITIONS = {
    "shanghai_composite": {"name": "上证指数", "market": "SH", "symbol": "s_sh000001"},
    "shenzhen_component": {"name": "深证成指", "market": "SZ", "symbol": "s_sz399001"},
    "chinext": {"name": "创业板指", "market": "SZ", "symbol": "s_sz399006"},
    "csi_300": {"name": "沪深 300", "market": "SH", "symbol": "s_sh000300"},
}


class SinaMarketIndexSource:
    """Market index source using Sina hq.sinajs.cn (single batch request)."""

    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self) -> list[MarketIndexSnapshot]:
        symbols = ",".join(d["symbol"] for d in _INDEX_DEFINITIONS.values())
        with httpx.Client(
            headers={
                "Referer": "https://finance.sina.com.cn/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=httpx.Timeout(25.0),
            transport=self._transport,
        ) as client:
            response = retry_request(client, "GET", f"{_SINA_HQ_URL}{symbols}")
            response.raise_for_status()

        symbol_to_key = {d["symbol"]: k for k, d in _INDEX_DEFINITIONS.items()}
        results: list[MarketIndexSnapshot] = []

        for line in response.text.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue

            # Format: var hq_str_s_sh000001="上证指数,3813.28,-143.77,-3.63,8047388,108624829"
            var_part, _, value_part = line.partition("=")
            var_name = var_part.replace("var ", "").replace("hq_str_", "").strip()
            key = symbol_to_key.get(var_name)
            if key is None:
                continue

            definition = _INDEX_DEFINITIONS[key]
            fields = value_part.strip('"').split(",")
            # fields: [name, price, change_amount, change_percent, volume, amount]
            if len(fields) < 4:
                continue

            try:
                last_value = Decimal(fields[1]) if fields[1] else None
                change_amount = Decimal(fields[2]) if fields[2] else None
                change_percent = Decimal(fields[3]) if fields[3] else None

                if last_value is None or last_value <= 0:
                    continue

                results.append(
                    MarketIndexSnapshot(
                        key=key,
                        name=fields[0] or definition["name"],
                        market=definition["market"],
                        last_value=last_value,
                        change_amount=change_amount,
                        change_percent=change_percent,
                        snapshot_time=None,
                    )
                )
            except (ValueError, IndexError, ArithmeticError):
                continue

        return results
