from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.eastmoney_announcement import EastmoneyAnnouncementSource
from app.services.providers.raw_types import RawAnnouncement



def test_eastmoney_announcement_source_maps_json_rows_to_raw_announcements():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "list": [
                        {
                            "title": "Board resolution",
                            "notice_date": "2026-03-11 09:30:00",
                            "art_code": "AN202603110001",
                            "summary": "Approved the annual dividend plan.",
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneyAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert result == [
        RawAnnouncement(
            title="Board resolution",
            published_at=datetime(2026, 3, 11, 9, 30, tzinfo=timezone.utc),
            source="Eastmoney",
            url="https://data.eastmoney.com/notices/detail/AN202603110001.html",
            summary="Approved the annual dividend plan.",
        )
    ]



def test_eastmoney_announcement_source_filters_rows_older_than_since():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "list": [
                        {
                            "title": "Older filing",
                            "notice_date": "2026-03-10 09:00:00",
                            "art_code": "AN202603100001",
                        },
                        {
                            "title": "Fresh filing",
                            "notice_date": "2026-03-11 11:00:00",
                            "art_code": "AN202603110002",
                        },
                    ]
                }
            },
        )
    )

    source = EastmoneyAnnouncementSource(transport=transport)

    result = source.fetch(
        "600519",
        "sh",
        since=datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc),
    )

    assert [item.title for item in result] == ["Fresh filing"]



def test_eastmoney_announcement_source_raises_clear_error_for_bad_payload():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"unexpected": []})
    )

    source = EastmoneyAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="payload missing data.list"):
        source.fetch("600519", "sh")
