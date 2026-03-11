from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class WatchlistItem(SQLModel, table=True):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("security_id", name="uq_watchlist_items_security_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
