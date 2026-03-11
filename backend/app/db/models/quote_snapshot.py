from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class QuoteSnapshot(SQLModel, table=True):
    __tablename__ = "quote_snapshots"
    __table_args__ = (
        Index("ix_quote_snapshots_security_id_snapshot_time", "security_id", "snapshot_time"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    last_price: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    change_amount: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    change_percent: Decimal = Field(sa_column=Column(Numeric(9, 4), nullable=False))
    snapshot_time: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
