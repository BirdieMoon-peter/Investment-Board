from decimal import Decimal

from pydantic import field_validator
from sqlmodel import SQLModel

from app.schemas.security import SecuritySearchResult


class HoldingUpsertRequest(SQLModel):
    security_id: int
    quantity: Decimal
    average_cost: Decimal
    notes: str | None = None
    target_horizon: str | None = None

    @field_validator("quantity", "average_cost")
    @classmethod
    def validate_positive_decimal(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("must be greater than 0")
        return value

    @field_validator("notes", "target_horizon")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class HoldingResponse(SQLModel):
    holding_id: int
    security_id: int
    security: SecuritySearchResult
    quantity: Decimal
    average_cost: Decimal
    notes: str | None = None
    target_horizon: str | None = None


class HoldingRemoveResponse(SQLModel):
    removed: bool
    holding_id: int
