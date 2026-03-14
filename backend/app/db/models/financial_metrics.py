from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class FinancialMetrics(SQLModel, table=True):
    __tablename__ = "financial_metrics"
    __table_args__ = (
        UniqueConstraint(
            "security_id",
            "report_period",
            name="uq_financial_metrics_security_id_report_period",
        ),
        Index(
            "ix_financial_metrics_security_id_report_period",
            "security_id",
            "report_period",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    report_period: str = Field(sa_column=Column(String, nullable=False, index=True))
    revenue: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(20, 4), nullable=True))
    net_profit: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(20, 4), nullable=True))
    eps: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 4), nullable=True))
    roe: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(9, 6), nullable=True))
    debt_to_asset_ratio: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(9, 6), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
