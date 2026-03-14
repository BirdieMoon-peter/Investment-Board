from datetime import date
from decimal import Decimal

from app.db.models import CompanyProfile, FinancialMetrics, PriceHistory
from app.db.repositories.stock_detail_repository import StockDetailRepository



def test_get_by_security_id_returns_empty_sections_when_detail_data_is_missing(session, seeded_security):
    repository = StockDetailRepository(session)

    detail = repository.get_by_security_id(seeded_security.id)

    assert detail is not None
    assert detail.security.id == seeded_security.id
    assert detail.security.code == "000001"
    assert detail.security.name == "Ping An Bank"
    assert detail.price_context == []
    assert detail.announcements == []
    assert detail.news == []
    assert detail.price_history == []
    assert detail.financial_metrics == []
    assert detail.company_profile is None



def test_get_by_security_id_returns_stock_data_sections(session, seeded_security):
    session.add(
        PriceHistory(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 10),
            open_price=Decimal("10.5000"),
            high_price=Decimal("10.8000"),
            low_price=Decimal("10.4000"),
            close_price=Decimal("10.7000"),
            volume=Decimal("1000000.0000"),
            amount=Decimal("10700000.0000"),
        )
    )
    session.add(
        FinancialMetrics(
            security_id=seeded_security.id,
            report_period="2025Q4",
            revenue=Decimal("1000000000.0000"),
            net_profit=Decimal("100000000.0000"),
            eps=Decimal("1.2500"),
            roe=Decimal("0.150000"),
            debt_to_asset_ratio=Decimal("0.450000"),
        )
    )
    session.add(
        CompanyProfile(
            security_id=seeded_security.id,
            full_name="平安银行股份有限公司",
            english_name="Ping An Bank Co., Ltd.",
            registered_capital=Decimal("19405918198.0000"),
            establishment_date=date(1987, 12, 22),
            website="https://bank.pingan.com",
            main_business="商业银行业务",
            employees=35000,
        )
    )
    session.commit()

    repository = StockDetailRepository(session)
    detail = repository.get_by_security_id(seeded_security.id)

    assert detail is not None
    assert len(detail.price_history) == 1
    assert detail.price_history[0].trade_date == date(2026, 3, 10)
    assert detail.price_history[0].close_price == Decimal("10.7000")
    assert detail.price_history[0].amount == Decimal("10700000.0000")
    assert len(detail.financial_metrics) == 1
    assert detail.financial_metrics[0].report_period == "2025Q4"
    assert detail.financial_metrics[0].eps == Decimal("1.2500")
    assert detail.financial_metrics[0].debt_to_asset_ratio == Decimal("0.450000")
    assert detail.company_profile is not None
    assert detail.company_profile.full_name == "平安银行股份有限公司"
    assert detail.company_profile.english_name == "Ping An Bank Co., Ltd."
    assert detail.company_profile.employees == 35000
