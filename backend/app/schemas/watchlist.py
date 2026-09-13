from decimal import Decimal

from pydantic import field_validator
from sqlmodel import SQLModel

from app.schemas.security import SecuritySearchResult
from app.schemas.timestamps import UTCDateTime


class WatchlistAddRequest(SQLModel):
    security_id: int


class WatchlistCustomAddRequest(SQLModel):
    market: str
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code must not be blank")
        return value


class WatchlistItemResponse(SQLModel):
    security_id: int


class WatchlistCustomAddResponse(SQLModel):
    security_id: int
    security: SecuritySearchResult


class WatchlistListRow(SQLModel):
    security_id: int
    market: str
    code: str
    name: str
    industry: str | None
    last_price: Decimal | None
    change_percent: Decimal | None
    snapshot_time: UTCDateTime | None


class WatchlistRemoveResponse(SQLModel):
    removed: bool
    security_id: int


class WatchlistSyncResponse(SQLModel):
    security_ids: list[int]
    synced_count: int
    announcements_upserted: int
    news_items_upserted: int
    price_bars_upserted: int = 0
    financial_metrics_upserted: int = 0
    quote_snapshots_updated: int = 0
    company_profiles_updated: int = 0
    warnings: list[str]
    synced_at: UTCDateTime
