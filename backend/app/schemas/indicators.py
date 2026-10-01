"""Reproducible numerical results; decimal values serialize as lossless text."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class IndicatorResult(BaseModel):
    key: str
    label: str
    value: Decimal | None = None
    status: Literal['ready', 'unavailable'] = 'unavailable'
    formula: str
    formula_version: str = '1'
    window: str
    unit: str
    as_of: date | str | None = None
    sample_count: int = 0
    price_basis: str = 'unknown'
    input_refs: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SecurityIndicatorsResponse(BaseModel):
    security_id: int
    instrument_type: str
    metrics: list[IndicatorResult]
    data_context: dict[str, Any]


class PositionIndicators(BaseModel):
    holding_id: int
    security_id: int
    quantity: Decimal
    average_cost: Decimal
    valuation_at: datetime | None
    metrics: list[IndicatorResult]
    warnings: list[str]


class HoldingsIndicatorsResponse(BaseModel):
    positions: list[PositionIndicators]
    missing_price_security_ids: list[int]
    valuation_complete: bool
    denominator: Literal['known_valued_positions_only'] = 'known_valued_positions_only'
    metrics: list[IndicatorResult]
    warnings: list[str]
