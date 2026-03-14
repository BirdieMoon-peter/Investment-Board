from datetime import date
from decimal import Decimal

from sqlmodel import select

from app.db.models import PriceHistory
from app.db.repositories.price_history_repository import PriceHistoryRepository



def test_upsert_many_returns_empty_list_for_empty_input(session):
    repository = PriceHistoryRepository(session)

    assert repository.upsert_many([]) == []



def test_upsert_many_inserts_and_updates_price_history_rows_in_deterministic_input_order(
    session, seeded_security
):
    existing = PriceHistory(
        security_id=seeded_security.id,
        trade_date=date(2026, 3, 10),
        open_price=Decimal("10.1000"),
        high_price=Decimal("10.3000"),
        low_price=Decimal("10.0000"),
        close_price=Decimal("10.2000"),
        volume=Decimal("1000000.0000"),
        amount=Decimal("10200000.0000"),
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    repository = PriceHistoryRepository(session)

    persisted = repository.upsert_many(
        [
            PriceHistory(
                security_id=seeded_security.id,
                trade_date=date(2026, 3, 11),
                open_price=Decimal("10.3000"),
                high_price=Decimal("10.7000"),
                low_price=Decimal("10.2000"),
                close_price=Decimal("10.6000"),
                volume=Decimal("1300000.0000"),
                amount=Decimal("13780000.0000"),
            ),
            PriceHistory(
                security_id=seeded_security.id,
                trade_date=date(2026, 3, 10),
                open_price=Decimal("10.4000"),
                high_price=Decimal("10.8000"),
                low_price=Decimal("10.3000"),
                close_price=Decimal("10.7000"),
                volume=Decimal("1500000.0000"),
                amount=Decimal("16050000.0000"),
            ),
        ]
    )

    rows = session.exec(select(PriceHistory).order_by(PriceHistory.trade_date, PriceHistory.id)).all()

    assert len(rows) == 2
    assert [row.trade_date for row in persisted] == [date(2026, 3, 11), date(2026, 3, 10)]
    assert persisted[0].id == rows[1].id
    assert persisted[1].id == existing.id
    assert rows[0].open_price == Decimal("10.4000")
    assert rows[0].close_price == Decimal("10.7000")
    assert rows[0].volume == Decimal("1500000.0000")
    assert rows[1].open_price == Decimal("10.3000")
    assert rows[1].close_price == Decimal("10.6000")



def test_list_recent_by_security_id_returns_descending_trade_dates(session, seeded_security):
    session.add(
        PriceHistory(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 8),
            open_price=Decimal("9.9000"),
            high_price=Decimal("10.2000"),
            low_price=Decimal("9.8000"),
            close_price=Decimal("10.1000"),
            volume=Decimal("1100000.0000"),
            amount=Decimal("11110000.0000"),
        )
    )
    session.add(
        PriceHistory(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 10),
            open_price=Decimal("10.1000"),
            high_price=Decimal("10.5000"),
            low_price=Decimal("10.0000"),
            close_price=Decimal("10.3000"),
            volume=Decimal("1200000.0000"),
            amount=Decimal("12360000.0000"),
        )
    )
    session.add(
        PriceHistory(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 9),
            open_price=Decimal("10.0000"),
            high_price=Decimal("10.3000"),
            low_price=Decimal("9.9000"),
            close_price=Decimal("10.2000"),
            volume=Decimal("1150000.0000"),
            amount=Decimal("11730000.0000"),
        )
    )
    session.commit()

    repository = PriceHistoryRepository(session)

    rows = repository.list_recent_by_security_id(seeded_security.id, limit=2)

    assert [row.trade_date for row in rows] == [date(2026, 3, 10), date(2026, 3, 9)]
