from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.raw_types import RawAnnouncement
from app.services.providers.sina_announcement import SinaAnnouncementSource



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
