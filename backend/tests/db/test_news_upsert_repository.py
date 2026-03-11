from datetime import datetime

from sqlmodel import select

from app.db.models import NewsItem
from app.db.repositories.news_repository import NewsRepository



def test_upsert_many_inserts_new_news_items(session, seeded_security):
    repository = NewsRepository(session)

    persisted = repository.upsert_many(
        [
            NewsItem(
                security_id=seeded_security.id,
                title="Opening bell coverage",
                source="Newswire",
                url="https://example.com/news/1",
                summary="Opening bell summary",
                published_at=datetime(2026, 3, 10, 9, 30),
            ),
            NewsItem(
                security_id=seeded_security.id,
                title="Closing bell coverage",
                source="Newswire",
                url="https://example.com/news/2",
                summary="Closing bell summary",
                published_at=datetime(2026, 3, 10, 15, 0),
            ),
        ]
    )

    rows = session.exec(select(NewsItem).order_by(NewsItem.published_at)).all()

    assert [row.id for row in persisted] == [rows[0].id, rows[1].id]
    assert [(row.title, row.url) for row in rows] == [
        ("Opening bell coverage", "https://example.com/news/1"),
        ("Closing bell coverage", "https://example.com/news/2"),
    ]



def test_upsert_many_updates_existing_news_item_without_creating_duplicate(session, seeded_security):
    existing = NewsItem(
        security_id=seeded_security.id,
        title="Broker note roundup",
        source="Newswire",
        url="https://example.com/news/original",
        summary="Original summary",
        published_at=datetime(2026, 3, 10, 12, 0),
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    repository = NewsRepository(session)

    persisted = repository.upsert_many(
        [
            NewsItem(
                security_id=seeded_security.id,
                title="Broker note roundup",
                source="Desk update",
                url="https://example.com/news/updated",
                summary="Updated summary",
                published_at=datetime(2026, 3, 10, 12, 0),
            ),
            NewsItem(
                security_id=seeded_security.id,
                title="After-hours coverage",
                source="Newswire",
                url="https://example.com/news/new",
                summary="New summary",
                published_at=datetime(2026, 3, 10, 18, 0),
            ),
        ]
    )

    rows = session.exec(select(NewsItem).order_by(NewsItem.published_at, NewsItem.id)).all()

    assert len(rows) == 2
    assert rows[0].id == existing.id
    assert rows[0].source == "Desk update"
    assert rows[0].url == "https://example.com/news/updated"
    assert rows[0].summary == "Updated summary"
    assert rows[1].title == "After-hours coverage"
    assert {(row.title, row.id) for row in persisted} == {
        ("Broker note roundup", existing.id),
        ("After-hours coverage", rows[1].id),
    }
