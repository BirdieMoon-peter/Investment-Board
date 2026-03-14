from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.raw_types import RawAnnouncement
from app.services.providers.sina_announcement import SinaAnnouncementSource



def test_sina_announcement_source_maps_flattened_datelist_markup_to_raw_announcements():
    html = """
    <html>
      <body>
        <div class="datelist">
          <ul>
            2026-03-11 09:45:00
            <a href="/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1">Dividend plan</a><br />
            2026-03-10 08:30:00
            <a href="https://vip.stock.finance.sina.com.cn/corp/view/vCB_BulletinDetail.php?stockid=600519&id=2">Annual report</a><br />
          </ul>
        </div>
      </body>
    </html>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))

    source = SinaAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert result == [
        RawAnnouncement(
            title="Dividend plan",
            published_at=datetime(2026, 3, 11, 9, 45, tzinfo=timezone.utc),
            source="Sina",
            url="https://vip.stock.finance.sina.com.cn/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1",
            summary=None,
        ),
        RawAnnouncement(
            title="Annual report",
            published_at=datetime(2026, 3, 10, 8, 30, tzinfo=timezone.utc),
            source="Sina",
            url="https://vip.stock.finance.sina.com.cn/corp/view/vCB_BulletinDetail.php?stockid=600519&id=2",
            summary=None,
        ),
    ]



def test_sina_announcement_source_filters_flattened_datelist_rows_by_since():
    html = """
    <div class="datelist">
      <ul>
        2026-03-11 09:45:00
        <a href="/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1">Dividend plan</a><br />
        2026-03-10 08:30:00
        <a href="/corp/view/vCB_BulletinDetail.php?stockid=600519&id=2">Annual report</a><br />
      </ul>
    </div>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))

    source = SinaAnnouncementSource(transport=transport)

    result = source.fetch(
        "600519",
        "sh",
        since=datetime(2026, 3, 11, 0, 0, tzinfo=timezone.utc),
    )

    assert result == [
        RawAnnouncement(
            title="Dividend plan",
            published_at=datetime(2026, 3, 11, 9, 45, tzinfo=timezone.utc),
            source="Sina",
            url="https://vip.stock.finance.sina.com.cn/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1",
            summary=None,
        )
    ]



def test_sina_announcement_source_maps_html_rows_to_raw_announcements():
    html = """
    <html>
      <body>
        <div class="datelist">
          <ul>
            <li>
              <a href="/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1">Dividend plan</a>
              <span class="date">2026-03-11 09:45:00</span>
            </li>
          </ul>
        </div>
      </body>
    </html>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))

    source = SinaAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert result == [
        RawAnnouncement(
            title="Dividend plan",
            published_at=datetime(2026, 3, 11, 9, 45, tzinfo=timezone.utc),
            source="Sina",
            url="https://vip.stock.finance.sina.com.cn/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1",
            summary=None,
        )
    ]



def test_sina_announcement_source_keeps_absolute_urls():
    html = """
    <div class="datelist">
      <ul>
        <li>
          <a href="https://vip.stock.finance.sina.com.cn/corp/view/vCB_BulletinDetail.php?stockid=000001&id=2">Absolute url item</a>
          <span class="date">2026-03-11 10:00:00</span>
        </li>
      </ul>
    </div>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))

    source = SinaAnnouncementSource(transport=transport)

    result = source.fetch("000001", "sz")

    assert result == [
        RawAnnouncement(
            title="Absolute url item",
            published_at=datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc),
            source="Sina",
            url="https://vip.stock.finance.sina.com.cn/corp/view/vCB_BulletinDetail.php?stockid=000001&id=2",
            summary=None,
        )
    ]



def test_sina_announcement_source_raises_clear_error_for_missing_markup():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="<html><body><p>empty</p></body></html>")
    )

    source = SinaAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="markup missing div.datelist ul li rows"):
        source.fetch("600519", "sh")


def test_sina_announcement_source_retries_on_timeout():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise httpx.TimeoutException("timeout")
        html = """
        <div class="datelist">
          <ul>
            <li>
              <a href="/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1">Success after retry</a>
              <span class="date">2026-03-11 10:00:00</span>
            </li>
          </ul>
        </div>
        """
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(mock_handler)
    source = SinaAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].title == "Success after retry"
    assert attempt_count == 2


def test_sina_announcement_source_does_not_retry_parse_errors():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        return httpx.Response(200, text="<html><body><p>empty</p></body></html>")

    transport = httpx.MockTransport(mock_handler)
    source = SinaAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="markup missing div.datelist ul li rows"):
        source.fetch("600519", "sh")

    assert attempt_count == 1


def test_sina_announcement_source_clear_error_for_missing_title():
    html = """
    <div class="datelist">
      <ul>
        <li>
          <span class="date">2026-03-11 10:00:00</span>
        </li>
      </ul>
    </div>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))
    source = SinaAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="row 0.*missing link"):
        source.fetch("600519", "sh")


def test_sina_announcement_source_clear_error_for_missing_date():
    html = """
    <div class="datelist">
      <ul>
        <li>
          <a href="/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1">Title</a>
        </li>
      </ul>
    </div>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))
    source = SinaAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="row 0.*missing date"):
        source.fetch("600519", "sh")


def test_sina_announcement_source_logs_successful_fetch(caplog):
    import logging

    html = """
    <div class="datelist">
      <ul>
        <li>
          <a href="/corp/view/vCB_BulletinDetail.php?stockid=600519&id=1">Item</a>
          <span class="date">2026-03-11 10:00:00</span>
        </li>
      </ul>
    </div>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))
    source = SinaAnnouncementSource(transport=transport)

    with caplog.at_level(logging.INFO):
        result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert any("Provider fetch completed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)


def test_sina_announcement_source_logs_failed_fetch(caplog):
    import logging

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="<html><body><p>empty</p></body></html>")
    )
    source = SinaAnnouncementSource(transport=transport)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            source.fetch("600519", "sh")

    assert any("Provider fetch failed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)
