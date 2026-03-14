from datetime import datetime
from decimal import Decimal

from pydantic import field_validator
from sqlmodel import SQLModel

from app.schemas.security import SecuritySearchResult


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
    snapshot_time: datetime | None


class WatchlistRemoveResponse(SQLModel):
    removed: bool
    security_id: int
