from decimal import Decimal

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawFinancialMetrics

_EASTMONEY_FINANCIAL_METRICS_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


class EastmoneyFinancialMetricsSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        limit: int = 8,
    ) -> list[RawFinancialMetrics]:
        normalized_code = stock_code.strip()
        normalized_market = market.strip().upper()
        security_code = _security_code(normalized_market, normalized_code)

        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                _EASTMONEY_FINANCIAL_METRICS_URL,
                params={
                    "reportName": "RPT_LICO_FN_CPD",
                    "columns": "SECURITY_CODE,SECUCODE,DATATYPE,NOTICE_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,BASIC_EPS,WEIGHTAVG_ROE",
                    "filter": f'(SECURITY_CODE="{security_code}")',
                    "pageNumber": "1",
                    "pageSize": str(limit),
                    "sortColumns": "NOTICE_DATE",
                    "sortTypes": "-1",
                },
            )
            response.raise_for_status()
            payload = response.json()

        rows = _extract_metric_rows(payload)
        if not isinstance(rows, list):
            raise ValueError("Eastmoney financial metrics payload missing result.data")

        return [_parse_metric_row(row) for row in rows]



def _extract_metric_rows(payload: object) -> object:
    if not isinstance(payload, dict):
        return None

    result = payload.get("result")
    if not isinstance(result, dict):
        return None

    return result.get("data")



def _security_code(market: str, code: str) -> str:
    if market not in {"SZ", "SH"}:
        raise ValueError(f"unsupported market: {market}")
    if not code:
        raise ValueError("stock code is required")
    return code



def _parse_metric_row(row: object) -> RawFinancialMetrics:
    if not isinstance(row, dict):
        raise ValueError("Eastmoney financial metrics row is not a dict")

    report_period = _report_period(row)
    return RawFinancialMetrics(
        report_period=report_period,
        revenue=_optional_decimal(row.get("TOTAL_OPERATE_INCOME")),
        net_profit=_optional_decimal(row.get("PARENT_NETPROFIT")),
        eps=_optional_decimal(row.get("BASIC_EPS")),
        roe=_optional_decimal(row.get("WEIGHTAVG_ROE")),
        debt_to_asset_ratio=_optional_decimal(row.get("DEBT_ASSET_RATIO")),
    )



def _report_period(row: dict[str, object]) -> str:
    report_period = row.get("REPORT_DATE_NAME")
    if isinstance(report_period, str) and report_period.strip():
        return report_period.strip()

    datatype = row.get("DATATYPE")
    if not isinstance(datatype, str) or not datatype.strip():
        raise ValueError("Eastmoney financial metrics row missing DATATYPE")
    return _normalize_datatype(datatype)



def _normalize_datatype(datatype: str) -> str:
    normalized = datatype.strip().replace(" ", "")
    if normalized.endswith("一季报"):
        return normalized[:4] + "Q1"
    if normalized.endswith("半年报"):
        return normalized[:4] + "Q2"
    if normalized.endswith("三季报"):
        return normalized[:4] + "Q3"
    if normalized.endswith("年报"):
        return normalized[:4] + "Q4"
    return normalized



def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)
