from sqlmodel import Session, select

from app.db.models import WatchlistItem


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
