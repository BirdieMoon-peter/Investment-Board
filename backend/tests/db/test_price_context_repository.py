from datetime import date
from decimal import Decimal

from app.db.models import PriceBarDaily
from app.db.repositories.price_context_repository import PriceContextRepository



def test_list_recent_by_security_id_returns_descending_trade_dates(session, seeded_security):
    session.add(
        PriceBarDaily(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 7),
            open_price=Decimal("9.8000"),
            high_price=Decimal("10.1000"),
            low_price=Decimal("9.7000"),
            close_price=Decimal("10.0000"),
            volume=Decimal("1000000.0000"),
        )
    )
    session.add(
        PriceBarDaily(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 9),
            open_price=Decimal("10.0000"),
            high_price=Decimal("10.5000"),
            low_price=Decimal("9.9000"),
            close_price=Decimal("10.3000"),
            volume=Decimal("1200000.0000"),
        )
    )
    session.add(
        PriceBarDaily(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 8),
            open_price=Decimal("9.9000"),
            high_price=Decimal("10.2000"),
            low_price=Decimal("9.8000"),
            close_price=Decimal("10.1000"),
            volume=Decimal("1100000.0000"),
        )
    )
    session.commit()

    repository = PriceContextRepository(session)

    rows = repository.list_recent_by_security_id(seeded_security.id, limit=2)

    assert [row.trade_date for row in rows] == [date(2026, 3, 9), date(2026, 3, 8)]
