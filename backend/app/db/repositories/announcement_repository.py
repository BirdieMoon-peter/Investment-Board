from collections.abc import Sequence

from sqlalchemy import tuple_
from sqlmodel import Session, select

from app.db.models import Announcement


class AnnouncementRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(
        self, items: Sequence[Announcement], *, commit: bool = True
    ) -> list[Announcement]:
        if not items:
            return []

        latest_by_key: dict[tuple[int, object, str], Announcement] = {}
        for item in items:
            latest_by_key[(item.security_id, item.published_at, item.title)] = item

        existing_rows = self.session.exec(
            select(Announcement).where(
                tuple_(Announcement.security_id, Announcement.published_at, Announcement.title).in_(
                    list(latest_by_key)
                )
            )
        ).all()
        existing_by_key = {
            (row.security_id, row.published_at, row.title): row for row in existing_rows
        }

        persisted: list[Announcement] = []
        for key, item in latest_by_key.items():
            existing = existing_by_key.get(key)
            if existing is None:
                new_row = Announcement(
                    security_id=item.security_id,
                    title=item.title,
                    source=item.source,
                    url=item.url,
                    summary=item.summary,
                    published_at=item.published_at,
                )
                self.session.add(new_row)
                self.session.flush()
                existing_by_key[key] = new_row
                persisted.append(new_row)
                continue

            existing.source = item.source
            existing.url = item.url
            existing.summary = item.summary
            persisted.append(existing)

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        for row in persisted:
            self.session.refresh(row)
        return persisted

    def get_latest_published_at(self, security_id: int):
        statement = (
            select(Announcement.published_at)
            .where(Announcement.security_id == security_id)
            .order_by(Announcement.published_at.desc(), Announcement.id.desc())
            .limit(1)
        )
        return self.session.exec(statement).first()

    def list_recent_by_security_id(self, security_id: int, limit: int = 20) -> list[Announcement]:
        if limit <= 0:
            return []

        statement = (
            select(Announcement)
            .where(Announcement.security_id == security_id)
            .order_by(Announcement.published_at.desc(), Announcement.id.desc())
            .limit(limit)
        )
        return self.session.exec(statement).all()
