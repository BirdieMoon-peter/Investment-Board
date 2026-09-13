from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class InvestmentAdviceCache(SQLModel, table=True):
    __tablename__ = "investment_advice_cache"
    __table_args__ = (
        Index("ix_investment_advice_cache_generated_at", "generated_at"),
        Index(
            "ix_investment_advice_cache_target",
            "target_type",
            "target_id",
            "generated_at",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    target_type: str = Field(sa_column=Column(String, nullable=False, index=True))
    target_id: int = Field(nullable=False, index=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    holding_id: int | None = Field(
        default=None,
        sa_column=Column(ForeignKey("holdings.id"), nullable=True, index=True),
    )
    target_market: str = Field(sa_column=Column(String, nullable=False))
    target_code: str = Field(sa_column=Column(String, nullable=False))
    target_name: str = Field(sa_column=Column(String, nullable=False))
    recommendation: str = Field(sa_column=Column(String, nullable=False))
    confidence: str = Field(sa_column=Column(String, nullable=False))
    summary: str = Field(sa_column=Column(String, nullable=False))
    thesis_points_json: str = Field(sa_column=Column(String, nullable=False))
    risk_points_json: str = Field(sa_column=Column(String, nullable=False))
    position_notes_json: str = Field(sa_column=Column(String, nullable=False))
    recent_catalysts_json: str = Field(sa_column=Column(String, nullable=False))
    warnings_json: str = Field(sa_column=Column(String, nullable=False))
    full_analysis: str = Field(sa_column=Column(String, nullable=False))
    disclaimer: str = Field(sa_column=Column(String, nullable=False))
    generated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
