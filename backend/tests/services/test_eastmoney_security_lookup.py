import httpx
import pytest

from app.services.providers.eastmoney_security_lookup import EastmoneySecurityLookupSource
from app.services.providers.raw_types import RawSecurityLookup


def test_eastmoney_security_lookup_source_maps_real_payload_to_security_seed():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "QuotationCodeTable": {
                    "Data": [
                        {
                            "Code": "600519",
                            "Name": "Kweichow Moutai",
                            "SecurityTypeName": "A股",
                            "MktNum": "1",
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneySecurityLookupSource(transport=transport)

    result = source.fetch("SH", "600519")

    assert result == RawSecurityLookup(
        market="SH",
        code="600519",
        name="Kweichow Moutai",
        industry="A股",
    )


def test_eastmoney_security_lookup_source_raises_for_missing_match():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "QuotationCodeTable": {
                    "Data": [
                        {
                            "Code": "000001",
                            "Name": "Ping An Bank",
                            "SecurityTypeName": "A股",
                            "MktNum": "0",
                        }
                    ]
                }
            },
        )
    )

    source = EastmoneySecurityLookupSource(transport=transport)

    with pytest.raises(ValueError, match="did not match SH:600519"):
        source.fetch(" sh ", "600519")
