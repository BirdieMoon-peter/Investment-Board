from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.raw_types import RawNewsItem
from app.services.providers.sina_news import SinaNewsSource



def test_sina_news_source_maps_json_rows_to_raw_news_items():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
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
    )

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
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
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
    )

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
