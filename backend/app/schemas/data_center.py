"""Strict controls for managed security acquisition and the manual overlay."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal['announcements', 'news', 'price_history', 'quote_snapshot', 'financial_metrics', 'company_profile', 'fund_nav', 'fund_profile']
InstrumentType = Literal['unknown', 'stock', 'etf', 'lof', 'index']


class SecuritySyncRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    categories: list[Category] | None = Field(default=None, min_length=1, max_length=8)
    price_source: Literal['eastmoney', 'sina', 'netease'] | None = None

    @model_validator(mode='after')
    def validate_source(self):
        if self.price_source is not None and (self.categories is None or 'price_history' not in self.categories):
            raise ValueError('price_source requires explicit price_history category')
        if self.categories is not None and len(set(self.categories)) != len(self.categories):
            raise ValueError('duplicate category')
        return self


class SecurityMetadataUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    instrument_type: InstrumentType | None = None
    benchmark_code: str | None = Field(default=None, pattern=r'^(SH|SZ):[0-9]{6}$')
    benchmark_name: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def validate_type(self):
        if 'instrument_type' in self.model_fields_set and self.instrument_type is None:
            raise ValueError('instrument_type must be an explicit type, including unknown')
        if not self.model_fields_set:
            raise ValueError('empty metadata update')
        return self

# Response models make the data-center contract visible in OpenAPI. Provider
# decimals are deliberately text, including nested NAV/fee/asset fields.
from datetime import date, datetime


class AcquisitionAttempt(BaseModel):
    id: int
    provider_key: str
    security_id: int
    category: str
    status: str
    state: str
    started_at: datetime
    finished_at: datetime | None
    records_received: int
    records_written: int
    records_rejected: int
    error_code: str | None
    persisted_coverage: str
    write_attribution: str


class QualityIssue(BaseModel):
    id: int
    run_id: int | None
    code: str
    severity: str
    message: str
    created_at: datetime
    resolved_at: datetime | None


class DatasetHealth(BaseModel):
    health: Literal['healthy','stale','partial','failed','unknown','not_applicable']
    source_key: str | None
    unit: str | None
    frequency: str | None
    price_basis: str
    observation_at: datetime | None
    observation_precision: Literal['unknown','date','datetime']
    observation_time_note: str
    fetched_at: datetime | None
    coverage_start: date | None
    coverage_end: date | None
    recent_attempts: list[AcquisitionAttempt]
    unresolved_issues: list[QualityIssue]
    latest_attempt: AcquisitionAttempt | None
    freshness: str
    coverage: str
    context_disclosures: list[str]
    unit_provenance: str
    freshness_threshold_days: int | None
    freshness_basis: str
    valuation_basis: str | None = None
    received_count_unit: str | None = None
    written_count_unit: str | None = None
    publication_at: datetime | None = None


class SecurityIdentity(BaseModel):
    id: int
    code: str
    market: str
    name: str
    industry: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class SecurityMetadata(BaseModel):
    instrument_type: InstrumentType
    effective_instrument_type: InstrumentType
    classification_origin: str
    benchmark_code: str | None
    benchmark_name: str | None
    manager: str | None
    management_fee: str | None
    custody_fee: str | None
    fund_assets: str | None
    assets_as_of: date | None
    source_id: int | None
    source_key: str | None
    as_of: date | None
    overlay_scope: list[str]
    provider_fields_source: str | None
    publication_at: datetime | None
    provenance_note: str


class NavObservation(BaseModel):
    nav_date: date
    nav_kind: Literal['unit_nav','cumulative_nav','iopv']
    value: str
    fetched_at: datetime
    published_at: datetime | None
    source_key: str


class CalendarDisclosure(BaseModel):
    verified: bool
    note: str


class SecurityDataResponse(BaseModel):
    security: SecurityIdentity
    metadata: SecurityMetadata
    categories: dict[Category, DatasetHealth]
    nav_observations: list[NavObservation]
    nav_limit: int
    calendar: CalendarDisclosure


class CategorySyncOutcome(BaseModel):
    outcome: Literal['succeeded','partial','empty','skipped','failed_fetch','failed_persist','disabled','not_applicable','unavailable']
    reason: str | None = None
    received: int | None = None
    written: int | None = None
    received_count_unit: str | None = None
    written_count_unit: str | None = None
    resolved_instrument_type: InstrumentType | None = None


class SecuritySyncResponse(BaseModel):
    security_id: int
    category_outcomes: dict[Category, CategorySyncOutcome]
    warnings: list[str]
    data: SecurityDataResponse
