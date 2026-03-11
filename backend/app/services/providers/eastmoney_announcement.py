from datetime import UTC, datetime

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawAnnouncement

_EASTMONEY_BASE_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
_SOURCE_NAME = "Eastmoney"


class EastmoneyAnnouncementSource:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self._client = client or build_provider_client(transport=transport)

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> list[RawAnnouncement]:
        response = self._client.get(
            _EASTMONEY_BASE_URL,
            params={
                "page_size": "100",
                "page_index": "1",
                "stock_list": f"{market}{stock_code}",
            },
        )
        response.raise_for_status()
        payload = response.json()

        rows = payload.get("data", {}).get("list") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("Eastmoney announcement payload missing data.list")

        items: list[RawAnnouncement] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Eastmoney announcement payload contains an invalid row")

            published_at = _parse_published_at(row)
            if since is not None and published_at < since:
                continue

            items.append(
                RawAnnouncement(
                    title=_require_str(row, "title"),
                    published_at=published_at,
                    source=_SOURCE_NAME,
                    url=_build_announcement_url(row),
                    summary=_optional_str(row, "summary"),
                )
            )

        return items


def _parse_published_at(row: dict[str, object]) -> datetime:
    raw_value = row.get("notice_date") or row.get("display_time")
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError("Eastmoney announcement row missing notice_date")

    normalized = raw_value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _build_announcement_url(row: dict[str, object]) -> str | None:
    art_code = row.get("art_code")
    if not isinstance(art_code, str) or not art_code.strip():
        return None
    return f"https://data.eastmoney.com/notices/detail/{art_code}.html"


def _require_str(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Eastmoney announcement row missing {key}")
    return value.strip()


def _optional_str(row: dict[str, object], key: str) -> str | None:
    value = row.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
