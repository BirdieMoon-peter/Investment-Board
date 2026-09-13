from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import tuple_
from sqlmodel import Session, select

from app.db.models import QuoteSnapshot


class QuoteSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(
        self, items: Sequence[QuoteSnapshot], *, commit: bool = True
    ) -> list[QuoteSnapshot]:
        if not items:
            return []

        latest_by_key = {
            (item.security_id, _utc_storage_time(item.snapshot_time)): item
            for item in items
        }

        existing_rows = self.session.exec(
            select(QuoteSnapshot).where(
                tuple_(QuoteSnapshot.security_id, QuoteSnapshot.snapshot_time).in_(
                    list(latest_by_key)
                )
            )
        ).all()
        existing_by_key = {
            (row.security_id, _utc_storage_time(row.snapshot_time)): row for row in existing_rows
        }

        persisted: list[QuoteSnapshot] = []
        for key, item in latest_by_key.items():
            existing = existing_by_key.get(key)
            if existing is None:
                new_row = QuoteSnapshot(
                    security_id=item.security_id,
                    last_price=item.last_price,
                    change_amount=item.change_amount,
                    change_percent=item.change_percent,
                    snapshot_time=key[1],
                )
                self.session.add(new_row)
                self.session.flush()
                existing_by_key[key] = new_row
                persisted.append(new_row)
                continue

            existing.last_price = item.last_price
            existing.change_amount = item.change_amount
            existing.change_percent = item.change_percent
            persisted.append(existing)

        if commit:
            self.session.commit()
            for row in persisted:
                self.session.refresh(row)
        else:
            self.session.flush()

        return persisted


def _utc_storage_time(value: datetime) -> datetime:
    # Match SQLite's naive UTC storage in both incoming and persisted keys.
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value
