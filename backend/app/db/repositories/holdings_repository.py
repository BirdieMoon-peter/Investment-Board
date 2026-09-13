from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.db.models import Holding, InvestmentAdviceCache, Security, utc_now


@dataclass(frozen=True)
class HoldingRow:
    holding_id: int
    security_id: int
    market: str
    code: str
    name: str
    industry: str | None
    status: str
    quantity: Decimal
    average_cost: Decimal
    notes: str | None
    target_horizon: str | None
    created_at: datetime
    updated_at: datetime


class HoldingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, holding_id: int) -> Holding | None:
        return self.session.get(Holding, holding_id)

    def get_by_security_id(self, security_id: int) -> Holding | None:
        statement = select(Holding).where(Holding.security_id == security_id)
        return self.session.exec(statement).first()

    def get_row_by_id(self, holding_id: int) -> HoldingRow | None:
        statement = (
            select(Holding, Security)
            .join(Security, Security.id == Holding.security_id)
            .where(Holding.id == holding_id)
        )
        result = self.session.exec(statement).first()
        if result is None:
            return None

        holding, security = result
        return _to_row(holding, security)

    def get_row_by_security_id(self, security_id: int) -> HoldingRow | None:
        statement = (
            select(Holding, Security)
            .join(Security, Security.id == Holding.security_id)
            .where(Holding.security_id == security_id)
        )
        result = self.session.exec(statement).first()
        if result is None:
            return None

        holding, security = result
        return _to_row(holding, security)

    def list_rows(self) -> list[HoldingRow]:
        statement = (
            select(Holding, Security)
            .join(Security, Security.id == Holding.security_id)
            .order_by(Holding.updated_at.desc(), Holding.id.desc())
        )
        return [_to_row(holding, security) for holding, security in self.session.exec(statement).all()]

    def upsert_by_security_id(
        self,
        *,
        security_id: int,
        quantity: Decimal,
        average_cost: Decimal,
        notes: str | None,
        target_horizon: str | None,
    ) -> Holding:
        existing = self.get_by_security_id(security_id)
        if existing is None:
            holding = Holding(
                security_id=security_id,
                quantity=quantity,
                average_cost=average_cost,
                notes=notes,
                target_horizon=target_horizon,
            )
            self.session.add(holding)
        else:
            existing.quantity = quantity
            existing.average_cost = average_cost
            existing.notes = notes
            existing.target_horizon = target_horizon
            existing.updated_at = utc_now()
            holding = existing

        self.session.commit()
        self.session.refresh(holding)
        return holding

    def update_by_id(
        self,
        holding_id: int,
        *,
        quantity: Decimal,
        average_cost: Decimal,
        notes: str | None,
        target_horizon: str | None,
    ) -> Holding | None:
        holding = self.get_by_id(holding_id)
        if holding is None:
            return None

        holding.quantity = quantity
        holding.average_cost = average_cost
        holding.notes = notes
        holding.target_horizon = target_horizon
        holding.updated_at = utc_now()
        self.session.commit()
        self.session.refresh(holding)
        return holding

    def remove_by_id(self, holding_id: int) -> bool:
        holding = self.get_by_id(holding_id)
        if holding is None:
            return False

        try:
            # Retain the analysis snapshot while removing its live holding link.
            self.session.execute(
                update(InvestmentAdviceCache)
                .where(InvestmentAdviceCache.holding_id == holding_id)
                .values(holding_id=None)
            )
            self.session.delete(holding)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return True



def _to_row(holding: Holding, security: Security) -> HoldingRow:
    return HoldingRow(
        holding_id=holding.id,
        security_id=security.id,
        market=security.market,
        code=security.code,
        name=security.name,
        industry=security.industry,
        status=security.status,
        quantity=holding.quantity,
        average_cost=holding.average_cost,
        notes=holding.notes,
        target_horizon=holding.target_horizon,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
    )
