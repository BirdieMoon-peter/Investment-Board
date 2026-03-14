from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin
import logging
import time

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawNewsItem

_IFENG_NEWS_ENDPOINT = "https://finance.ifeng.com/app/hq/stock/{market}{stock_code}/news"
_IFENG_ORIGIN = "https://finance.ifeng.com"
_SOURCE_NAME = "Ifeng"

logger = logging.getLogger(__name__)


class IfengNewsSource:
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
    ) -> list[RawNewsItem]:
        start_time = time.time()
        normalized_market = market.strip().lower()

        try:
            for attempt in range(2):
                try:
                    response = self._client.get(
                        _IFENG_NEWS_ENDPOINT.format(
                            market=normalized_market,
                            stock_code=stock_code,
                        ),
                        params={"market": normalized_market},
                    )
                    response.raise_for_status()

                    parser = _IfengNewsHTMLParser()
                    parser.feed(response.text)
                    rows = parser.rows
                    if not rows:
                        raise ValueError("Ifeng news markup missing article rows")

                    raw_count = len(rows)
                    items: list[RawNewsItem] = []
                    for row_index, row in enumerate(rows):
                        if not row.title:
                            raise ValueError(f"Ifeng news row {row_index} missing title")
                        if not row.published_at_text:
                            raise ValueError(
                                f"Ifeng news row {row_index} missing published time"
                            )

                        published_at = _parse_published_at(row.published_at_text)
                        if since is not None and published_at < since:
                            continue

                        items.append(
                            RawNewsItem(
                                title=row.title,
                                published_at=published_at,
                                source=_SOURCE_NAME,
                                url=urljoin(_IFENG_ORIGIN, row.href) if row.href else None,
                                summary=row.summary or None,
                            )
                        )

                    elapsed = time.time() - start_time
                    logger.info(
                        "Provider fetch completed: source=%s stock=%s:%s elapsed=%.2fs raw_count=%d filtered_count=%d",
                        self.__class__.__name__,
                        normalized_market,
                        stock_code,
                        elapsed,
                        raw_count,
                        len(items),
                    )

                    return items

                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == 0:
                        time.sleep(1)
                        continue
                    raise

        except Exception as exc:
            elapsed = time.time() - start_time
            logger.warning(
                "Provider fetch failed: source=%s stock=%s:%s elapsed=%.2fs error=%s",
                self.__class__.__name__,
                normalized_market,
                stock_code,
                elapsed,
                exc,
            )
            raise


class _IfengNewsRow:
    def __init__(self):
        self.href: str | None = None
        self.title = ""
        self.published_at_text = ""
        self.summary = ""


class _IfengNewsHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[_IfengNewsRow] = []
        self._article_depth = 0
        self._current_row: _IfengNewsRow | None = None
        self._capture_title = False
        self._capture_time = False
        self._capture_summary = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attr_map = dict(attrs)
        class_names = set((attr_map.get("class") or "").split())

        if tag == "article" and "news-item" in class_names:
            self._article_depth = 1
            self._current_row = _IfengNewsRow()
            return

        if self._current_row is None:
            return

        if tag == "article":
            self._article_depth += 1
            return
        if tag == "a":
            self._capture_title = True
            self._current_row.href = attr_map.get("href")
            return
        if tag == "time":
            self._capture_time = True
            datetime_attr = attr_map.get("datetime")
            if isinstance(datetime_attr, str):
                self._current_row.published_at_text = datetime_attr.strip()
            return
        if tag == "p":
            self._capture_summary = True

    def handle_endtag(self, tag: str):
        if self._current_row is None:
            return

        if tag == "a":
            self._capture_title = False
            return
        if tag == "time":
            self._capture_time = False
            return
        if tag == "p":
            self._capture_summary = False
            return
        if tag == "article":
            self._article_depth -= 1
            if self._article_depth == 0:
                self.rows.append(self._current_row)
                self._current_row = None

    def handle_data(self, data: str):
        if self._current_row is None:
            return

        stripped = data.strip()
        if not stripped:
            return

        if self._capture_title:
            self._current_row.title = f"{self._current_row.title} {stripped}".strip()
        elif self._capture_time and not self._current_row.published_at_text:
            self._current_row.published_at_text = stripped
        elif self._capture_summary:
            self._current_row.summary = f"{self._current_row.summary} {stripped}".strip()


def _parse_published_at(raw_value: str) -> datetime:
    parsed = datetime.fromisoformat(raw_value.replace("/", "-").strip())
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
