from dataclasses import dataclass

from sqlmodel import Session, select

from app.db.models import Security, WatchlistItem


@dataclass(frozen=True)
class WatchlistSecurityRow:
    security_id: int
    market: str
    code: str
    industry: str | None


class WatchlistRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, security_id: int) -> WatchlistItem:
        existing = self.session.exec(
            select(WatchlistItem).where(WatchlistItem.security_id == security_id)
        ).first()
        if existing is not None:
            return existing

        item = WatchlistItem(security_id=security_id)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def remove_by_security_id(self, security_id: int) -> bool:
        existing = self.session.exec(
            select(WatchlistItem).where(WatchlistItem.security_id == security_id)
        ).first()
        if existing is None:
            return False

        self.session.delete(existing)
        self.session.commit()
        return True

    def list_ids(self) -> list[int]:
        return list(
            self.session.exec(
                select(WatchlistItem.security_id).order_by(WatchlistItem.created_at, WatchlistItem.id)
            ).all()
        )

    def list_security_rows(self) -> list[WatchlistSecurityRow]:
        statement = (
            select(Security.id, Security.market, Security.code, Security.industry)
            .select_from(WatchlistItem)
            .join(Security, Security.id == WatchlistItem.security_id)
            .order_by(WatchlistItem.created_at, WatchlistItem.id)
        )
        return [
            WatchlistSecurityRow(
                security_id=security_id,
                market=market,
                code=code,
                industry=industry,
            )
            for security_id, market, code, industry in self.session.exec(statement).all()
        ]
