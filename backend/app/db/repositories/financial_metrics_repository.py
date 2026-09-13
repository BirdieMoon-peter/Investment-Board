from collections.abc import Sequence

from sqlalchemy import tuple_
from sqlmodel import Session, select

from app.db.models import FinancialMetrics


class FinancialMetricsRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(
        self, items: Sequence[FinancialMetrics], *, commit: bool = True
    ) -> list[FinancialMetrics]:
        if not items:
            return []

        latest_by_key = {
            (item.security_id, item.report_period): item
            for item in items
        }

        existing_rows = self.session.exec(
            select(FinancialMetrics).where(
                tuple_(FinancialMetrics.security_id, FinancialMetrics.report_period).in_(
                    list(latest_by_key)
                )
            )
        ).all()
        existing_by_key = {
            (row.security_id, row.report_period): row for row in existing_rows
        }

        persisted: list[FinancialMetrics] = []
        for key, item in latest_by_key.items():
            existing = existing_by_key.get(key)
            if existing is None:
                new_row = FinancialMetrics(
                    security_id=item.security_id,
                    report_period=item.report_period,
                    revenue=item.revenue,
                    net_profit=item.net_profit,
                    eps=item.eps,
                    roe=item.roe,
                    debt_to_asset_ratio=item.debt_to_asset_ratio,
                )
                self.session.add(new_row)
                self.session.flush()
                existing_by_key[key] = new_row
                persisted.append(new_row)
                continue

            existing.revenue = item.revenue
            existing.net_profit = item.net_profit
            existing.eps = item.eps
            existing.roe = item.roe
            existing.debt_to_asset_ratio = item.debt_to_asset_ratio
            persisted.append(existing)

        if commit:
            self.session.commit()
            for row in persisted:
                self.session.refresh(row)
        else:
            self.session.flush()

        return persisted

    def list_recent_by_security_id(
        self, security_id: int, limit: int = 8
    ) -> list[FinancialMetrics]:
        if limit <= 0:
            return []

        statement = (
            select(FinancialMetrics)
            .where(FinancialMetrics.security_id == security_id)
            .order_by(FinancialMetrics.report_period.desc(), FinancialMetrics.id.desc())
            .limit(limit)
        )
        return self.session.exec(statement).all()
