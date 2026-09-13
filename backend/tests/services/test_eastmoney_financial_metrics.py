from decimal import Decimal

import httpx
import pytest

from app.services.providers.eastmoney_financial_metrics import EastmoneyFinancialMetricsSource
from app.services.providers.raw_types import RawFinancialMetrics



def test_eastmoney_financial_metrics_source_maps_rows_to_raw_metrics():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "result": {
                    "data": [
                        {
                            "DATATYPE": "2025年 年报",
                            "TOTAL_OPERATE_INCOME": "1000000000.0000",
                            "PARENT_NETPROFIT": "100000000.0000",
                            "BASIC_EPS": "1.2500",
                            "WEIGHTAVG_ROE": "0.150000",
                        },
                        {
                            "DATATYPE": "2025年 三季报",
                            "TOTAL_OPERATE_INCOME": "900000000.0000",
                            "PARENT_NETPROFIT": "90000000.0000",
                            "BASIC_EPS": "1.1000",
                            "WEIGHTAVG_ROE": None,
                        },
                    ]
                }
            },
        )
    )

    source = EastmoneyFinancialMetricsSource(transport=transport)

    result = source.fetch(" 600519 ", " sh ")

    assert result == [
        RawFinancialMetrics(
            report_period="2025Q4",
            revenue=Decimal("1000000000.0000"),
            net_profit=Decimal("100000000.0000"),
            eps=Decimal("1.2500"),
            roe=Decimal("0.150000"),
            debt_to_asset_ratio=None,
        ),
        RawFinancialMetrics(
            report_period="2025Q3",
            revenue=Decimal("900000000.0000"),
            net_profit=Decimal("90000000.0000"),
            eps=Decimal("1.1000"),
            roe=None,
            debt_to_asset_ratio=None,
        ),
    ]



def test_eastmoney_financial_metrics_source_uses_current_filter_and_sort_columns():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"result": {"data": []}})

    source = EastmoneyFinancialMetricsSource(transport=httpx.MockTransport(handler))

    source.fetch(" 002594 ", " sz ")

    assert len(requests) == 1
    params = requests[0].url.params
    assert params.get("filter") == '(SECURITY_CODE="002594")'
    assert params.get("sortColumns") == "NOTICE_DATE"
    assert params.get("columns") == "SECURITY_CODE,SECUCODE,DATATYPE,NOTICE_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,BASIC_EPS,WEIGHTAVG_ROE"


    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"result": None})
    )

    source = EastmoneyFinancialMetricsSource(transport=transport)

    with pytest.raises(ValueError, match="financial metrics payload missing result.data"):
        source.fetch("600519", "sh")
