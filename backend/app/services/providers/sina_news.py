from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawNewsItem

SINA_NEWS_ENDPOINT = "https://finance.sina.com.cn/stock/api/jsonp.php/var%20news=/StockNewsService.getNewsList"
SINA_NEWS_BASE_URL = "https://finance.sina.com.cn"
SINA_NEWS_SOURCE = "Sina"


class SinaNewsSource:
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
                SINA_NEWS_ENDPOINT,
                params={
                    "symbol": f"{market}{stock_code}",
                    "page": 1,
                    "num": 20,
                },
            )
            response.raise_for_status()
            payload = response.json()

        rows = _extract_rows(payload)
        items: list[RawNewsItem] = []
        for index, row in enumerate(rows):
            item = _parse_row(row, index=index)
            if since is None or item.published_at >= since:
                items.append(item)
        return items


def _extract_rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("result"), dict):
            data = payload["result"].get("data")
            if isinstance(data, list):
                return data
        data = payload.get("data")
        if isinstance(data, list):
            return data
    raise ValueError("Sina news payload missing data rows")


def _parse_row(row: object, *, index: int) -> RawNewsItem:
    if not isinstance(row, dict):
        raise ValueError(f"Sina news row {index} is invalid")

    title = _require_text(row, "title", index=index)
    published_at = _parse_published_at(_require_text(row, "ctime", index=index))
    url = urljoin(SINA_NEWS_BASE_URL, _require_text(row, "url", index=index))

    return RawNewsItem(
        title=title,
        published_at=published_at,
        source=SINA_NEWS_SOURCE,
        url=url,
        summary=_optional_text(row.get("intro")),
    )


def _require_text(row: dict[str, object], key: str, *, index: int) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Sina news row {index} missing {key}")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _parse_published_at(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
