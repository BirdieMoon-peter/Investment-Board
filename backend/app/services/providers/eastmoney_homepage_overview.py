from datetime import datetime, timezone
from decimal import Decimal

import httpx

from app.services.homepage_overview import HomepageMacroItem, MarketIndexSnapshot
from app.services.providers.http_client import build_provider_client, retry_request
from app.services.providers.raw_types import RawMacroSnapshotItem, RawMarketIndexSnapshot

_INDEX_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
_MACRO_DATA_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

_INDEX_DEFINITIONS = (
    {"key": "shanghai_composite", "name": "上证指数", "market": "SH", "secid": "1.000001"},
    {"key": "shenzhen_component", "name": "深证成指", "market": "SZ", "secid": "0.399001"},
    {"key": "chinext", "name": "创业板指", "market": "SZ", "secid": "0.399006"},
    {"key": "csi_300", "name": "沪深300", "market": "SH", "secid": "1.000300"},
)

_MACRO_DEFINITIONS = (
    {
        "key": "cpi",
        "title": "CPI",
        "category": "inflation",
        "importance": "high",
        "report_name": "RPT_ECONOMY_CPI",
    },
    {
        "key": "ppi",
        "title": "PPI",
        "category": "inflation",
        "importance": "medium",
        "report_name": "RPT_ECONOMY_PPI",
    },
    {
        "key": "manufacturing_pmi",
        "title": "制造业PMI",
        "category": "activity",
        "importance": "high",
        "report_name": "RPT_ECONOMY_PMI",
    },
    {
        "key": "m2",
        "title": "M2",
        "category": "liquidity",
        "importance": "medium",
        "report_name": "RPT_ECONOMY_CURRENCY_SUPPLY",
    },
)


class EastmoneyMarketIndexSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self) -> list[MarketIndexSnapshot]:
        with build_provider_client(transport=self._transport) as client:
            results = [
                _to_market_index_snapshot(_fetch_index_snapshot(client, definition))
                for definition in _INDEX_DEFINITIONS
            ]
        return results


class EastmoneyMacroSnapshotSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self) -> list[HomepageMacroItem]:
        with build_provider_client(transport=self._transport) as client:
            items = [
                _to_homepage_macro_item(_fetch_macro_snapshot(client, definition))
                for definition in _MACRO_DEFINITIONS
            ]
        return items


def _fetch_index_snapshot(client: httpx.Client, definition: dict[str, str]) -> RawMarketIndexSnapshot:
    response = retry_request(
        client,
        "GET",
        _INDEX_QUOTE_URL,
        params={"secid": definition["secid"], "fields": "f43,f169,f170,f124,f58"},
    )
    payload = response.json()
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"index payload missing data for {definition['key']}")

    snapshot_time_raw = data.get("f124")
    snapshot_time = (
        datetime.fromtimestamp(int(snapshot_time_raw), tz=timezone.utc)
        if isinstance(snapshot_time_raw, (int, float, str)) and str(snapshot_time_raw) != "0"
        else None
    )

    return RawMarketIndexSnapshot(
        key=definition["key"],
        name=str(data.get("f58") or definition["name"]),
        market=definition["market"],
        last_value=_scaled_decimal(data.get("f43")),
        change_amount=_scaled_decimal(data.get("f169")),
        change_percent=_scaled_decimal(data.get("f170")),
        snapshot_time=snapshot_time,
    )


def _fetch_macro_snapshot(client: httpx.Client, definition: dict[str, str]) -> RawMacroSnapshotItem:
    response = client.get(
        _MACRO_DATA_URL,
        params={
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": "1",
            "pageNumber": "1",
            "reportName": definition["report_name"],
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
        },
        headers={"Referer": "https://data.eastmoney.com/center/macro.html"},
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"macro payload missing result for {definition['key']}")
    data = result.get("data")
    if not isinstance(data, list) or len(data) == 0 or not isinstance(data[0], dict):
        raise ValueError(f"macro payload missing data rows for {definition['key']}")

    row = data[0]
    report_date = row.get("REPORT_DATE")
    published_at = (
        datetime.fromisoformat(str(report_date).replace(" ", "T")).replace(tzinfo=timezone.utc)
        if report_date
        else None
    )

    value, unit, change_text, summary = _parse_macro_row(definition["key"], row)
    return RawMacroSnapshotItem(
        key=definition["key"],
        title=definition["title"],
        category=definition["category"],
        value=value,
        unit=unit,
        change_text=change_text,
        published_at=published_at,
        importance=definition["importance"],
        summary=summary,
    )


def _parse_macro_row(key: str, row: dict[str, object]) -> tuple[str | None, str | None, str | None, str | None]:
    time_label = str(row.get("TIME")) if row.get("TIME") else None
    if key == "cpi":
        same = row.get("NATIONAL_SAME")
        sequential = row.get("NATIONAL_SEQUENTIAL")
        return _stringify(same), "%", _percent_text("环比", sequential), time_label
    if key == "ppi":
        same = row.get("BASE_SAME")
        accumulate = row.get("BASE_ACCUMULATE")
        return _stringify(same), "%", _percent_text("累计", accumulate), time_label
    if key == "manufacturing_pmi":
        current = row.get("MAKE_INDEX")
        change = row.get("MAKE_SAME")
        return _stringify(current), None, _percent_text("较上月", change), time_label
    if key == "m2":
        current = row.get("CURRENCY_SAME")
        sequential = row.get("CURRENCY_SEQUENTIAL")
        return _stringify(current), "%", _percent_text("环比", sequential), time_label
    return None, None, None, time_label


def _percent_text(label: str, value: object) -> str | None:
    text = _stringify(value)
    if text is None:
        return None
    return f"{label}{text}%"


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _scaled_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, (int, float, str)):
        raise ValueError("index field is not numeric")
    return Decimal(str(value)) / Decimal("100")


def _to_market_index_snapshot(raw: RawMarketIndexSnapshot) -> MarketIndexSnapshot:
    return MarketIndexSnapshot(
        key=raw.key,
        name=raw.name,
        market=raw.market,
        last_value=raw.last_value,
        change_amount=raw.change_amount,
        change_percent=raw.change_percent,
        snapshot_time=raw.snapshot_time,
    )


def _to_homepage_macro_item(raw: RawMacroSnapshotItem) -> HomepageMacroItem:
    return HomepageMacroItem(
        key=raw.key,
        title=raw.title,
        category=raw.category,
        value=raw.value,
        unit=raw.unit,
        change_text=raw.change_text,
        published_at=raw.published_at,
        importance=raw.importance,
        summary=raw.summary,
    )
