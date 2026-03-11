from datetime import datetime

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
