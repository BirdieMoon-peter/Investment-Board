from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.raw_types import RawNewsItem
from app.services.providers.sina_news import SinaNewsSource



def test_sina_news_source_maps_json_rows_to_raw_news_items():
    def mock_handler(request):
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "title": "Broker sees margin resilience",
                            "ctime": "2026-03-11 10:15:00",
                            "url": "https://finance.sina.com.cn/stock/company/2026-03-11/doc-example.shtml",
                            "intro": "The desk kept its outperform stance.",
                        }
                    ]
                },
            )
        else:
            return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(mock_handler)

    source = SinaNewsSource(transport=transport)

    result = source.fetch("000001", "sz")

    assert result == [
        RawNewsItem(
            title="Broker sees margin resilience",
            published_at=datetime(2026, 3, 11, 10, 15, tzinfo=timezone.utc),
            source="Sina",
            url="https://finance.sina.com.cn/stock/company/2026-03-11/doc-example.shtml",
            summary="The desk kept its outperform stance.",
        )
    ]



def test_sina_news_source_normalizes_relative_urls():
    def mock_handler(request):
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "result": {
                        "data": [
                            {
                                "title": "Relative link item",
                                "ctime": "2026-03-11 11:00:00",
                                "url": "/stock/company/2026-03-11/doc-relative.shtml",
                                "intro": "Relative path should be normalized.",
                            }
                        ]
                    }
                },
            )
        else:
            return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(mock_handler)

    source = SinaNewsSource(transport=transport)

    result = source.fetch("000001", "sz")

    assert result == [
        RawNewsItem(
            title="Relative link item",
            published_at=datetime(2026, 3, 11, 11, 0, tzinfo=timezone.utc),
            source="Sina",
            url="https://finance.sina.com.cn/stock/company/2026-03-11/doc-relative.shtml",
            summary="Relative path should be normalized.",
        )
    ]



def test_sina_news_source_raises_clear_error_for_invalid_rows():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": [
                    {
                        "title": "Missing url",
                        "ctime": "2026-03-11 11:30:00",
                    }
                ]
            },
        )
    )

    source = SinaNewsSource(transport=transport)

    with pytest.raises(ValueError, match="Sina news row 0 missing url"):
        source.fetch("000001", "sz")


def test_sina_news_source_degrades_to_empty_results_on_http_404(caplog):
    import logging

    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, json={"message": "not found"})
    )
    source = SinaNewsSource(transport=transport)

    with caplog.at_level(logging.WARNING):
        result = source.fetch("000001", "sz")

    assert result == []
    assert any("degraded" in record.message.lower() for record in caplog.records)
    assert any("404" in record.message for record in caplog.records)
    assert not any("Provider fetch failed" in record.message for record in caplog.records)


def test_sina_news_source_retries_on_timeout():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        page = int(request.url.params.get("page", "1"))
        if attempt_count == 1:
            raise httpx.TimeoutException("timeout")
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "title": "Success after retry",
                            "ctime": "2026-03-11 10:00:00",
                            "url": "https://finance.sina.com.cn/stock/company/2026-03-11/doc-example.shtml",
                        }
                    ]
                },
            )
        else:
            return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(mock_handler)
    source = SinaNewsSource(transport=transport)

    result = source.fetch("000001", "sz")

    assert len(result) == 1
    assert result[0].title == "Success after retry"
    assert attempt_count == 3  # 1 timeout + 1 retry + 1 page 2 check


def test_sina_news_source_does_not_retry_parse_errors():
    attempt_count = 0

    def mock_handler(request):
        nonlocal attempt_count
        attempt_count += 1
        return httpx.Response(200, json={"unexpected": []})

    transport = httpx.MockTransport(mock_handler)
    source = SinaNewsSource(transport=transport)

    with pytest.raises(ValueError, match="Sina news payload missing data rows"):
        source.fetch("000001", "sz")

    assert attempt_count == 1


def test_sina_news_source_tolerates_missing_summary():
    def mock_handler(request):
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "title": "No summary item",
                            "ctime": "2026-03-11 10:00:00",
                            "url": "https://finance.sina.com.cn/stock/company/2026-03-11/doc-example.shtml",
                        }
                    ]
                },
            )
        else:
            return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(mock_handler)
    source = SinaNewsSource(transport=transport)
    result = source.fetch("000001", "sz")

    assert len(result) == 1
    assert result[0].summary is None


def test_sina_news_source_fetches_multiple_pages():
    page_count = 0

    def mock_handler(request):
        nonlocal page_count
        page_count += 1
        page = int(request.url.params.get("page", "1"))

        if page == 1:
            return httpx.Response(
                200,
                json={"data": [
                    {"title": f"Page 1 item {i}", "ctime": "2026-03-11 10:00:00", "url": f"/doc{i}.shtml"}
                    for i in range(20)
                ]}
            )
        elif page == 2:
            return httpx.Response(
                200,
                json={"data": [
                    {"title": f"Page 2 item {i}", "ctime": "2026-03-11 09:00:00", "url": f"/doc{i+20}.shtml"}
                    for i in range(20)
                ]}
            )
        else:
            return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(mock_handler)
    source = SinaNewsSource(transport=transport)

    result = source.fetch("000001", "sz", max_pages=2)

    assert len(result) == 40
    assert page_count == 2


def test_sina_news_source_stops_at_empty_page():
    page_count = 0

    def mock_handler(request):
        nonlocal page_count
        page_count += 1
        page = int(request.url.params.get("page", "1"))

        if page == 1:
            return httpx.Response(
                200,
                json={"data": [
                    {"title": "Page 1 item", "ctime": "2026-03-11 10:00:00", "url": "/doc1.shtml"}
                ]}
            )
        else:
            return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(mock_handler)
    source = SinaNewsSource(transport=transport)

    result = source.fetch("000001", "sz", max_pages=5)

    assert len(result) == 1
    assert page_count == 2


def test_sina_news_source_logs_successful_fetch(caplog):
    import logging

    def mock_handler(request):
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(
                200,
                json={"data": [
                    {"title": "Item", "ctime": "2026-03-11 10:00:00", "url": "/doc1.shtml"}
                ]}
            )
        else:
            return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(mock_handler)
    source = SinaNewsSource(transport=transport)

    with caplog.at_level(logging.INFO):
        result = source.fetch("000001", "sz")

    assert len(result) == 1
    assert any("Provider fetch completed" in record.message for record in caplog.records)
    assert any("sz:000001" in record.message for record in caplog.records)


def test_sina_news_source_logs_failed_fetch(caplog):
    import logging

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"unexpected": []})
    )

    source = SinaNewsSource(transport=transport)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            source.fetch("000001", "sz")

    assert any("Provider fetch failed" in record.message for record in caplog.records)
    assert any("sz:000001" in record.message for record in caplog.records)
