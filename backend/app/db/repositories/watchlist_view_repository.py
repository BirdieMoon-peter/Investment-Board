from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models import QuoteSnapshot, Security, WatchlistItem


@dataclass(frozen=True)
class WatchlistRow:
    security_id: int
    market: str
    code: str
    name: str
    industry: Optional[str]
    last_price: Optional[Decimal]
    change_percent: Optional[Decimal]
    snapshot_time: Optional[datetime]


class WatchlistViewRepository:
    def __init__(self, session: Session):
        self.session = session

    def _latest_snapshot_subquery(self):
        watched_security_ids = select(WatchlistItem.security_id.label("security_id")).subquery()
        ranked_snapshots = (
            select(
                QuoteSnapshot.id.label("quote_snapshot_id"),
                QuoteSnapshot.security_id.label("security_id"),
                func.row_number()
                .over(
                    partition_by=QuoteSnapshot.security_id,
                    order_by=(QuoteSnapshot.snapshot_time.desc(), QuoteSnapshot.id.desc()),
                )
                .label("row_number"),
            )
            .join(watched_security_ids, watched_security_ids.c.security_id == QuoteSnapshot.security_id)
            .subquery()
        )

        return (
            select(
                ranked_snapshots.c.quote_snapshot_id,
                ranked_snapshots.c.security_id,
            )
            .where(ranked_snapshots.c.row_number == 1)
            .subquery()
        )

    def list_rows(self) -> list[WatchlistRow]:
        latest_snapshot = self._latest_snapshot_subquery()

        statement = (
            select(
                Security.id,
                Security.market,
                Security.code,
                Security.name,
                Security.industry,
                QuoteSnapshot.last_price,
                QuoteSnapshot.change_percent,
                QuoteSnapshot.snapshot_time,
            )
            .select_from(WatchlistItem)
            .join(Security, Security.id == WatchlistItem.security_id)
            .outerjoin(latest_snapshot, latest_snapshot.c.security_id == Security.id)
            .outerjoin(QuoteSnapshot, QuoteSnapshot.id == latest_snapshot.c.quote_snapshot_id)
            .order_by(Security.market, Security.code)
        )

        return [
            WatchlistRow(
                security_id=security_id,
                market=market,
                code=code,
                name=name,
                industry=industry,
                last_price=last_price,
                change_percent=change_percent,
                snapshot_time=snapshot_time,
            )
            for security_id, market, code, name, industry, last_price, change_percent, snapshot_time in self.session.exec(
                statement
            ).all()
        ]
