from datetime import datetime, timedelta
from decimal import Decimal

from app.db.models import QuoteSnapshot, Security
from app.db.repositories.watchlist_repository import WatchlistRepository
from app.db.repositories.watchlist_view_repository import WatchlistRow, WatchlistViewRepository



def test_list_rows_returns_latest_snapshot_for_each_security(session):
    alpha = Security(
        market="SH",
        code="600001",
        name="Alpha Co",
        industry="Utilities",
        status="active",
    )
    beta = Security(
        market="SZ",
        code="000001",
        name="Beta Co",
        industry="Banking",
        status="active",
    )
    session.add(alpha)
    session.add(beta)
    session.commit()
    session.refresh(alpha)
    session.refresh(beta)

    watchlist_repository = WatchlistRepository(session)
    watchlist_repository.add(alpha.id)
    watchlist_repository.add(beta.id)

    older_time = datetime(2026, 3, 10, 9, 30)
    latest_time = older_time + timedelta(minutes=5)
    beta_time = older_time + timedelta(minutes=2)

    session.add(
        QuoteSnapshot(
            security_id=alpha.id,
            last_price=Decimal("10.1000"),
            change_amount=Decimal("0.1000"),
            change_percent=Decimal("1.0000"),
            snapshot_time=older_time,
        )
    )
    session.add(
        QuoteSnapshot(
            security_id=alpha.id,
            last_price=Decimal("10.5000"),
            change_amount=Decimal("0.5000"),
            change_percent=Decimal("5.0000"),
            snapshot_time=latest_time,
        )
    )
    session.add(
        QuoteSnapshot(
            security_id=beta.id,
            last_price=Decimal("8.8000"),
            change_amount=Decimal("-0.2000"),
            change_percent=Decimal("-2.2222"),
            snapshot_time=beta_time,
        )
    )
    session.commit()

    repository = WatchlistViewRepository(session)

    rows = repository.list_rows()

    assert rows == [
        WatchlistRow(
            security_id=alpha.id,
            code="600001",
            name="Alpha Co",
            industry="Utilities",
            last_price=Decimal("10.5000"),
            change_percent=Decimal("5.0000"),
            snapshot_time=latest_time,
        ),
        WatchlistRow(
            security_id=beta.id,
            code="000001",
            name="Beta Co",
            industry="Banking",
            last_price=Decimal("8.8000"),
            change_percent=Decimal("-2.2222"),
            snapshot_time=beta_time,
        ),
    ]



def test_list_rows_returns_single_deterministic_row_when_latest_snapshot_time_ties(
    session, seeded_security
):
    watchlist_repository = WatchlistRepository(session)
    watchlist_repository.add(seeded_security.id)

    tied_time = datetime(2026, 3, 10, 10, 0)

    first_snapshot = QuoteSnapshot(
        security_id=seeded_security.id,
        last_price=Decimal("10.1000"),
        change_amount=Decimal("0.1000"),
        change_percent=Decimal("1.0000"),
        snapshot_time=tied_time,
    )
    second_snapshot = QuoteSnapshot(
        security_id=seeded_security.id,
        last_price=Decimal("10.2000"),
        change_amount=Decimal("0.2000"),
        change_percent=Decimal("2.0000"),
        snapshot_time=tied_time,
    )
    session.add(first_snapshot)
    session.add(second_snapshot)
    session.commit()
    session.refresh(second_snapshot)

    repository = WatchlistViewRepository(session)

    rows = repository.list_rows()

    assert rows == [
        WatchlistRow(
            security_id=seeded_security.id,
            code="000001",
            name="Ping An Bank",
            industry="Banking",
            last_price=Decimal("10.2000"),
            change_percent=Decimal("2.0000"),
            snapshot_time=tied_time,
        )
    ]



def test_list_rows_keeps_security_when_quote_is_missing(session, seeded_security):
    watchlist_repository = WatchlistRepository(session)
    watchlist_repository.add(seeded_security.id)

    repository = WatchlistViewRepository(session)

    rows = repository.list_rows()

    assert rows == [
        WatchlistRow(
            security_id=seeded_security.id,
            code="000001",
            name="Ping An Bank",
            industry="Banking",
            last_price=None,
            change_percent=None,
            snapshot_time=None,
        )
    ]
