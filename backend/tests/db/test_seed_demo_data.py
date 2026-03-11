from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import select

from app.db.models import QuoteSnapshot, WatchlistItem
from app.db.repositories import SecurityRepository, WatchlistViewRepository
from app.db.services.seed_demo_data import seed_demo_data



def test_seed_demo_data_populates_deterministic_watchlist_dataset(session):
    seed_demo_data(session)

    securities = SecurityRepository(session).list_by_market_code(
        [("SH", "600519"), ("SZ", "000001"), ("SZ", "300750")]
    )
    quote_snapshots = session.exec(select(QuoteSnapshot).order_by(QuoteSnapshot.id)).all()
    watchlist_items = session.exec(select(WatchlistItem).order_by(WatchlistItem.id)).all()
    watchlist_rows = WatchlistViewRepository(session).list_rows()

    assert [(security.market, security.code, security.name) for security in securities] == [
        ("SH", "600519", "Kweichow Moutai"),
        ("SZ", "000001", "Ping An Bank"),
        ("SZ", "300750", "CATL"),
    ]
    assert len(quote_snapshots) == 3
    assert len(watchlist_items) == 2
    assert [item.security_id for item in watchlist_items] == [securities[0].id, securities[1].id]
    assert [(row.code, row.name) for row in watchlist_rows] == [
        ("600519", "Kweichow Moutai"),
        ("000001", "Ping An Bank"),
    ]
    assert watchlist_rows[0].last_price == Decimal("1688.0000")
    assert watchlist_rows[0].change_percent == Decimal("0.7362")
    assert watchlist_rows[1].last_price == Decimal("10.5000")
    assert watchlist_rows[1].change_percent == Decimal("5.0000")
    assert quote_snapshots[0].change_amount == Decimal("12.3400")
    assert quote_snapshots[1].change_amount == Decimal("0.5000")
    assert quote_snapshots[0].snapshot_time.replace(tzinfo=timezone.utc) == datetime.fromisoformat(
        "2026-03-11T09:30:00+00:00"
    )



def test_seed_demo_data_is_idempotent_for_repeated_runs(session):
    seed_demo_data(session)
    seed_demo_data(session)

    securities = SecurityRepository(session).list_by_market_code(
        [("SH", "600519"), ("SZ", "000001"), ("SZ", "300750")]
    )
    quote_snapshots = session.exec(select(QuoteSnapshot).order_by(QuoteSnapshot.id)).all()
    watchlist_items = session.exec(select(WatchlistItem).order_by(WatchlistItem.id)).all()

    assert len(securities) == 3
    assert len(quote_snapshots) == 6
    assert len(watchlist_items) == 2
