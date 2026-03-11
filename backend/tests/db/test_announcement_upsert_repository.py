from datetime import datetime

from sqlmodel import select

from app.db.models import Announcement
from app.db.repositories.announcement_repository import AnnouncementRepository



def test_upsert_many_inserts_new_announcements(session, seeded_security):
    repository = AnnouncementRepository(session)

    persisted = repository.upsert_many(
        [
            Announcement(
                security_id=seeded_security.id,
                title="Initial disclosure",
                source="Exchange",
                url="https://example.com/announcements/1",
                summary="Initial summary",
                published_at=datetime(2026, 3, 10, 9, 0),
            ),
            Announcement(
                security_id=seeded_security.id,
                title="Follow-up disclosure",
                source="Exchange",
                url="https://example.com/announcements/2",
                summary="Follow-up summary",
                published_at=datetime(2026, 3, 11, 9, 0),
            ),
        ]
    )

    rows = session.exec(select(Announcement).order_by(Announcement.published_at)).all()

    assert [row.id for row in persisted] == [rows[0].id, rows[1].id]
    assert [(row.title, row.url) for row in rows] == [
        ("Initial disclosure", "https://example.com/announcements/1"),
        ("Follow-up disclosure", "https://example.com/announcements/2"),
    ]



def test_upsert_many_updates_existing_announcement_without_creating_duplicate(session, seeded_security):
    existing = Announcement(
        security_id=seeded_security.id,
        title="Quarterly results",
        source="Exchange",
        url="https://example.com/announcements/original",
        summary="Original summary",
        published_at=datetime(2026, 3, 10, 18, 0),
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    repository = AnnouncementRepository(session)

    persisted = repository.upsert_many(
        [
            Announcement(
                security_id=seeded_security.id,
                title="Quarterly results",
                source="Listed company",
                url="https://example.com/announcements/updated",
                summary="Updated summary",
                published_at=datetime(2026, 3, 10, 18, 0),
            ),
            Announcement(
                security_id=seeded_security.id,
                title="Board meeting notice",
                source="Exchange",
                url="https://example.com/announcements/new",
                summary="New summary",
                published_at=datetime(2026, 3, 11, 8, 30),
            ),
        ]
    )

    rows = session.exec(select(Announcement).order_by(Announcement.published_at, Announcement.id)).all()

    assert len(rows) == 2
    assert rows[0].id == existing.id
    assert rows[0].source == "Listed company"
    assert rows[0].url == "https://example.com/announcements/updated"
    assert rows[0].summary == "Updated summary"
    assert rows[1].title == "Board meeting notice"
    assert {(row.title, row.id) for row in persisted} == {
        ("Quarterly results", existing.id),
        ("Board meeting notice", rows[1].id),
    }
