from datetime import datetime
from decimal import Decimal

from app.db.models import QuoteSnapshot
from app.db.repositories.price_context_repository import PriceContextRepository



def test_list_recent_by_security_id_returns_descending_snapshot_times(session, seeded_security):
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.0000"),
            change_amount=Decimal("0.1000"),
            change_percent=Decimal("1.0000"),
            snapshot_time=datetime(2026, 3, 7, 15, 0, 0),
        )
    )
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.3000"),
            change_amount=Decimal("0.3000"),
            change_percent=Decimal("3.0000"),
            snapshot_time=datetime(2026, 3, 9, 15, 0, 0),
        )
    )
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.1000"),
            change_amount=Decimal("0.2000"),
            change_percent=Decimal("2.0000"),
            snapshot_time=datetime(2026, 3, 8, 15, 0, 0),
        )
    )
    session.commit()

    repository = PriceContextRepository(session)

    rows = repository.list_recent_by_security_id(seeded_security.id, limit=2)

    assert [row.snapshot_time for row in rows] == [
        datetime(2026, 3, 9, 15, 0, 0),
        datetime(2026, 3, 8, 15, 0, 0),
    ]



def test_list_recent_by_security_id_filters_invalid_epoch_snapshots(session, seeded_security):
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("7.5000"),
            change_amount=Decimal("0.1000"),
            change_percent=Decimal("1.0000"),
            snapshot_time=datetime(1970, 1, 1, 0, 0, 0),
        )
    )
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("7.7000"),
            change_amount=Decimal("0.2000"),
            change_percent=Decimal("2.0000"),
            snapshot_time=datetime(2026, 3, 20, 15, 0, 0),
        )
    )
    session.commit()

    repository = PriceContextRepository(session)

    rows = repository.list_recent_by_security_id(seeded_security.id, limit=5)

    assert len(rows) == 1
    assert rows[0].last_price == Decimal("7.7000")
