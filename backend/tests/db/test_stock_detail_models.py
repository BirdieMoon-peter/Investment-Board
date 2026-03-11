from sqlalchemy import inspect

from app.db.session import create_db_and_tables, make_engine
from app.core.settings import Settings


def test_stock_detail_schema_registers_detail_tables_and_indexes(tmp_path):
    db_path = tmp_path / "stock-detail.db"
    engine = make_engine(Settings(database_url=f"sqlite:///{db_path}"))

    create_db_and_tables(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert {"price_bar_daily", "announcements", "news_items"}.issubset(table_names)

    expected_foreign_key = ("securities", ("id",))
    for table_name in ("price_bar_daily", "announcements", "news_items"):
        foreign_keys = {
            tuple(foreign_key["constrained_columns"]): (
                foreign_key["referred_table"],
                tuple(foreign_key["referred_columns"]),
            )
            for foreign_key in inspector.get_foreign_keys(table_name)
        }
        assert foreign_keys[("security_id",)] == expected_foreign_key

    indexes_by_table = {
        table_name: {
            index["name"]: tuple(index["column_names"])
            for index in inspector.get_indexes(table_name)
        }
        for table_name in ("price_bar_daily", "announcements", "news_items")
    }

    assert {
        ("security_id",),
        ("trade_date",),
        ("security_id", "trade_date"),
    }.issubset(set(indexes_by_table["price_bar_daily"].values()))
    assert {
        ("security_id",),
        ("published_at",),
    }.issubset(set(indexes_by_table["announcements"].values()))
    assert {
        ("security_id",),
        ("published_at",),
    }.issubset(set(indexes_by_table["news_items"].values()))
