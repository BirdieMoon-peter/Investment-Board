from datetime import date, datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.db.models import Announcement, NewsItem, PriceBarDaily
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


class StockDetailResponse(SQLModel):
    security: StockDetailSecurityResponse
    price_context: list[StockDetailPriceBarResponse]
    announcements: list[StockDetailAnnouncementResponse]
    news: list[StockDetailNewsItemResponse]

    @classmethod
    def from_repository_model(cls, detail: StockDetail) -> "StockDetailResponse":
        return cls(
            security=StockDetailSecurityResponse.from_repository_model(detail.security),
            price_context=[
                StockDetailPriceBarResponse.from_model(price_bar) for price_bar in detail.price_context
            ],
            announcements=[
                StockDetailAnnouncementResponse.from_model(announcement)
                for announcement in detail.announcements
            ],
            news=[StockDetailNewsItemResponse.from_model(news_item) for news_item in detail.news],
        )


class StockSyncResponse(SQLModel):
    security_id: int
    synced: bool
    announcements_upserted: int
    news_items_upserted: int
    warnings: list[str]
    synced_at: datetime

    @classmethod
    def from_service_result(
        cls,
        security_id: int,
        *,
        synced: bool,
        announcements_upserted: int,
        news_items_upserted: int,
        warnings: list[str],
        synced_at: datetime,
    ) -> "StockSyncResponse":
        return cls(
            security_id=security_id,
            synced=synced,
            announcements_upserted=announcements_upserted,
            news_items_upserted=news_items_upserted,
            warnings=warnings,
            synced_at=synced_at,
        )
