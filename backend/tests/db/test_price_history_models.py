from datetime import date
from decimal import Decimal

from sqlalchemy import inspect

from app.core.settings import Settings
from app.db.models import PriceHistory
from app.db.session import create_db_and_tables, make_engine, make_session


def test_price_history_model_registers_expected_schema_and_fields(tmp_path):
    price_history_row = PriceHistory(
        security_id=1,
        trade_date=date(2026, 3, 10),
        open_price=Decimal("100.5000"),
        high_price=Decimal("102.0000"),
        low_price=Decimal("99.8000"),
        close_price=Decimal("101.2000"),
        volume=Decimal("1000000.0000"),
        amount=Decimal("101000000.0000"),
    )

    assert price_history_row.security_id == 1
    assert price_history_row.trade_date == date(2026, 3, 10)
    assert price_history_row.close_price == Decimal("101.2000")
    assert price_history_row.amount == Decimal("101000000.0000")

    db_path = tmp_path / "price-history.db"
    engine = make_engine(Settings(database_url=f"sqlite:///{db_path}"))
    create_db_and_tables(engine)

    inspector = inspect(engine)
    assert "price_history" in set(inspector.get_table_names())

    foreign_keys = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("price_history")
    }
    assert foreign_keys[("security_id",)] == ("securities", ("id",))

    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("price_history")
    }
    assert {
        ("security_id",),
        ("trade_date",),
        ("security_id", "trade_date"),
    }.issubset(set(indexes.values()))

    unique_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("price_history")
    }
    assert unique_constraints["uq_price_history_security_id_trade_date"] == (
        "security_id",
        "trade_date",
    )


def test_price_history_model_persists_round_trip(session, seeded_security):
    price_history_row = PriceHistory(
        security_id=seeded_security.id,
        trade_date=date(2026, 3, 10),
        open_price=Decimal("100.5000"),
        high_price=Decimal("102.0000"),
        low_price=Decimal("99.8000"),
        close_price=Decimal("101.2000"),
        volume=Decimal("1000000.0000"),
        amount=Decimal("101000000.0000"),
    )

    session.add(price_history_row)
    session.commit()
    session.refresh(price_history_row)

    with make_session(session.bind) as verification_session:
        persisted_row = verification_session.get(PriceHistory, price_history_row.id)

    assert persisted_row is not None
    assert persisted_row.security_id == seeded_security.id
    assert persisted_row.trade_date == date(2026, 3, 10)
    assert persisted_row.close_price == Decimal("101.2000")
    assert persisted_row.volume == Decimal("1000000.0000")
