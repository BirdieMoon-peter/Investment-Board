from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawAnnouncement

_SINA_BASE_URL = "https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllBulletin/stockid/{stock_code}.phtml"
_SINA_ORIGIN = "https://vip.stock.finance.sina.com.cn"
_SOURCE_NAME = "Sina"


class SinaAnnouncementSource:
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
            _SINA_BASE_URL.format(stock_code=stock_code),
            params={"market": market},
        )
        response.raise_for_status()

        parser = _SinaAnnouncementHTMLParser()
        parser.feed(response.text)
        rows = parser.rows
        if not rows:
            raise ValueError("Sina announcement markup missing div.datelist ul li rows")

        items: list[RawAnnouncement] = []
        for row in rows:
            if not row.title:
                raise ValueError("Sina announcement row missing link")
            if not row.date_text:
                raise ValueError("Sina announcement row missing date")

            published_at = _parse_published_at(row.date_text)
            if since is not None and published_at < since:
                continue

            items.append(
                RawAnnouncement(
                    title=row.title,
                    published_at=published_at,
                    source=_SOURCE_NAME,
                    url=urljoin(_SINA_ORIGIN, row.href) if row.href else None,
                )
            )

        return items


class _AnnouncementRow:
    def __init__(self):
        self.href: str | None = None
        self.title = ""
        self.date_text = ""


class _SinaAnnouncementHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[_AnnouncementRow] = []
        self._div_depth = 0
        self._in_datelist_div = False
        self._in_li = False
        self._in_anchor = False
        self._in_date_span = False
        self._current_row: _AnnouncementRow | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attr_map = dict(attrs)
        class_names = set((attr_map.get("class") or "").split())

        if tag == "div":
            if self._in_datelist_div:
                self._div_depth += 1
            elif "datelist" in class_names:
                self._in_datelist_div = True
                self._div_depth = 1
            return

        if not self._in_datelist_div:
            return

        if tag == "li":
            self._in_li = True
            self._current_row = _AnnouncementRow()
            return

        if not self._in_li or self._current_row is None:
            return

        if tag == "a":
            self._in_anchor = True
            self._current_row.href = attr_map.get("href")
        elif tag == "span" and "date" in class_names:
            self._in_date_span = True

    def handle_endtag(self, tag: str):
        if tag == "div" and self._in_datelist_div:
            self._div_depth -= 1
            if self._div_depth == 0:
                self._in_datelist_div = False
            return

        if not self._in_datelist_div:
            return

        if tag == "a":
            self._in_anchor = False
        elif tag == "span":
            self._in_date_span = False
        elif tag == "li" and self._current_row is not None:
            self.rows.append(self._current_row)
            self._current_row = None
            self._in_li = False

    def handle_data(self, data: str):
        if self._current_row is None:
            return

        stripped = data.strip()
        if not stripped:
            return

        if self._in_anchor:
            self._current_row.title = f"{self._current_row.title} {stripped}".strip()
        elif self._in_date_span:
            self._current_row.date_text = f"{self._current_row.date_text} {stripped}".strip()


def _parse_published_at(raw_value: str) -> datetime:
    if not raw_value:
        raise ValueError("Sina announcement row missing date")

    parsed = datetime.fromisoformat(raw_value.replace("/", "-"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
