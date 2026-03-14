from datetime import date
from decimal import Decimal

import httpx

from app.services.providers.http_client import build_provider_client
from app.services.providers.raw_types import RawCompanyProfile

_EASTMONEY_COMPANY_PROFILE_URL = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax"


class EastmoneyCompanyProfileSource:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def fetch(self, stock_code: str, market: str) -> RawCompanyProfile:
        normalized_code = stock_code.strip()
        normalized_market = market.strip().upper()
        secid = _secid(normalized_market, normalized_code)

        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                _EASTMONEY_COMPANY_PROFILE_URL,
                params={"code": secid},
            )
            response.raise_for_status()
            payload = response.json()

        profile = _extract_profile(payload)
        if not isinstance(profile, dict):
            raise ValueError("Eastmoney company profile payload missing jbzl")

        return RawCompanyProfile(
            full_name=_optional_text(profile.get("FULLNAME")),
            english_name=_optional_text(profile.get("ENAME")),
            registered_capital=_optional_decimal(profile.get("REGCAPITAL")),
            establishment_date=_optional_date(profile.get("FOUNDDATE")),
            website=_optional_text(profile.get("WEBSITE")),
            main_business=_optional_text(profile.get("MAINBUSINESS")),
            employees=_optional_int(profile.get("EMPNUM")),
        )



def _extract_profile(payload: object) -> object:
    if not isinstance(payload, dict):
        return None
    return payload.get("jbzl")



def _secid(market: str, code: str) -> str:
    market_map = {"SZ": "0", "SH": "1"}
    market_prefix = market_map.get(market)
    if market_prefix is None:
        raise ValueError(f"unsupported market: {market}")
    if not code:
        raise ValueError("stock code is required")
    return f"{market_prefix}.{code}"



def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None



def _optional_decimal(value: object) -> Decimal | None:
    text = _optional_text(value)
    return Decimal(text) if text is not None else None



def _optional_date(value: object) -> date | None:
    text = _optional_text(value)
    return date.fromisoformat(text) if text is not None else None



def _optional_int(value: object) -> int | None:
    text = _optional_text(value)
    return int(text) if text is not None else None
