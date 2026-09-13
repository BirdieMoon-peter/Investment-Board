from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.db.models import CompanyProfile, FinancialMetrics, PriceHistory
from app.services.providers import (
    CompanyProfileFetchResult,
    FinancialMetricsFetchResult,
    PriceHistoryFetchResult,
)
from app.services.stock_sync import StockSyncService


class StubAnnouncementProvider:
    def fetch_for_security(self, security_id: int, *, stock_code: str, market: str, since=None):
        return []


class StubNewsProvider:
    def fetch_for_security(self, security_id: int, *, stock_code: str, market: str, since=None):
        return []


@dataclass
class RecordingPriceHistoryProvider:
    result: PriceHistoryFetchResult
    calls: list[dict[str, object]]

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        limit: int = 60,
    ) -> PriceHistoryFetchResult:
        self.calls.append(
            {
                "security_id": security_id,
                "stock_code": stock_code,
                "market": market,
                "limit": limit,
            }
        )
        return self.result


@dataclass
class RecordingFinancialMetricsProvider:
    result: FinancialMetricsFetchResult
    calls: list[dict[str, object]]

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        limit: int = 8,
    ) -> FinancialMetricsFetchResult:
        self.calls.append(
            {
                "security_id": security_id,
                "stock_code": stock_code,
                "market": market,
                "limit": limit,
            }
        )
        return self.result


@dataclass
class RecordingCompanyProfileProvider:
    result: CompanyProfileFetchResult
    calls: list[dict[str, object]]

    def fetch_for_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
    ) -> CompanyProfileFetchResult:
        self.calls.append(
            {
                "security_id": security_id,
                "stock_code": stock_code,
                "market": market,
            }
        )
        return self.result


class RecordingAnnouncementRepository:
    def get_latest_published_at(self, security_id: int):
        return None

    def upsert_many(self, items, commit: bool = True):
        return list(items)


class RecordingNewsRepository:
    def get_latest_published_at(self, security_id: int):
        return None

    def upsert_many(self, items, commit: bool = True):
        return list(items)


class RecordingPriceHistoryRepository:
    def __init__(self):
        self.upsert_calls: list[list[PriceHistory]] = []

    def upsert_many(self, items: list[PriceHistory], commit: bool = True):
        self.upsert_calls.append(items)
        return items


class RecordingFinancialMetricsRepository:
    def __init__(self):
        self.upsert_calls: list[list[FinancialMetrics]] = []

    def upsert_many(self, items: list[FinancialMetrics], commit: bool = True):
        self.upsert_calls.append(items)
        return items


class RecordingCompanyProfileRepository:
    def __init__(self):
        self.upsert_calls: list[CompanyProfile] = []

    def upsert(self, item: CompanyProfile, commit: bool = True):
        self.upsert_calls.append(item)
        return item



def test_sync_security_persists_stock_data_and_collects_warnings():
    security_id = 7
    stock_code = "000001"
    market = "SZ"
    synced_at = datetime(2026, 3, 13, 10, 0)
    price_history_calls: list[dict[str, object]] = []
    financial_metrics_calls: list[dict[str, object]] = []
    company_profile_calls: list[dict[str, object]] = []
    price_history_repository = RecordingPriceHistoryRepository()
    financial_metrics_repository = RecordingFinancialMetricsRepository()
    company_profile_repository = RecordingCompanyProfileRepository()

    service = StockSyncService(
        announcement_provider=StubAnnouncementProvider(),
        news_provider=StubNewsProvider(),
        announcement_repository=RecordingAnnouncementRepository(),
        news_repository=RecordingNewsRepository(),
        price_history_provider=RecordingPriceHistoryProvider(
            PriceHistoryFetchResult(
                items=[
                    PriceHistory(
                        security_id=security_id,
                        trade_date=date(2026, 3, 10),
                        open_price=Decimal("10.5000"),
                        high_price=Decimal("10.8000"),
                        low_price=Decimal("10.4000"),
                        close_price=Decimal("10.7000"),
                        volume=Decimal("1000000.0000"),
                        amount=Decimal("10700000.0000"),
                    )
                ],
                warnings=["price source timeout"],
            ),
            price_history_calls,
        ),
        financial_metrics_provider=RecordingFinancialMetricsProvider(
            FinancialMetricsFetchResult(
                items=[
                    FinancialMetrics(
                        security_id=security_id,
                        report_period="2025Q4",
                        revenue=Decimal("1000000000.0000"),
                        net_profit=Decimal("100000000.0000"),
                        eps=Decimal("1.2500"),
                        roe=Decimal("0.150000"),
                        debt_to_asset_ratio=Decimal("0.450000"),
                    )
                ],
                warnings=["financial metrics source timeout"],
            ),
            financial_metrics_calls,
        ),
        company_profile_provider=RecordingCompanyProfileProvider(
            CompanyProfileFetchResult(
                item=CompanyProfile(
                    security_id=security_id,
                    full_name="平安银行股份有限公司",
                    english_name="Ping An Bank Co., Ltd.",
                    registered_capital=Decimal("19405918198.0000"),
                    establishment_date=date(1987, 12, 22),
                    website="https://bank.pingan.com",
                    main_business="商业银行业务",
                    employees=35000,
                ),
                warnings=["company profile source timeout"],
            ),
            company_profile_calls,
        ),
        price_history_repository=price_history_repository,
        financial_metrics_repository=financial_metrics_repository,
        company_profile_repository=company_profile_repository,
    )

    result = service.sync_security(
        security_id,
        stock_code=stock_code,
        market=market,
        synced_at=synced_at,
    )

    assert price_history_calls == [
        {
            "security_id": security_id,
            "stock_code": stock_code,
            "market": market,
            "limit": 60,
        }
    ]
    assert financial_metrics_calls == [
        {
            "security_id": security_id,
            "stock_code": stock_code,
            "market": market,
            "limit": 8,
        }
    ]
    assert company_profile_calls == [
        {
            "security_id": security_id,
            "stock_code": stock_code,
            "market": market,
        }
    ]
    assert len(price_history_repository.upsert_calls) == 1
    assert len(financial_metrics_repository.upsert_calls) == 1
    assert len(company_profile_repository.upsert_calls) == 1
    assert result.synced is True
    assert result.announcements_upserted == 0
    assert result.news_items_upserted == 0
    assert result.price_bars_upserted == 1
    assert result.financial_metrics_upserted == 1
    assert result.company_profile_updated is True
    assert result.warnings == [
        "price source timeout",
        "financial metrics source timeout",
        "company profile source timeout",
    ]
    assert result.synced_at == synced_at
