from datetime import datetime, timezone

import httpx
import pytest

from app.services.providers.eastmoney_news import EastmoneyNewsSource
from app.services.providers.raw_types import RawNewsItem



def test_eastmoney_news_source_maps_json_rows_to_raw_news_items():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
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
    )

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
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
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
    )

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
