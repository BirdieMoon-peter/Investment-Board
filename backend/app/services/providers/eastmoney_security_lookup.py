import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawSecurityLookup


class EastmoneySecurityLookupSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self, market: str, code: str) -> RawSecurityLookup:
        normalized_market = market.strip().upper()
        normalized_code = code.strip()
        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                "https://searchapi.eastmoney.com/api/suggest/get",
                params={"input": normalized_code, "type": "14"},
            )
            response.raise_for_status()
            payload = response.json()

        rows = payload.get("QuotationCodeTable", {}).get("Data")
        if not isinstance(rows, list) or not rows:
            raise ValueError("security lookup returned no matches")

        row = next(
            (
                item
                for item in rows
                if isinstance(item, dict)
                and _optional_text(item.get("Code")) == normalized_code
                and _normalize_market(item.get("MktNum")) == normalized_market
            ),
            None,
        )
        if row is None:
            raise ValueError(
                f"security lookup did not match {normalized_market}:{normalized_code}"
            )

        return RawSecurityLookup(
            market=normalized_market,
            code=normalized_code,
            name=_require_text(row, "Name"),
            industry=_optional_text(row.get("SecurityTypeName")),
        )


def _normalize_market(value: object) -> str | None:
    market_map = {
        "1": "SH",
        "0": "SZ",
        "2": "SZ",
        "SH": "SH",
        "SZ": "SZ",
    }
    if value is None:
        return None
    return market_map.get(str(value).strip().upper())



def _require_text(row: dict[str, object], key: str) -> str:
    value = _optional_text(row.get(key))
    if value is None:
        raise ValueError(f"security lookup row missing {key}")
    return value



def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
