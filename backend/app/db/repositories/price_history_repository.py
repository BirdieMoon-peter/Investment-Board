from collections.abc import Sequence

from sqlalchemy import tuple_
from sqlmodel import Session, select

from app.db.models import PriceHistory


class PriceHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(
        self, items: Sequence[PriceHistory], *, commit: bool = True
    ) -> list[PriceHistory]:
        if not items:
            return []

        latest_by_key = {
            (item.security_id, item.trade_date): item
            for item in items
        }

        existing_rows = self.session.exec(
            select(PriceHistory).where(
                tuple_(PriceHistory.security_id, PriceHistory.trade_date).in_(
                    list(latest_by_key)
                )
            )
        ).all()
        existing_by_key = {
            (row.security_id, row.trade_date): row for row in existing_rows
        }

        persisted: list[PriceHistory] = []
        for key, item in latest_by_key.items():
            existing = existing_by_key.get(key)
            if existing is None:
                new_row = PriceHistory(
                    security_id=item.security_id,
                    trade_date=item.trade_date,
                    open_price=item.open_price,
                    high_price=item.high_price,
                    low_price=item.low_price,
                    close_price=item.close_price,
                    volume=item.volume,
                    amount=item.amount,
                )
                self.session.add(new_row)
                self.session.flush()
                existing_by_key[key] = new_row
                persisted.append(new_row)
                continue

            existing.open_price = item.open_price
            existing.high_price = item.high_price
            existing.low_price = item.low_price
            existing.close_price = item.close_price
            existing.volume = item.volume
            existing.amount = item.amount
            persisted.append(existing)

        if commit:
            self.session.commit()
            for row in persisted:
                self.session.refresh(row)
        else:
            self.session.flush()

        return persisted

    def list_recent_by_security_id(
        self, security_id: int, limit: int = 252
    ) -> list[PriceHistory]:
        if limit <= 0:
            return []

        statement = (
            select(PriceHistory)
            .where(PriceHistory.security_id == security_id)
            .order_by(PriceHistory.trade_date.desc(), PriceHistory.id.desc())
            .limit(limit)
        )
        return self.session.exec(statement).all()
