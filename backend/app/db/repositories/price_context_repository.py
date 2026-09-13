from datetime import datetime

from sqlmodel import Session, select

from app.db.models import QuoteSnapshot


class PriceContextRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_recent_by_security_id(self, security_id: int, limit: int = 20) -> list[QuoteSnapshot]:
        if limit <= 0:
            return []

        statement = (
            select(QuoteSnapshot)
            .where(QuoteSnapshot.security_id == security_id)
            .where(QuoteSnapshot.snapshot_time > datetime(2000, 1, 1))
            .order_by(QuoteSnapshot.snapshot_time.desc(), QuoteSnapshot.id.desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())
