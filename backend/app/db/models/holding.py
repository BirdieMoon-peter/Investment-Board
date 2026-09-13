from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class Holding(SQLModel, table=True):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("security_id", name="uq_holdings_security_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    quantity: Decimal = Field(sa_column=Column(Numeric(20, 4), nullable=False))
    average_cost: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    notes: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    target_horizon: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )
