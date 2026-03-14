from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.ifeng_news import IfengNewsSource
from app.services.providers.raw_types import RawNewsItem


HTML_PAGE = """
<html>
  <body>
    <div class="news-stream">
      <article class="news-item">
        <a href="/c/20260311/01">Ifeng market recap</a>
        <time datetime="2026-03-11 10:15">2026-03-11 10:15</time>
        <p>Margin financing stayed resilient.</p>
      </article>
    </div>
  </body>
</html>
"""


MULTI_ROW_HTML_PAGE = """
<html>
  <body>
    <div class="news-stream">
      <article class="news-item">
        <a href="/c/20260311/early">Early note</a>
        <time datetime="2026-03-11 09:00">2026-03-11 09:00</time>
        <p>Older row.</p>
      </article>
      <article class="news-item">
        <a href="/c/20260311/midday">Midday note</a>
        <time datetime="2026-03-11 12:30">2026-03-11 12:30</time>
        <p>Newer row.</p>
      </article>
    </div>
  </body>
</html>
"""


MISSING_TIME_HTML_PAGE = """
<html>
  <body>
    <div class="news-stream">
      <article class="news-item">
        <a href="/c/20260311/01">Missing time item</a>
      </article>
    </div>
  </body>
</html>
"""


def test_ifeng_news_source_maps_html_rows_to_raw_news_items():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=HTML_PAGE))

    source = IfengNewsSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert result == [
        RawNewsItem(
            title="Ifeng market recap",
            published_at=datetime(2026, 3, 11, 10, 15, tzinfo=timezone.utc),
            source="Ifeng",
            url="https://finance.ifeng.com/c/20260311/01",
            summary="Margin financing stayed resilient.",
        )
    ]


def test_ifeng_news_source_requests_market_specific_path():
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, text=HTML_PAGE)

    transport = httpx.MockTransport(handler)
    source = IfengNewsSource(transport=transport)

    source.fetch("600519", "sh")
    source.fetch("000001", "sz")

    assert requested_urls == [
        "https://finance.ifeng.com/app/hq/stock/sh600519/news?market=sh",
        "https://finance.ifeng.com/app/hq/stock/sz000001/news?market=sz",
    ]



def test_ifeng_news_source_filters_rows_older_than_since():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=MULTI_ROW_HTML_PAGE)
    )

    source = IfengNewsSource(transport=transport)

    result = source.fetch(
        "600519",
        "sh",
        since=datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc),
    )

    assert [item.title for item in result] == ["Midday note"]


def test_ifeng_news_source_raises_clear_error_for_missing_rows():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="<html><body><div>No news rows</div></body></html>")
    )

    source = IfengNewsSource(transport=transport)

    with pytest.raises(ValueError, match="Ifeng news markup missing article rows"):
        source.fetch("600519", "sh")


def test_ifeng_news_source_raises_clear_error_for_missing_time():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=MISSING_TIME_HTML_PAGE)
    )

    source = IfengNewsSource(transport=transport)

    with pytest.raises(ValueError, match="Ifeng news row 0 missing published time"):
        source.fetch("600519", "sh")


def test_ifeng_news_source_retries_on_timeout():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, text=HTML_PAGE)

    transport = httpx.MockTransport(mock_handler)
    source = IfengNewsSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].title == "Ifeng market recap"
    assert attempt_count == 2


def test_ifeng_news_source_logs_successful_fetch(caplog):
    import logging

    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=HTML_PAGE))
    source = IfengNewsSource(transport=transport)

    with caplog.at_level(logging.INFO):
        result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert any("Provider fetch completed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)
