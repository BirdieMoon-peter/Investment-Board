from datetime import datetime, timezone

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawNewsItem

EASTMONEY_NEWS_ENDPOINT = "https://search-api-web.eastmoney.com/search/jsonp"
EASTMONEY_NEWS_SOURCE = "Eastmoney"


class EastmoneyNewsSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> list[RawNewsItem]:
        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                EASTMONEY_NEWS_ENDPOINT,
                params={
                    "keyword": stock_code,
                    "market": market,
                    "pageIndex": 1,
                    "pageSize": 20,
                },
            )
            response.raise_for_status()
            payload = response.json()

        rows = payload.get("data", {}).get("list")
        if not rows:
            raise ValueError("Eastmoney news payload is empty")

        items: list[RawNewsItem] = []
        for row in rows:
            item = RawNewsItem(
                title=_require_text(row, "title"),
                published_at=_parse_published_at(_require_text(row, "publish_time")),
                source=EASTMONEY_NEWS_SOURCE,
                url=_build_news_url(row.get("info_code")),
                summary=_optional_text(row.get("content")),
            )
            if since is None or item.published_at >= since:
                items.append(item)

        return items


def _require_text(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Eastmoney news row missing {key}")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _parse_published_at(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _build_news_url(info_code: object) -> str | None:
    if not isinstance(info_code, str) or not info_code.strip():
        return None
    return f"https://finance.eastmoney.com/a/{info_code.strip()}.html"
