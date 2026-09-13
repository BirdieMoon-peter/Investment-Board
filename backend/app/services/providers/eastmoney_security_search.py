import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawSecurityLookup
from app.services.providers.eastmoney_security_lookup import _normalize_market, _optional_text, _require_text


class EastmoneySecuritySearchSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def search(self, query: str, limit: int = 20) -> list[RawSecurityLookup]:
        normalized_query = query.strip()
        if not normalized_query or limit <= 0:
            return []

        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                "https://searchapi.eastmoney.com/api/suggest/get",
                params={"input": normalized_query, "type": "14"},
            )
            response.raise_for_status()
            payload = response.json()

        rows = payload.get("QuotationCodeTable", {}).get("Data")
        if not isinstance(rows, list) or not rows:
            return []

        results: list[RawSecurityLookup] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue

            market = _normalize_market(row.get("MktNum"))
            code = _optional_text(row.get("Code"))
            if market not in {"SH", "SZ"} or code is None:
                continue

            key = (market, code)
            if key in seen:
                continue
            seen.add(key)

            results.append(
                RawSecurityLookup(
                    market=market,
                    code=code,
                    name=_require_text(row, "Name"),
                    industry=_optional_text(row.get("SecurityTypeName")),
                )
            )
            if len(results) >= limit:
                break

        return results
