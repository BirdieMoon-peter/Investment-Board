from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import text

from app.core.settings import Settings
from app.db.models import QuoteSnapshot, Security, WatchlistItem
from app.db.session import create_db_and_tables, make_engine, make_session


def test_session_bootstrap_creates_sqlite_file_and_opens_working_session(tmp_path):
    db_path = tmp_path / "watchlist.db"
    settings = Settings(database_url=f"sqlite:///{db_path}")

    engine = make_engine(settings)
    create_db_and_tables(engine)

    assert Path(db_path).exists()

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert {"securities", "watchlist_items", "quote_snapshots"}.issubset(table_names)

    securities_unique_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("securities")
    }
    assert securities_unique_constraints["uq_securities_market_code"] == ("market", "code")

    watchlist_unique_constraints = {
        tuple(constraint["column_names"]) for constraint in inspector.get_unique_constraints("watchlist_items")
    }
    assert ("security_id",) in watchlist_unique_constraints

    watchlist_foreign_keys = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("watchlist_items")
    }
    assert watchlist_foreign_keys[("security_id",)] == ("securities", ("id",))

    quote_foreign_keys = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("quote_snapshots")
    }
    assert quote_foreign_keys[("security_id",)] == ("securities", ("id",))

    indexes_by_table = {
        table_name: {
            index["name"]: tuple(index["column_names"])
            for index in inspector.get_indexes(table_name)
        }
        for table_name in ("securities", "watchlist_items", "quote_snapshots")
    }

    assert {
        ("market",),
        ("code",),
        ("name",),
        ("status",),
    }.issubset(set(indexes_by_table["securities"].values()))
    assert ("security_id",) in set(indexes_by_table["watchlist_items"].values())
    assert ("security_id",) in set(indexes_by_table["quote_snapshots"].values())
    assert ("snapshot_time",) in set(indexes_by_table["quote_snapshots"].values())
    assert (
        indexes_by_table["quote_snapshots"]["ix_quote_snapshots_security_id_snapshot_time"]
        == ("security_id", "snapshot_time")
    )

    with make_session(engine) as session:
        valid_security = Security(market="SZ", code="000001", name="Ping An Bank")
        session.add(valid_security)
        session.commit()
        session.refresh(valid_security)

        result = session.exec(text("SELECT 1")).one()
        assert result == (1,)

        session.add(WatchlistItem(security_id=valid_security.id + 1))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Expected watchlist_items foreign key enforcement")

        session.add(
            QuoteSnapshot(
                security_id=valid_security.id + 1,
                last_price=Decimal("10.5000"),
                change_amount=Decimal("0.1000"),
                change_percent=Decimal("1.0000"),
                snapshot_time=datetime.now(timezone.utc),
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("Expected quote_snapshots foreign key enforcement")
