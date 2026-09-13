from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.services.homepage_overview import HomepageMacroItem, HomepageOverview, HomepageOverviewWarning, MarketIndexSnapshot


class HomepageMarketIndexResponse(SQLModel):
    key: str
    name: str
    market: str | None = None
    last_value: Decimal | None = None
    change_amount: Decimal | None = None
    change_percent: Decimal | None = None
    snapshot_time: datetime | None = None

    @classmethod
    def from_service_model(cls, item: MarketIndexSnapshot) -> "HomepageMarketIndexResponse":
        return cls(
            key=item.key,
            name=item.name,
            market=item.market,
            last_value=item.last_value,
            change_amount=item.change_amount,
            change_percent=item.change_percent,
            snapshot_time=item.snapshot_time,
        )


class HomepageMacroItemResponse(SQLModel):
    key: str
    title: str
    category: str
    value: str | None = None
    unit: str | None = None
    change_text: str | None = None
    published_at: datetime | None = None
    importance: str
    summary: str | None = None

    @classmethod
    def from_service_model(cls, item: HomepageMacroItem) -> "HomepageMacroItemResponse":
        return cls(
            key=item.key,
            title=item.title,
            category=item.category,
            value=item.value,
            unit=item.unit,
            change_text=item.change_text,
            published_at=item.published_at,
            importance=item.importance,
            summary=item.summary,
        )


class HomepageOverviewWarningResponse(SQLModel):
    section: str
    message: str

    @classmethod
    def from_service_model(cls, warning: HomepageOverviewWarning) -> "HomepageOverviewWarningResponse":
        return cls(section=warning.section, message=warning.message)


class HomepageOverviewResponse(SQLModel):
    indexes: list[HomepageMarketIndexResponse]
    macro: list[HomepageMacroItemResponse]
    updated_at: datetime | None = None
    warnings: list[HomepageOverviewWarningResponse]

    @classmethod
    def from_service_model(cls, overview: HomepageOverview) -> "HomepageOverviewResponse":
        return cls(
            indexes=[HomepageMarketIndexResponse.from_service_model(item) for item in overview.indexes],
            macro=[HomepageMacroItemResponse.from_service_model(item) for item in overview.macro],
            updated_at=overview.updated_at,
            warnings=[HomepageOverviewWarningResponse.from_service_model(item) for item in overview.warnings],
        )
