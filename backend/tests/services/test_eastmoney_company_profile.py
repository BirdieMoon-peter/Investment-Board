from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.providers.eastmoney_company_profile import EastmoneyCompanyProfileSource
from app.services.providers.raw_types import RawCompanyProfile



def test_eastmoney_company_profile_source_maps_payload_to_raw_profile():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "jbzl": {
                    "FULLNAME": "平安银行股份有限公司",
                    "ENAME": "Ping An Bank Co., Ltd.",
                    "REGCAPITAL": "19405918198.0000",
                    "FOUNDDATE": "1987-12-22",
                    "WEBSITE": "https://bank.pingan.com",
                    "MAINBUSINESS": "商业银行业务",
                    "EMPNUM": "35000",
                }
            },
        )
    )

    source = EastmoneyCompanyProfileSource(transport=transport)

    result = source.fetch(" 600519 ", " sh ")

    assert result == RawCompanyProfile(
        full_name="平安银行股份有限公司",
        english_name="Ping An Bank Co., Ltd.",
        registered_capital=Decimal("19405918198.0000"),
        establishment_date=date(1987, 12, 22),
        website="https://bank.pingan.com",
        main_business="商业银行业务",
        employees=35000,
    )



def test_eastmoney_company_profile_source_raises_clear_error_for_missing_jbzl():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"jbzl": None})
    )

    source = EastmoneyCompanyProfileSource(transport=transport)

    with pytest.raises(ValueError, match="company profile payload missing jbzl"):
        source.fetch("600519", "sh")
