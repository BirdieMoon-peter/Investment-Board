from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class CompanyProfile(SQLModel, table=True):
    __tablename__ = "company_profiles"
    __table_args__ = (UniqueConstraint("security_id", name="uq_company_profiles_security_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    full_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    english_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    registered_capital: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(20, 4), nullable=True),
    )
    establishment_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )
    website: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    main_business: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    employees: Optional[int] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
