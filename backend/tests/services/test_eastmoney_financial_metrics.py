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
                            "REPORT_DATE_NAME": "2025Q4",
                            "TOTAL_OPERATE_INCOME": "1000000000.0000",
                            "PARENT_NETPROFIT": "100000000.0000",
                            "BASIC_EPS": "1.2500",
                            "WEIGHTAVG_ROE": "0.150000",
                            "DEBT_ASSET_RATIO": "0.450000",
                        },
                        {
                            "REPORT_DATE_NAME": "2025Q3",
                            "TOTAL_OPERATE_INCOME": "900000000.0000",
                            "PARENT_NETPROFIT": "90000000.0000",
                            "BASIC_EPS": "1.1000",
                            "WEIGHTAVG_ROE": None,
                            "DEBT_ASSET_RATIO": "0.470000",
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
            debt_to_asset_ratio=Decimal("0.450000"),
        ),
        RawFinancialMetrics(
            report_period="2025Q3",
            revenue=Decimal("900000000.0000"),
            net_profit=Decimal("90000000.0000"),
            eps=Decimal("1.1000"),
            roe=None,
            debt_to_asset_ratio=Decimal("0.470000"),
        ),
    ]



def test_eastmoney_financial_metrics_source_raises_clear_error_for_missing_result_data():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"result": None})
    )

    source = EastmoneyFinancialMetricsSource(transport=transport)

    with pytest.raises(ValueError, match="financial metrics payload missing result.data"):
        source.fetch("600519", "sh")
