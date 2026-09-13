from datetime import UTC, datetime

from app.db.models import NewsItem
from app.db.repositories.news_repository import NewsRepository



def test_list_recent_by_security_id_returns_descending_published_at(session, seeded_security):
    session.add(
        NewsItem(
            security_id=seeded_security.id,
            title="Mid-market coverage",
            source="Newswire",
            url="https://example.com/mid",
            summary="Mid summary",
            published_at=datetime(2026, 3, 9, 14, 0),
        )
    )
    session.add(
        NewsItem(
            security_id=seeded_security.id,
            title="Latest market coverage",
            source="Newswire",
            url="https://example.com/latest",
            summary="Latest summary",
            published_at=datetime(2026, 3, 10, 14, 0),
        )
    )
    session.add(
        NewsItem(
            security_id=seeded_security.id,
            title="Older market coverage",
            source="Newswire",
            url="https://example.com/older",
            summary="Older summary",
            published_at=datetime(2026, 3, 8, 14, 0),
        )
    )
    session.commit()

    repository = NewsRepository(session)

    rows = repository.list_recent_by_security_id(seeded_security.id, limit=2)

    assert [row.title for row in rows] == ["Latest market coverage", "Mid-market coverage"]
    assert [row.published_at for row in rows] == [
        datetime(2026, 3, 10, 14, 0),
        datetime(2026, 3, 9, 14, 0),
    ]



def test_upsert_many_matches_existing_rows_with_timezone_normalization(session, seeded_security):
    repository = NewsRepository(session)
    original = NewsItem(
        security_id=seeded_security.id,
        title="Duplicate-safe news",
        source="Newswire",
        url="https://example.com/original",
        summary="Original summary",
        published_at=datetime(2026, 3, 10, 14, 0),
    )
    session.add(original)
    session.commit()

    persisted = repository.upsert_many(
        [
            NewsItem(
                security_id=seeded_security.id,
                title="Duplicate-safe news",
                source="Eastmoney",
                url="https://example.com/updated",
                summary="Updated summary",
                published_at=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
            )
        ]
    )

    assert len(persisted) == 1
    assert persisted[0].id == original.id
    assert persisted[0].source == "Eastmoney"
    assert persisted[0].url == "https://example.com/updated"
    assert persisted[0].summary == "Updated summary"
    rows = repository.list_recent_by_security_id(seeded_security.id, limit=10)
    assert [row.title for row in rows].count("Duplicate-safe news") == 1
