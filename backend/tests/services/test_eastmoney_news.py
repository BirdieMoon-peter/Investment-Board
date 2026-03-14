from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.eastmoney_news import EastmoneyNewsSource
from app.services.providers.raw_types import RawNewsItem



def test_eastmoney_news_source_maps_json_rows_to_raw_news_items():
    def mock_handler(request):
        page_index = int(request.url.params.get("pageIndex", "1"))
        if page_index == 1:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "list": [
                            {
                                "title": "Consumer demand stays firm",
                                "publish_time": "2026-03-11 09:30:00",
                                "info_code": "202603110001",
                                "content": "Channel checks stayed constructive.",
                            }
                        ]
                    }
                },
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)

    source = EastmoneyNewsSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert result == [
        RawNewsItem(
            title="Consumer demand stays firm",
            published_at=datetime(2026, 3, 11, 9, 30, tzinfo=timezone.utc),
            source="Eastmoney",
            url="https://finance.eastmoney.com/a/202603110001.html",
            summary="Channel checks stayed constructive.",
        )
    ]



def test_eastmoney_news_source_filters_rows_older_than_since():
    def mock_handler(request):
        page_index = int(request.url.params.get("pageIndex", "1"))
        if page_index == 1:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "list": [
                            {
                                "title": "Pre-open note",
                                "publish_time": "2026-03-11 08:00:00",
                                "info_code": "202603110010",
                            },
                            {
                                "title": "Midday note",
                                "publish_time": "2026-03-11 12:30:00",
                                "info_code": "202603110011",
                            },
                        ]
                    }
                },
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)

    source = EastmoneyNewsSource(transport=transport)

    result = source.fetch(
        "600519",
        "sh",
        since=datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc),
    )

    assert [item.title for item in result] == ["Midday note"]



def test_eastmoney_news_source_raises_clear_error_for_empty_payload():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": {"list": []}})
    )

    source = EastmoneyNewsSource(transport=transport)

    with pytest.raises(ValueError, match="Eastmoney news payload is empty"):
        source.fetch("600519", "sh")


def test_eastmoney_news_source_degrades_to_empty_results_on_http_400(caplog):
    import logging

    transport = httpx.MockTransport(
        lambda request: httpx.Response(400, json={"message": "bad request"})
    )
    source = EastmoneyNewsSource(transport=transport)

    with caplog.at_level(logging.WARNING):
        result = source.fetch("600519", "sh")

    assert result == []
    assert any("degraded" in record.message.lower() for record in caplog.records)
    assert any("400" in record.message for record in caplog.records)
    assert not any("Provider fetch failed" in record.message for record in caplog.records)


def test_eastmoney_news_source_retries_on_timeout():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        page_index = int(request.url.params.get("pageIndex", "1"))
        if attempt_count == 1:
            raise httpx.TimeoutException("timeout")
        if page_index == 1:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "list": [
                            {
                                "title": "Success after retry",
                                "publish_time": "2026-03-11 10:00:00",
                                "info_code": "202603110001",
                            }
                        ]
                    }
                },
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyNewsSource(transport=transport)

    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].title == "Success after retry"
    assert attempt_count == 3  # 1 timeout + 1 retry + 1 page 2 check


def test_eastmoney_news_source_does_not_retry_parse_errors():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyNewsSource(transport=transport)

    with pytest.raises(ValueError, match="Eastmoney news payload is empty"):
        source.fetch("600519", "sh")

    assert attempt_count == 1


def test_eastmoney_news_source_tolerates_missing_summary():
    def mock_handler(request):
        page_index = int(request.url.params.get("pageIndex", "1"))
        if page_index == 1:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "list": [
                            {
                                "title": "No summary item",
                                "publish_time": "2026-03-11 10:00:00",
                                "info_code": "202603110001",
                            }
                        ]
                    }
                },
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyNewsSource(transport=transport)
    result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert result[0].summary is None


def test_eastmoney_news_source_clear_error_for_missing_title():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "list": [
                        {
                            "publish_time": "2026-03-11 10:00:00",
                            "info_code": "202603110001",
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneyNewsSource(transport=transport)

    with pytest.raises(ValueError, match="row 0.*missing title"):
        source.fetch("600519", "sh")


def test_eastmoney_news_source_fetches_multiple_pages():
    page_count = 0

    def mock_handler(request):
        nonlocal page_count
        page_count += 1
        page_index = int(request.url.params.get("pageIndex", "1"))

        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": f"Page 1 item {i}", "publish_time": "2026-03-11 10:00:00", "info_code": f"2026{i}"}
                    for i in range(20)
                ]}}
            )
        elif page_index == 2:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": f"Page 2 item {i}", "publish_time": "2026-03-11 09:00:00", "info_code": f"2026{i+20}"}
                    for i in range(20)
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyNewsSource(transport=transport)

    result = source.fetch("600519", "sh", max_pages=2)

    assert len(result) == 40
    assert page_count == 2


def test_eastmoney_news_source_stops_at_empty_page():
    page_count = 0

    def mock_handler(request):
        nonlocal page_count
        page_count += 1
        page_index = int(request.url.params.get("pageIndex", "1"))

        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": "Page 1 item", "publish_time": "2026-03-11 10:00:00", "info_code": "20261"}
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyNewsSource(transport=transport)

    result = source.fetch("600519", "sh", max_pages=5)

    assert len(result) == 1
    assert page_count == 2


def test_eastmoney_news_source_logs_successful_fetch(caplog):
    import logging

    def mock_handler(request):
        page_index = int(request.url.params.get("pageIndex", "1"))
        if page_index == 1:
            return httpx.Response(
                200,
                json={"data": {"list": [
                    {"title": "Item", "publish_time": "2026-03-11 10:00:00", "info_code": "202603110001"}
                ]}}
            )
        else:
            return httpx.Response(200, json={"data": {"list": []}})

    transport = httpx.MockTransport(mock_handler)
    source = EastmoneyNewsSource(transport=transport)

    with caplog.at_level(logging.INFO):
        result = source.fetch("600519", "sh")

    assert len(result) == 1
    assert any("Provider fetch completed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)


def test_eastmoney_news_source_logs_failed_fetch(caplog):
    import logging

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"unexpected": []})
    )

    source = EastmoneyNewsSource(transport=transport)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            source.fetch("600519", "sh")

    assert any("Provider fetch failed" in record.message for record in caplog.records)
    assert any("sh:600519" in record.message for record in caplog.records)
