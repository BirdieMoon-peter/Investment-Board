from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import tuple_
from sqlmodel import Session, select

from app.db.models import NewsItem


class NewsRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_many(self, items: Sequence[NewsItem], *, commit: bool = True) -> list[NewsItem]:
        if not items:
            return []

        latest_by_key: dict[tuple[int, datetime, str], NewsItem] = {}
        for item in items:
            latest_by_key[_news_key(item.security_id, item.published_at, item.title)] = item

        existing_rows = self.session.exec(
            select(NewsItem).where(
                tuple_(NewsItem.security_id, NewsItem.published_at, NewsItem.title).in_(
                    [
                        (security_id, published_at, title)
                        for security_id, published_at, title in latest_by_key
                    ]
                )
            )
        ).all()
        existing_by_key = {
            _news_key(row.security_id, row.published_at, row.title): row for row in existing_rows
        }

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
                    published_at=_normalize_datetime_utc(item.published_at),
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
            for row in persisted:
                self.session.refresh(row)
        else:
            self.session.flush()

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


def _normalize_datetime_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _news_key(security_id: int, published_at: datetime, title: str) -> tuple[int, datetime, str]:
    return (security_id, _normalize_datetime_utc(published_at), title)
