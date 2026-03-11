from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class Security(SQLModel, table=True):
    __tablename__ = "securities"
    __table_args__ = (UniqueConstraint("market", "code", name="uq_securities_market_code"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    market: str = Field(sa_column=Column(String, nullable=False, index=True))
    code: str = Field(sa_column=Column(String, nullable=False, index=True))
    name: str = Field(sa_column=Column(String, nullable=False, index=True))
    industry: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    status: str = Field(
        default="active",
        sa_column=Column(String, nullable=False, default="active", index=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )
