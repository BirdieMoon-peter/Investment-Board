from collections.abc import Sequence

from sqlalchemy import tuple_
from sqlmodel import Session, select

from app.db.models import NewsItem


class NewsRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(self, items: Sequence[NewsItem], *, commit: bool = True) -> list[NewsItem]:
        if not items:
            return []

        latest_by_key: dict[tuple[int, object, str], NewsItem] = {}
        for item in items:
            latest_by_key[(item.security_id, item.published_at, item.title)] = item

        existing_rows = self.session.exec(
            select(NewsItem).where(
                tuple_(NewsItem.security_id, NewsItem.published_at, NewsItem.title).in_(
                    list(latest_by_key)
                )
            )
        ).all()
        existing_by_key = {(row.security_id, row.published_at, row.title): row for row in existing_rows}

        persisted: list[NewsItem] = []
        for key, item in latest_by_key.items():
            existing = existing_by_key.get(key)
            if existing is None:
                new_row = NewsItem(
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
            select(NewsItem.published_at)
            .where(NewsItem.security_id == security_id)
            .order_by(NewsItem.published_at.desc(), NewsItem.id.desc())
            .limit(1)
        )
        return self.session.exec(statement).first()

    def list_recent_by_security_id(self, security_id: int, limit: int = 20) -> list[NewsItem]:
        if limit <= 0:
            return []

        statement = (
            select(NewsItem)
            .where(NewsItem.security_id == security_id)
            .order_by(NewsItem.published_at.desc(), NewsItem.id.desc())
            .limit(limit)
        )
        return self.session.exec(statement).all()
