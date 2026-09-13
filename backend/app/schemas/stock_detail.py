from datetime import date, datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.schemas.timestamps import UTCDateTime

from app.db.models import Announcement, CompanyProfile, FinancialMetrics, NewsItem, PriceBarDaily, PriceHistory, QuoteSnapshot
from app.db.repositories import StockDetail, StockDetailSecurity


class StockDetailSecurityResponse(SQLModel):
    security_id: int
    market: str
    code: str
    name: str
    industry: str | None = None
    status: str

    @classmethod
    def from_repository_model(cls, security: StockDetailSecurity) -> "StockDetailSecurityResponse":
        return cls(
            security_id=security.id,
            market=security.market,
            code=security.code,
            name=security.name,
            industry=security.industry,
            status=security.status,
        )


class StockDetailPriceBarResponse(SQLModel):
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal

    @classmethod
    def from_model(cls, price_bar: PriceBarDaily) -> "StockDetailPriceBarResponse":
        return cls.model_validate(price_bar)


class StockDetailQuoteSnapshotResponse(SQLModel):
    last_price: Decimal
    change_amount: Decimal
    change_percent: Decimal
    snapshot_time: UTCDateTime

    @classmethod
    def from_model(cls, quote_snapshot: QuoteSnapshot) -> "StockDetailQuoteSnapshotResponse":
        return cls.model_validate(quote_snapshot)


class StockDetailAnnouncementResponse(SQLModel):
    title: str
    source: str | None = None
    url: str | None = None
    summary: str | None = None
    published_at: datetime

    @classmethod
    def from_model(cls, announcement: Announcement) -> "StockDetailAnnouncementResponse":
        return cls.model_validate(announcement)


class StockDetailNewsItemResponse(SQLModel):
    title: str
    source: str | None = None
    url: str | None = None
    summary: str | None = None
    published_at: datetime

    @classmethod
    def from_model(cls, news_item: NewsItem) -> "StockDetailNewsItemResponse":
        return cls.model_validate(news_item)


class StockDetailPriceHistoryResponse(SQLModel):
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    amount: Decimal

    @classmethod
    def from_model(cls, price_history: PriceHistory) -> "StockDetailPriceHistoryResponse":
        return cls.model_validate(price_history)


class StockDetailFinancialMetricsResponse(SQLModel):
    report_period: str
    revenue: Decimal | None = None
    net_profit: Decimal | None = None
    eps: Decimal | None = None
    roe: Decimal | None = None
    debt_to_asset_ratio: Decimal | None = None

    @classmethod
    def from_model(cls, financial_metrics: FinancialMetrics) -> "StockDetailFinancialMetricsResponse":
        return cls.model_validate(financial_metrics)


class StockDetailCompanyProfileResponse(SQLModel):
    full_name: str | None = None
    english_name: str | None = None
    registered_capital: Decimal | None = None
    establishment_date: date | None = None
    website: str | None = None
    main_business: str | None = None
    employees: int | None = None

    @classmethod
    def from_model(cls, company_profile: CompanyProfile) -> "StockDetailCompanyProfileResponse":
        return cls.model_validate(company_profile)


class StockDetailResponse(SQLModel):
    security: StockDetailSecurityResponse
    price_context: list[StockDetailQuoteSnapshotResponse]
    announcements: list[StockDetailAnnouncementResponse]
    news: list[StockDetailNewsItemResponse]
    price_history: list[StockDetailPriceHistoryResponse]
    financial_metrics: list[StockDetailFinancialMetricsResponse]
    company_profile: StockDetailCompanyProfileResponse | None = None

    @classmethod
    def from_repository_model(cls, detail: StockDetail) -> "StockDetailResponse":
        return cls(
            security=StockDetailSecurityResponse.from_repository_model(detail.security),
            price_context=[
                StockDetailQuoteSnapshotResponse.from_model(quote_snapshot) for quote_snapshot in detail.price_context
            ],
            announcements=[
                StockDetailAnnouncementResponse.from_model(announcement)
                for announcement in detail.announcements
            ],
            news=[StockDetailNewsItemResponse.from_model(news_item) for news_item in detail.news],
            price_history=[
                StockDetailPriceHistoryResponse.from_model(price_history)
                for price_history in detail.price_history
            ],
            financial_metrics=[
                StockDetailFinancialMetricsResponse.from_model(financial_metrics)
                for financial_metrics in detail.financial_metrics
            ],
            company_profile=(
                StockDetailCompanyProfileResponse.from_model(detail.company_profile)
                if detail.company_profile is not None
                else None
            ),
        )


class StockSyncResponse(SQLModel):
    security_id: int
    synced: bool
    announcements_upserted: int
    news_items_upserted: int
    price_bars_upserted: int = 0
    financial_metrics_upserted: int = 0
    quote_snapshot_updated: bool = False
    company_profile_updated: bool = False
    warnings: list[str]
    synced_at: UTCDateTime

    @classmethod
    def from_service_result(
        cls,
        security_id: int,
        *,
        synced: bool,
        announcements_upserted: int,
        news_items_upserted: int,
        price_bars_upserted: int = 0,
        financial_metrics_upserted: int = 0,
        quote_snapshot_updated: bool = False,
        company_profile_updated: bool = False,
        warnings: list[str],
        synced_at: datetime,
    ) -> "StockSyncResponse":
        return cls(
            security_id=security_id,
            synced=synced,
            announcements_upserted=announcements_upserted,
            news_items_upserted=news_items_upserted,
            price_bars_upserted=price_bars_upserted,
            financial_metrics_upserted=financial_metrics_upserted,
            quote_snapshot_updated=quote_snapshot_updated,
            company_profile_updated=company_profile_updated,
            warnings=warnings,
            synced_at=synced_at,
        )
