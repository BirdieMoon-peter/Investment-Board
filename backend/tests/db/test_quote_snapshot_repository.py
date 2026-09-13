from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlmodel import Session, select

from app.db.models import QuoteSnapshot
from app.db.repositories.quote_snapshot_repository import QuoteSnapshotRepository


def _quote(security_id, timestamp, price="10"):
    return QuoteSnapshot(
        security_id=security_id, snapshot_time=timestamp, last_price=Decimal(price),
        change_amount=Decimal("0.1"), change_percent=Decimal("1"),
    )


@pytest.mark.parametrize("incoming_time", [
    datetime(2026, 9, 11, 7, tzinfo=UTC),
    datetime(2026, 9, 11, 15, tzinfo=ZoneInfo("Asia/Shanghai")),
])
def test_quote_upsert_reuses_same_instant_across_sqlite_sessions(engine, seeded_security, incoming_time):
    with Session(engine) as first:
        rows = QuoteSnapshotRepository(first).upsert_many([
            _quote(seeded_security.id, datetime(2026, 9, 11, 7, tzinfo=UTC))
        ])
        original_id = rows[0].id
    with Session(engine) as second:
        rows = QuoteSnapshotRepository(second).upsert_many([
            _quote(seeded_security.id, incoming_time, "11")
        ])
        assert rows[0].id == original_id
        assert rows[0].snapshot_time == datetime(2026, 9, 11, 7)
    with Session(engine) as check:
        rows = check.exec(select(QuoteSnapshot)).all()
        assert len(rows) == 1
        assert rows[0].last_price == Decimal("11")


def test_quote_batch_merges_naive_utc_and_aware_same_instant(session, seeded_security):
    rows = QuoteSnapshotRepository(session).upsert_many([
        _quote(seeded_security.id, datetime(2026, 9, 11, 7)),
        _quote(seeded_security.id, datetime(2026, 9, 11, 15, tzinfo=ZoneInfo("Asia/Shanghai")), "11"),
    ])
    assert len(rows) == 1
    assert rows[0].last_price == Decimal("11")
    assert rows[0].snapshot_time == datetime(2026, 9, 11, 7)
