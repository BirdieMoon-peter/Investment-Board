from decimal import Decimal

from sqlalchemy import inspect

from app.core.settings import Settings
from app.db.models import FinancialMetrics
from app.db.session import create_db_and_tables, make_engine, make_session


def test_financial_metrics_model_registers_expected_schema_and_fields(tmp_path):
    metrics = FinancialMetrics(
        security_id=1,
        report_period="2025Q4",
        revenue=Decimal("1000000000.0000"),
        net_profit=Decimal("100000000.0000"),
        eps=Decimal("1.2500"),
        roe=Decimal("0.150000"),
        debt_to_asset_ratio=Decimal("0.450000"),
    )

    assert metrics.security_id == 1
    assert metrics.report_period == "2025Q4"
    assert metrics.eps == Decimal("1.2500")
    assert metrics.roe == Decimal("0.150000")

    db_path = tmp_path / "financial-metrics.db"
    engine = make_engine(Settings(database_url=f"sqlite:///{db_path}"))
    create_db_and_tables(engine)

    inspector = inspect(engine)
    assert "financial_metrics" in set(inspector.get_table_names())

    foreign_keys = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("financial_metrics")
    }
    assert foreign_keys[("security_id",)] == ("securities", ("id",))

    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("financial_metrics")
    }
    assert {
        ("security_id",),
        ("report_period",),
        ("security_id", "report_period"),
    }.issubset(set(indexes.values()))

    unique_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("financial_metrics")
    }
    assert unique_constraints["uq_financial_metrics_security_id_report_period"] == (
        "security_id",
        "report_period",
    )


def test_financial_metrics_model_persists_round_trip(session, seeded_security):
    metrics = FinancialMetrics(
        security_id=seeded_security.id,
        report_period="2025Q4",
        revenue=Decimal("1000000000.0000"),
        net_profit=Decimal("100000000.0000"),
        eps=Decimal("1.2500"),
        roe=Decimal("0.150000"),
        debt_to_asset_ratio=Decimal("0.450000"),
    )

    session.add(metrics)
    session.commit()
    session.refresh(metrics)

    with make_session(session.bind) as verification_session:
        persisted_metrics = verification_session.get(FinancialMetrics, metrics.id)

    assert persisted_metrics is not None
    assert persisted_metrics.security_id == seeded_security.id
    assert persisted_metrics.report_period == "2025Q4"
    assert persisted_metrics.revenue == Decimal("1000000000.0000")
    assert persisted_metrics.eps == Decimal("1.2500")
    assert persisted_metrics.debt_to_asset_ratio == Decimal("0.450000")
