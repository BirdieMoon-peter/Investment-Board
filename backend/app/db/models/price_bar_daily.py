from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Numeric
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class PriceBarDaily(SQLModel, table=True):
    __tablename__ = "price_bar_daily"
    __table_args__ = (
        Index("ix_price_bar_daily_security_id_trade_date", "security_id", "trade_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    trade_date: date = Field(sa_column=Column(Date, nullable=False, index=True))
    open_price: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    high_price: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    low_price: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    close_price: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    volume: Decimal = Field(sa_column=Column(Numeric(20, 4), nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
