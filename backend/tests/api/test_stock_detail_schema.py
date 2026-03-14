from datetime import date, datetime
from decimal import Decimal

from app.db.models import CompanyProfile, FinancialMetrics, PriceHistory
from app.db.repositories import StockDetail, StockDetailSecurity
from app.schemas.stock_detail import StockDetailResponse, StockSyncResponse



def test_stock_detail_response_maps_stock_data_sections_from_repository_model() -> None:
    detail = StockDetail(
        security=StockDetailSecurity(
            id=7,
            market="SZ",
            code="000001",
            name="Ping An Bank",
            industry="Banking",
            status="active",
        ),
        price_context=[],
        announcements=[],
        news=[],
        price_history=[
            PriceHistory(
                security_id=7,
                trade_date=date(2026, 3, 10),
                open_price=Decimal("10.5000"),
                high_price=Decimal("10.8000"),
                low_price=Decimal("10.4000"),
                close_price=Decimal("10.7000"),
                volume=Decimal("1000000.0000"),
                amount=Decimal("10700000.0000"),
            )
        ],
        financial_metrics=[
            FinancialMetrics(
                security_id=7,
                report_period="2025Q4",
                revenue=Decimal("1000000000.0000"),
                net_profit=Decimal("100000000.0000"),
                eps=Decimal("1.2500"),
                roe=Decimal("0.150000"),
                debt_to_asset_ratio=Decimal("0.450000"),
            )
        ],
        company_profile=CompanyProfile(
            security_id=7,
            full_name="平安银行股份有限公司",
            english_name="Ping An Bank Co., Ltd.",
            registered_capital=Decimal("19405918198.0000"),
            establishment_date=date(1987, 12, 22),
            website="https://bank.pingan.com",
            main_business="商业银行业务",
            employees=35000,
        ),
    )

    response = StockDetailResponse.from_repository_model(detail)

    assert response.price_history[0].trade_date == date(2026, 3, 10)
    assert response.price_history[0].amount == Decimal("10700000.0000")
    assert response.financial_metrics[0].report_period == "2025Q4"
    assert response.financial_metrics[0].roe == Decimal("0.150000")
    assert response.company_profile is not None
    assert response.company_profile.full_name == "平安银行股份有限公司"
    assert response.company_profile.website == "https://bank.pingan.com"



def test_stock_sync_response_includes_stock_data_summary_fields() -> None:
    response = StockSyncResponse.from_service_result(
        security_id=7,
        synced=True,
        announcements_upserted=2,
        news_items_upserted=3,
        price_bars_upserted=10,
        financial_metrics_upserted=4,
        company_profile_updated=True,
        warnings=["price source timeout"],
        synced_at=datetime(2026, 3, 13, 10, 0, 0),
    )

    assert response.security_id == 7
    assert response.price_bars_upserted == 10
    assert response.financial_metrics_upserted == 4
    assert response.company_profile_updated is True
    assert response.warnings == ["price source timeout"]
