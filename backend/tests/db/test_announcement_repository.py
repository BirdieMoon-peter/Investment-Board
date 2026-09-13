from datetime import UTC, datetime

from app.db.models import Announcement
from app.db.repositories.announcement_repository import AnnouncementRepository



def test_list_recent_by_security_id_returns_descending_published_at(session, seeded_security):
    session.add(
        Announcement(
            security_id=seeded_security.id,
            title="Middle disclosure",
            source="Exchange",
            url="https://example.com/middle",
            summary="Middle summary",
            published_at=datetime(2026, 3, 9, 9, 0),
        )
    )
    session.add(
        Announcement(
            security_id=seeded_security.id,
            title="Latest disclosure",
            source="Exchange",
            url="https://example.com/latest",
            summary="Latest summary",
            published_at=datetime(2026, 3, 10, 9, 0),
        )
    )
    session.add(
        Announcement(
            security_id=seeded_security.id,
            title="Older disclosure",
            source="Exchange",
            url="https://example.com/older",
            summary="Older summary",
            published_at=datetime(2026, 3, 8, 9, 0),
        )
    )
    session.commit()

    repository = AnnouncementRepository(session)

    rows = repository.list_recent_by_security_id(seeded_security.id, limit=2)

    assert [row.title for row in rows] == ["Latest disclosure", "Middle disclosure"]
    assert [row.published_at for row in rows] == [
        datetime(2026, 3, 10, 9, 0),
        datetime(2026, 3, 9, 9, 0),
    ]



def test_upsert_many_matches_existing_rows_with_timezone_normalization(session, seeded_security):
    repository = AnnouncementRepository(session)
    original = Announcement(
        security_id=seeded_security.id,
        title="Duplicate-safe disclosure",
        source="Exchange",
        url="https://example.com/original",
        summary="Original summary",
        published_at=datetime(2026, 3, 10, 9, 0),
    )
    session.add(original)
    session.commit()

    persisted = repository.upsert_many(
        [
            Announcement(
                security_id=seeded_security.id,
                title="Duplicate-safe disclosure",
                source="Sina",
                url="https://example.com/updated",
                summary="Updated summary",
                published_at=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
            )
        ]
    )

    assert len(persisted) == 1
    assert persisted[0].id == original.id
    assert persisted[0].source == "Sina"
    assert persisted[0].url == "https://example.com/updated"
    assert persisted[0].summary == "Updated summary"
    rows = repository.list_recent_by_security_id(seeded_security.id, limit=10)
    assert [row.title for row in rows].count("Duplicate-safe disclosure") == 1



def test_upsert_many_deduplicates_same_batch_with_mixed_timezone_inputs(session, seeded_security):
    repository = AnnouncementRepository(session)

    persisted = repository.upsert_many(
        [
            Announcement(
                security_id=seeded_security.id,
                title="Board resolution",
                source="Exchange",
                url="https://example.com/original",
                summary="Original summary",
                published_at=datetime(2026, 3, 12, 0, 0),
            ),
            Announcement(
                security_id=seeded_security.id,
                title="Board resolution",
                source="Sina",
                url="https://example.com/updated",
                summary="Updated summary",
                published_at=datetime(2026, 3, 12, 0, 0, tzinfo=UTC),
            ),
        ]
    )

    assert len(persisted) == 1
    rows = repository.list_recent_by_security_id(seeded_security.id, limit=10)
    assert len(rows) == 1
    assert rows[0].source == "Sina"
    assert rows[0].url == "https://example.com/updated"
    assert rows[0].summary == "Updated summary"
