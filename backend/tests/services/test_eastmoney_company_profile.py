from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.providers.eastmoney_company_profile import EastmoneyCompanyProfileSource
from app.services.providers.raw_types import RawCompanyProfile



def test_eastmoney_company_profile_source_maps_payload_to_raw_profile():
    requested_codes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_codes.append(str(request.url.params.get("code")))
        return httpx.Response(
            200,
            json={
                "jbzl": {
                    "gsmc": "平安银行股份有限公司",
                    "ywmc": "Ping An Bank Co., Ltd.",
                    "zczb": "194.05918198亿",
                    "FOUNDDATE": "1987-12-22",
                    "gswz": "bank.pingan.com",
                    "jyfw": "商业银行业务",
                    "gyrs": "35000人",
                }
            },
        )

    transport = httpx.MockTransport(handler)

    source = EastmoneyCompanyProfileSource(transport=transport)

    result = source.fetch(" 600519 ", " sh ")

    assert requested_codes == ["SH600519"]
    assert result == RawCompanyProfile(
        full_name="平安银行股份有限公司",
        english_name="Ping An Bank Co., Ltd.",
        registered_capital=Decimal("19405918198.00000000"),
        establishment_date=date(1987, 12, 22),
        website="https://bank.pingan.com",
        main_business="商业银行业务",
        employees=35000,
    )





def test_eastmoney_company_profile_source_falls_back_to_current_live_field_names():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "jbzl": {
                    "gsmc": "比亚迪股份有限公司",
                    "ywmc": "BYD Company Limited",
                    "zczb": "91.17亿",
                    "gswz": "www.bydglobal.com",
                    "jyfw": "新能源汽车关键零部件研发以及上述零部件的关键零件、部件的研发、销售。",
                    "gyrs": "968872",
                }
            },
        )
    )

    source = EastmoneyCompanyProfileSource(transport=transport)

    result = source.fetch("002594", "SZ")

    assert result == RawCompanyProfile(
        full_name="比亚迪股份有限公司",
        english_name="BYD Company Limited",
        registered_capital=Decimal("9117000000"),
        establishment_date=None,
        website="https://www.bydglobal.com",
        main_business="新能源汽车关键零部件研发以及上述零部件的关键零件、部件的研发、销售。",
        employees=968872,
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"jbzl": None})
    )

    source = EastmoneyCompanyProfileSource(transport=transport)

    with pytest.raises(ValueError, match="company profile payload missing jbzl"):
        source.fetch("600519", "sh")
