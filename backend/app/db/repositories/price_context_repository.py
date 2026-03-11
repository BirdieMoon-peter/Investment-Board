from sqlmodel import Session, select

from app.db.models import PriceBarDaily


class PriceContextRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_recent_by_security_id(self, security_id: int, limit: int = 20) -> list[PriceBarDaily]:
        if limit <= 0:
            return []

        statement = (
            select(PriceBarDaily)
            .where(PriceBarDaily.security_id == security_id)
            .order_by(PriceBarDaily.trade_date.desc(), PriceBarDaily.id.desc())
            .limit(limit)
        )
        return self.session.exec(statement).all()
