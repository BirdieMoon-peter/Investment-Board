"""Additive provenance and fund research tables; existing business schema is untouched."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class ExactDecimal(TypeDecorator):
    """Store decimal text to avoid SQLite NUMERIC's binary floating-point conversion."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("Decimal values must be finite")
        return format(number, "f")

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


class DataSource(SQLModel, table=True):
    __tablename__ = "data_sources"
    __table_args__ = (UniqueConstraint("source_key"),)

    id: int | None = Field(default=None, primary_key=True)
    source_key: str = Field(index=True)
    name: str
    access_mode: str = "unknown"
    enabled: bool = True
    url: str | None = None


class SecurityDataset(SQLModel, table=True):
    __tablename__ = "security_datasets"
    __table_args__ = (
        UniqueConstraint("security_id", "category"),
        CheckConstraint("price_basis IN ('unknown','unadjusted','forward_adjusted','backward_adjusted')"),
        CheckConstraint("coverage_start IS NULL OR coverage_end IS NULL OR coverage_start <= coverage_end"),
    )

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True)
    category: str
    source_id: int | None = Field(default=None, foreign_key="data_sources.id", index=True)
    unit: str | None = None
    frequency: str | None = None
    price_basis: str = "unknown"
    observation_at: datetime | None = None
    fetched_at: datetime | None = None
    coverage_start: date | None = None
    coverage_end: date | None = None


class IngestionRun(SQLModel, table=True):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending','running','succeeded','partial','failed')"),
        CheckConstraint("records_received >= 0 AND records_written >= 0 AND records_rejected >= 0"),
        UniqueConstraint("id", "dataset_id"),
        CheckConstraint("error_message IS NULL OR error_message IN ('ingestion_error','network_error','timeout','rate_limited','authentication_error','provider_unavailable','invalid_data')"),
    )

    id: int | None = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="security_datasets.id", index=True)
    source_id: int = Field(foreign_key="data_sources.id", index=True)
    status: str = "pending"
    started_at: datetime = Field(default_factory=utc_now, index=True)
    finished_at: datetime | None = None
    records_received: int = 0
    records_written: int = 0
    records_rejected: int = 0
    # Repository stores only allowlisted error codes, never provider text.
    error_message: str | None = None


class DataQualityIssue(SQLModel, table=True):
    __tablename__ = "data_quality_issues"
    __table_args__ = (
        CheckConstraint("severity IN ('info','warning','error')"),
        ForeignKeyConstraint(["run_id", "dataset_id"], ["ingestion_runs.id", "ingestion_runs.dataset_id"]),
    )

    id: int | None = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="security_datasets.id", index=True)
    run_id: int | None = Field(default=None, index=True)
    code: str
    severity: str
    message: str
    created_at: datetime = Field(default_factory=utc_now, index=True)
    resolved_at: datetime | None = None


class SecurityResearchMetadata(SQLModel, table=True):
    __tablename__ = "security_research_metadata"
    __table_args__ = (
        UniqueConstraint("security_id"),
        CheckConstraint("instrument_type IN ('unknown','stock','etf','lof','index')"),
        CheckConstraint("management_fee IS NULL OR CAST(management_fee AS REAL) BETWEEN 0 AND 1"),
        CheckConstraint("custody_fee IS NULL OR CAST(custody_fee AS REAL) BETWEEN 0 AND 1"),
        CheckConstraint("fund_assets IS NULL OR (fund_assets NOT LIKE '-%' AND REPLACE(REPLACE(fund_assets, '0', ''), '.', '') <> '')"),
    )

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True)
    instrument_type: str = "unknown"
    benchmark_code: str | None = None
    benchmark_name: str | None = None
    manager: str | None = None
    management_fee: Decimal | None = Field(default=None, sa_column=Column(ExactDecimal(), nullable=True))
    custody_fee: Decimal | None = Field(default=None, sa_column=Column(ExactDecimal(), nullable=True))
    fund_assets: Decimal | None = Field(default=None, sa_column=Column(ExactDecimal(), nullable=True))
    assets_as_of: date | None = None
    source_id: int | None = Field(default=None, foreign_key="data_sources.id", index=True)
    as_of: date | None = None


class FundNavObservation(SQLModel, table=True):
    __tablename__ = "fund_nav_observations"
    __table_args__ = (
        UniqueConstraint("security_id", "nav_date", "nav_kind", "source_id"),
        CheckConstraint("nav_kind IN ('unit_nav','cumulative_nav','iopv')"),
        # ExactDecimal binds canonical finite decimal text. Check sign/nonzero
        # without REAL conversion, which can underflow valid tiny decimals.
        CheckConstraint("value NOT LIKE '-%' AND REPLACE(REPLACE(value, '0', ''), '.', '') <> ''"),
    )

    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key="securities.id", index=True)
    nav_date: date = Field(index=True)
    nav_kind: str = "unit_nav"
    source_id: int = Field(foreign_key="data_sources.id", index=True)
    value: Decimal = Field(sa_column=Column(ExactDecimal(), nullable=False))
    fetched_at: datetime = Field(default_factory=utc_now)
    published_at: datetime | None = None
