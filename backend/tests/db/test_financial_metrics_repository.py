from decimal import Decimal

from sqlmodel import select

from app.db.models import FinancialMetrics
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository



def test_upsert_many_returns_empty_list_for_empty_input(session):
    repository = FinancialMetricsRepository(session)

    assert repository.upsert_many([]) == []



def test_upsert_many_inserts_and_updates_financial_metrics_in_deterministic_input_order(
    session, seeded_security
):
    existing = FinancialMetrics(
        security_id=seeded_security.id,
        report_period="2025Q4",
        revenue=Decimal("1000000000.0000"),
        net_profit=Decimal("100000000.0000"),
        eps=Decimal("1.2500"),
        roe=Decimal("0.150000"),
        debt_to_asset_ratio=Decimal("0.450000"),
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    repository = FinancialMetricsRepository(session)

    persisted = repository.upsert_many(
        [
            FinancialMetrics(
                security_id=seeded_security.id,
                report_period="2026Q1",
                revenue=Decimal("1200000000.0000"),
                net_profit=Decimal("125000000.0000"),
                eps=Decimal("1.3200"),
                roe=Decimal("0.152000"),
                debt_to_asset_ratio=Decimal("0.430000"),
            ),
            FinancialMetrics(
                security_id=seeded_security.id,
                report_period="2025Q4",
                revenue=Decimal("1100000000.0000"),
                net_profit=Decimal("110000000.0000"),
                eps=Decimal("1.2800"),
                roe=Decimal("0.151000"),
                debt_to_asset_ratio=Decimal("0.440000"),
            ),
            FinancialMetrics(
                security_id=seeded_security.id,
                report_period="2026Q1",
                revenue=Decimal("1250000000.0000"),
                net_profit=Decimal("130000000.0000"),
                eps=Decimal("1.3400"),
                roe=Decimal("0.153000"),
                debt_to_asset_ratio=Decimal("0.420000"),
            ),
        ]
    )

    rows = session.exec(
        select(FinancialMetrics).order_by(
            FinancialMetrics.report_period, FinancialMetrics.id
        )
    ).all()

    assert len(rows) == 2
    assert [row.report_period for row in persisted] == ["2026Q1", "2025Q4"]
    assert persisted[0].id == rows[1].id
    assert persisted[1].id == existing.id
    assert rows[0].revenue == Decimal("1100000000.0000")
    assert rows[0].eps == Decimal("1.2800")
    assert rows[1].revenue == Decimal("1250000000.0000")
    assert rows[1].eps == Decimal("1.3400")



def test_list_recent_by_security_id_returns_descending_report_periods(session, seeded_security):
    session.add(
        FinancialMetrics(
            security_id=seeded_security.id,
            report_period="2025Q3",
            revenue=Decimal("900000000.0000"),
            net_profit=Decimal("80000000.0000"),
            eps=Decimal("0.9800"),
        )
    )
    session.add(
        FinancialMetrics(
            security_id=seeded_security.id,
            report_period="2025Q4",
            revenue=Decimal("1000000000.0000"),
            net_profit=Decimal("100000000.0000"),
            eps=Decimal("1.2500"),
        )
    )
    session.add(
        FinancialMetrics(
            security_id=seeded_security.id,
            report_period="2024Q4",
            revenue=Decimal("850000000.0000"),
            net_profit=Decimal("75000000.0000"),
            eps=Decimal("0.9100"),
        )
    )
    session.commit()

    repository = FinancialMetricsRepository(session)

    rows = repository.list_recent_by_security_id(seeded_security.id, limit=2)

    assert [row.report_period for row in rows] == ["2025Q4", "2025Q3"]
