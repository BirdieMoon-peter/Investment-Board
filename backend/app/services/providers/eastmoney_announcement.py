from datetime import UTC, datetime
import logging
import time

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawAnnouncement

_EASTMONEY_BASE_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
_SOURCE_NAME = "Eastmoney"

logger = logging.getLogger(__name__)


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
        max_pages: int = 3,
    ) -> list[RawAnnouncement]:
        start_time = time.time()

        try:
            all_items: list[RawAnnouncement] = []
            raw_count = 0

            for page in range(1, max_pages + 1):
                for attempt in range(2):
                    try:
                        response = self._client.get(
                            _EASTMONEY_BASE_URL,
                            params={
                                "page_size": "50",
                                "page_index": str(page),
                                "stock_list": f"{market}{stock_code}",
                            },
                        )
                        response.raise_for_status()
                        payload = response.json()

                        rows = payload.get("data", {}).get("list") if isinstance(payload, dict) else None
                        if not isinstance(rows, list):
                            raise ValueError("Eastmoney announcement payload missing data.list")

                        if not rows:
                            break

                        raw_count += len(rows)

                        for row_index, row in enumerate(rows):
                            if not isinstance(row, dict):
                                raise ValueError(f"Eastmoney announcement row {row_index} is not a valid dict")

                            codes = row.get("codes")
                            if isinstance(codes, list) and len(codes) == 0:
                                continue

                            published_at = _parse_published_at(row, row_index=row_index)
                            if since is not None and published_at < since:
                                continue

                            all_items.append(
                                RawAnnouncement(
                                    title=_require_str(row, "title", row_index=row_index),
                                    published_at=published_at,
                                    source=_SOURCE_NAME,
                                    url=_build_announcement_url(row),
                                    summary=_optional_str(row, "summary"),
                                )
                            )

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


def _parse_published_at(row: dict[str, object], *, row_index: int = 0) -> datetime:
    raw_value = row.get("notice_date") or row.get("display_time")
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"Eastmoney announcement row {row_index} missing notice_date")

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


def _require_str(row: dict[str, object], key: str, *, row_index: int = 0) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Eastmoney announcement row {row_index} missing {key}")
    return value.strip()


def _optional_str(row: dict[str, object], key: str) -> str | None:
    value = row.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
