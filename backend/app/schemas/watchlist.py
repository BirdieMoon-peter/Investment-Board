from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel


class WatchlistAddRequest(SQLModel):
    security_id: int


class WatchlistItemResponse(SQLModel):
    security_id: int


class WatchlistListRow(SQLModel):
    security_id: int
    code: str
    name: str
    industry: str | None
    last_price: Decimal | None
    change_percent: Decimal | None
    snapshot_time: datetime | None


class WatchlistRemoveResponse(SQLModel):
    removed: bool
    security_id: int
