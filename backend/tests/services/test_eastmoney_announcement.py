from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.eastmoney_announcement import EastmoneyAnnouncementSource
from app.services.providers.raw_types import RawAnnouncement



def test_eastmoney_announcement_source_maps_json_rows_to_raw_announcements():
    def mock_handler(request):
        page_index = int(request.url.params.get("page_index", "1"))
        if page_index == 1:
            return httpx.Response(
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
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)

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
    def mock_handler(request):
        page_index = int(request.url.params.get("page_index", "1"))
        if page_index == 1:
            return httpx.Response(
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
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)

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


def test_eastmoney_announcement_source_retries_on_timeout():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        page_index = int(request.url.params.get("page_index", "1"))
        if attempt_count == 1:
            raise httpx.TimeoutException("timeout")
        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {
                        "title": "Success after retry",
                        "notice_date": "2026-03-11 10:00:00",
                        "art_code": "AN001",
                    }
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].title == "Success after retry"
    assert attempt_count == 3  # 1 timeout + 1 retry + 1 page 2 check


def test_eastmoney_announcement_source_does_not_retry_parse_errors():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        return httpx.Response(200, json={"unexpected": []})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match="payload missing data.list"):
        source.fetch("600519", "sh")

    assert attempt_count == 1


def test_eastmoney_announcement_source_tolerates_missing_summary():
    def mock_handler(request):
        page_index = int(request.url.params.get("page_index", "1"))
        if page_index == 1:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "list": [
                            {
                                "title": "No summary item",
                                "notice_date": "2026-03-11 10:00:00",
                                "art_code": "AN001",
                                # summary is missing
                            }
                        ]
                    }
                },
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)
    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].summary is None


def test_eastmoney_announcement_source_clear_error_for_missing_title():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "list": [
                        {
                            # title is missing
                            "notice_date": "2026-03-11 10:00:00",
                            "art_code": "AN001",
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneyAnnouncementSource(transport=transport)

    with pytest.raises(ValueError, match=r"row 0.*missing title"):
        source.fetch("600519", "sh")


def test_eastmoney_announcement_source_fetches_multiple_pages():
    page_count = 0

    def mock_handler(request):
        nonlocal page_count
        page_count += 1
        page_index = int(request.url.params.get("page_index", "1"))

        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": f"Page 1 item {i}", "notice_date": "2026-03-11 10:00:00", "art_code": f"AN{i}"}
                    for i in range(50)
                ]}}
            )
        elif page_index == 2:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": f"Page 2 item {i}", "notice_date": "2026-03-11 09:00:00", "art_code": f"AN{i+50}"}
                    for i in range(50)
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh", max_pages=2)

    assert len(result) == 100
    assert page_count == 2


def test_eastmoney_announcement_source_stops_at_empty_page():
    page_count = 0

    def mock_handler(request):
        nonlocal page_count
        page_count += 1
        page_index = int(request.url.params.get("page_index", "1"))

        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": "Page 1 item", "notice_date": "2026-03-11 10:00:00", "art_code": "AN1"}
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    result = source.fetch("600519", "sh", max_pages=5)

    assert len(result) == 1
    assert page_count == 2


def test_eastmoney_announcement_source_logs_successful_fetch(caplog):
    import logging

    def mock_handler(request):
        page_index = int(request.url.params.get("page_index", "1"))
        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": "Item", "notice_date": "2026-03-11 10:00:00", "art_code": "AN001"}
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyAnnouncementSource(transport=transport)

    with caplog.at_level(logging.INFO):
        result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert any("Provider fetch completed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)


def test_eastmoney_announcement_source_logs_failed_fetch(caplog):
    import logging

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"unexpected": []})
    )

    source = EastmoneyAnnouncementSource(transport=transport)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            source.fetch("600519", "sh")

    assert any("Provider fetch failed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)

