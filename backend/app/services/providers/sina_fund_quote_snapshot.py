from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawQuoteSnapshot


class SinaFundQuoteSnapshotSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self, stock_code: str, market: str) -> RawQuoteSnapshot:
        normalized_market = market.strip().lower()
        normalized_code = stock_code.strip()
        if normalized_market not in {"sh", "sz"}:
            raise ValueError(f"unsupported market: {market}")
        if not normalized_code:
            raise ValueError("stock code is required")

        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                "https://hq.sinajs.cn/list=" + f"{normalized_market}{normalized_code}",
                headers={"Referer": "https://finance.sina.com.cn"},
            )
            response.raise_for_status()
            payload = response.text

        return _parse_sina_quote_payload(payload, market=normalized_market, code=normalized_code)



def _parse_sina_quote_payload(payload: str, *, market: str, code: str) -> RawQuoteSnapshot:
    if '="' not in payload or '";' not in payload:
        raise ValueError("Sina fund quote payload is invalid")

    content = payload.split('="', 1)[1].rsplit('";', 1)[0]
    parts = [part.strip() for part in content.split(',')]
    if len(parts) < 32:
        raise ValueError("Sina fund quote payload is incomplete")

    previous_close = _required_decimal(parts[2])
    last_price = _required_decimal(parts[3])
    if previous_close == 0:
        raise ValueError("Sina fund quote previous close is zero")

    change_amount = (last_price - previous_close).quantize(Decimal("0.0001"))
    change_percent = ((change_amount / previous_close) * Decimal("100")).quantize(Decimal("0.0001"))
    snapshot_time = datetime.strptime(f"{parts[30]} {parts[31]}", "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=ZoneInfo("Asia/Shanghai")
    ).astimezone(UTC)

    return RawQuoteSnapshot(
        last_price=last_price,
        change_amount=change_amount,
        change_percent=change_percent,
        snapshot_time=snapshot_time,
    )



def _required_decimal(value: str) -> Decimal:
    if not value:
        raise ValueError("Sina fund quote field is empty")
    return Decimal(value)
