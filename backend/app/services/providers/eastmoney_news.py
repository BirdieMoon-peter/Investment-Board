from datetime import datetime, timezone
import logging
import time

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawNewsItem

EASTMONEY_NEWS_ENDPOINT = "https://search-api-web.eastmoney.com/search/jsonp"
EASTMONEY_NEWS_SOURCE = "Eastmoney"

logger = logging.getLogger(__name__)


class EastmoneyNewsSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
        max_pages: int = 3,
    ) -> list[RawNewsItem]:
        start_time = time.time()

        try:
            all_items: list[RawNewsItem] = []
            raw_count = 0

            for page in range(1, max_pages + 1):
                for attempt in range(2):
                    try:
                        with build_provider_client(transport=self._transport) as client:
                            response = client.get(
                                EASTMONEY_NEWS_ENDPOINT,
                                params={
                                    "keyword": stock_code,
                                    "market": market,
                                    "pageIndex": page,
                                    "pageSize": 20,
                                },
                            )
                            response.raise_for_status()
                            payload = response.json()

                        rows = payload.get("data", {}).get("list")
                        if not rows:
                            if page == 1:
                                raise ValueError("Eastmoney news payload is empty")
                            break

                        raw_count += len(rows)

                        for row_index, row in enumerate(rows):
                            item = RawNewsItem(
                                title=_require_text(row, "title", row_index=row_index),
                                published_at=_parse_published_at(_require_text(row, "publish_time", row_index=row_index)),
                                source=EASTMONEY_NEWS_SOURCE,
                                url=_build_news_url(row.get("info_code")),
                                summary=_optional_text(row.get("content")),
                            )
                            if since is None or item.published_at >= since:
                                all_items.append(item)

                        break

                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        if attempt == 0:
                            time.sleep(1)
                            continue
                        raise

                if not rows:
                    break

            elapsed = time.time() - start_time
            logger.info(
                "Provider fetch completed: source=%s stock=%s:%s elapsed=%.2fs raw_count=%d filtered_count=%d",
                self.__class__.__name__,
                market,
                stock_code,
                elapsed,
                raw_count,
                len(all_items),
            )

            return all_items

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                elapsed = time.time() - start_time
                logger.warning(
                    "Provider fetch degraded to empty results: source=%s stock=%s:%s elapsed=%.2fs status=%d error=%s",
                    self.__class__.__name__,
                    market,
                    stock_code,
                    elapsed,
                    exc.response.status_code,
                    exc,
                )
                return []
            raise
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.warning(
                "Provider fetch failed: source=%s stock=%s:%s elapsed=%.2fs error=%s",
                self.__class__.__name__,
                market,
                stock_code,
                elapsed,
                exc,
            )
            raise


def _require_text(row: dict[str, object], key: str, *, row_index: int = 0) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Eastmoney news row {row_index} missing {key}")
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
