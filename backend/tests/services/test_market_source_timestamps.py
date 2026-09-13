from datetime import UTC, datetime
import json

import httpx
import pytest

from app.services.providers.tencent_market_index import TencentMarketIndexSource
from app.services.providers.sina_market_index import SinaMarketIndexSource
from app.services.providers.netease_market_index import NetEaseMarketIndexSource
from app.services.providers.sina_fund_quote_snapshot import SinaFundQuoteSnapshotSource


@pytest.mark.parametrize("source_time, expected", [
    ("20260911161403", datetime(2026, 9, 11, 8, 14, 3, tzinfo=UTC)),
    ("", None), ("0", None), ("invalid", None), ("20260931161403", None),
])
def test_tencent_uses_source_time_or_unknown(source_time, expected):
    fields = [""] * 33
    fields[1], fields[3], fields[30], fields[31], fields[32] = "上证指数", "3888.11", source_time, "10.1", "0.2"
    source = TencentMarketIndexSource(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, text='v_sh000001="' + '~'.join(fields) + '";')
    ))
    result = source.fetch()
    assert len(result) == 1
    assert result[0].snapshot_time == expected


def test_sina_simplified_index_has_unknown_source_time():
    source = SinaMarketIndexSource(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, text='var hq_str_s_sh000001="上证指数,3813.28,-143.77,-3.63,8047388,108624829";'
    )))
    assert source.fetch()[0].snapshot_time is None


def test_netease_does_not_invent_time_when_payload_has_no_verified_timestamp():
    source = NetEaseMarketIndexSource(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, text='_ntes_quote_callback(' + json.dumps({"0000001": {"price": "3813.28", "updown": "1", "percent": "0.1"}}) + ')'
    )))
    assert source.fetch()[0].snapshot_time is None


def test_sina_fund_china_wall_time_is_normalized_to_utc():
    fields = ["0"] * 32
    fields[1], fields[2], fields[3], fields[30], fields[31] = "1.05", "1.0", "1.1", "2026-09-11", "15:00:00"
    source = SinaFundQuoteSnapshotSource(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, text='var hq_str_sh510300="' + ','.join(fields) + '";'
    )))
    assert source.fetch("510300", "SH").snapshot_time == datetime(2026, 9, 11, 7, tzinfo=UTC)


def test_sina_fund_change_uses_previous_close_not_open():
    from decimal import Decimal
    fields = ["0"] * 32
    fields[0], fields[1], fields[2], fields[3] = "黄金LOF", "1.679", "1.710", "1.682"
    fields[30], fields[31] = "2026-09-11", "15:00:00"
    source = SinaFundQuoteSnapshotSource(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, text='var hq_str_sz164701="' + ','.join(fields) + '";'
    )))
    quote = source.fetch("164701", "SZ")
    assert quote.last_price == Decimal("1.682")
    assert quote.change_amount == Decimal("-0.0280")
    assert quote.change_percent == Decimal("-1.6374")
