"""NetEase Finance market index data source."""

from decimal import Decimal

import httpx

from app.services.homepage_overview import MarketIndexSnapshot
from app.services.providers.http_client import retry_request

_NETEASE_INDEX_URL = "https://api.money.126.net/data/feed/"

_INDEX_DEFINITIONS = {
    "shanghai_composite": {"name": "上证指数", "market": "SH", "symbol": "0000001"},
    "shenzhen_component": {"name": "深证成指", "market": "SZ", "symbol": "1399001"},
    "chinext": {"name": "创业板指", "market": "SZ", "symbol": "1399006"},
    "csi_300": {"name": "沪深 300", "market": "SH", "symbol": "0930300"},
}


class NetEaseMarketIndexSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self) -> list[MarketIndexSnapshot]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://money.163.com/",
            "Accept": "*/*",
        }
        with httpx.Client(
            headers=headers,
            timeout=httpx.Timeout(25.0),
            transport=self._transport,
        ) as client:
            results = []
            for key, definition in _INDEX_DEFINITIONS.items():
                try:
                    snapshot = _fetch_index_snapshot(client, key, definition, headers)
                    if snapshot is not None:
                        results.append(snapshot)
                except Exception:
                    pass
            return results


def _fetch_index_snapshot(
    client: httpx.Client, key: str, definition: dict[str, str], headers: dict
) -> MarketIndexSnapshot | None:
    """Fetch index data from NetEase Finance API.

    Response format: _ntes_quote_callback({"0000001": {"name":"上证指数","price":"3813.28",...}})
    """
    symbol = definition["symbol"]
    response = retry_request(
        client,
        "GET",
        _NETEASE_INDEX_URL + symbol,
        headers=headers,
    )
    response.raise_for_status()

    # Parse response: _ntes_quote_callback({...})
    text = response.text.strip()
    if not text or "(" not in text:
        return None

    # Extract JSON from callback
    start = text.find("(") + 1
    end = text.rfind(")")
    if start <= 0 or end <= start:
        return None

    json_str = text[start:end]

    try:
        import json
        data = json.loads(json_str)
        quote = data.get(symbol, {})

        current = quote.get("price")
        change = quote.get("updown")
        change_pct = quote.get("percent")
        yesterday = quote.get("yestclose")

        current_dec = Decimal(current) if current else None
        change_amount_dec = Decimal(change) if change else None
        change_pct_dec = Decimal(change_pct) if change_pct else None

        return MarketIndexSnapshot(
            key=key,
            name=quote.get("name") or definition["name"],
            market=definition["market"],
            last_value=current_dec,
            change_amount=change_amount_dec,
            change_percent=change_pct_dec,
            snapshot_time=None,
        )
    except Exception:
        return None
