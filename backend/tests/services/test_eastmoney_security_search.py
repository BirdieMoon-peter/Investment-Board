import httpx

from app.services.providers.eastmoney_security_search import EastmoneySecuritySearchSource


def test_eastmoney_security_search_returns_sh_sz_results_only() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "QuotationCodeTable": {
                    "Data": [
                        {"Code": "600519", "Name": "Kweichow Moutai", "MktNum": "1", "SecurityTypeName": "Beverages"},
                        {"Code": "000001", "Name": "Ping An Bank", "MktNum": "0", "SecurityTypeName": "Banking"},
                        {"Code": "00700", "Name": "Tencent", "MktNum": "116", "SecurityTypeName": "Internet"},
                    ]
                }
            },
        )
    )

    source = EastmoneySecuritySearchSource(transport=transport)
    results = source.search("Ping")

    assert [(item.market, item.code) for item in results] == [("SH", "600519"), ("SZ", "000001")]


def test_eastmoney_security_search_deduplicates_results() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "QuotationCodeTable": {
                    "Data": [
                        {"Code": "000001", "Name": "Ping An Bank", "MktNum": "0", "SecurityTypeName": "Banking"},
                        {"Code": "000001", "Name": "Ping An Bank", "MktNum": "2", "SecurityTypeName": "Banking"},
                    ]
                }
            },
        )
    )

    source = EastmoneySecuritySearchSource(transport=transport)
    results = source.search("000001")

    assert len(results) == 1
    assert results[0].market == "SZ"
    assert results[0].code == "000001"
