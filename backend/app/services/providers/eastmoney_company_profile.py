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
        provider_code = _provider_code(normalized_market, normalized_code)

        with build_provider_client(transport=self._transport) as client:
            response = client.get(
                _EASTMONEY_COMPANY_PROFILE_URL,
                params={"code": provider_code},
            )
            response.raise_for_status()
            payload = response.json()

        profile = _extract_profile(payload)
        if not isinstance(profile, dict):
            raise ValueError("Eastmoney company profile payload missing jbzl")

        return RawCompanyProfile(
            full_name=_first_text(profile, "FULLNAME", "gsmc"),
            english_name=_first_text(profile, "ENAME", "ywmc"),
            registered_capital=_first_decimal(profile, "REGCAPITAL", "zczb"),
            establishment_date=_first_date(profile, "FOUNDDATE", "clrq"),
            website=_normalize_website(_first_text(profile, "WEBSITE", "gswz")),
            main_business=_first_text(profile, "MAINBUSINESS", "zyyw", "jyfw", "gsjj"),
            employees=_first_int(profile, "EMPNUM", "ygs", "gyrs"),
        )



def _extract_profile(payload: object) -> object:
    if not isinstance(payload, dict):
        return None
    return payload.get("jbzl")



def _provider_code(market: str, code: str) -> str:
    if market not in {"SZ", "SH"}:
        raise ValueError(f"unsupported market: {market}")
    if not code:
        raise ValueError("stock code is required")
    return f"{market}{code}"



def _first_text(profile: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        text = _optional_text(profile.get(key))
        if text is not None:
            return text
    return None



def _first_decimal(profile: dict[str, object], *keys: str) -> Decimal | None:
    for key in keys:
        value = _optional_decimal(profile.get(key))
        if value is not None:
            return value
    return None



def _first_date(profile: dict[str, object], *keys: str) -> date | None:
    for key in keys:
        value = _optional_date(profile.get(key))
        if value is not None:
            return value
    return None



def _first_int(profile: dict[str, object], *keys: str) -> int | None:
    for key in keys:
        value = _optional_int(profile.get(key))
        if value is not None:
            return value
    return None



def _normalize_website(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"



def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None



def _optional_decimal(value: object) -> Decimal | None:
    text = _optional_text(value)
    if text is None:
        return None
    normalized = text.replace(",", "")
    multiplier = Decimal("1")
    if normalized.endswith("亿"):
        normalized = normalized[:-1]
        multiplier = Decimal("100000000")
    elif normalized.endswith("万"):
        normalized = normalized[:-1]
        multiplier = Decimal("10000")
    return Decimal(normalized) * multiplier



def _optional_date(value: object) -> date | None:
    text = _optional_text(value)
    return date.fromisoformat(text) if text is not None else None



def _optional_int(value: object) -> int | None:
    text = _optional_text(value)
    if text is None:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None
