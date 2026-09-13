from datetime import date, datetime
from decimal import Decimal

from app.db.models import Announcement, CompanyProfile, FinancialMetrics, NewsItem, PriceHistory, QuoteSnapshot


def test_get_stock_detail_returns_security_with_price_context_announcements_and_news(
    client,
    seeded_security,
    session,
) -> None:
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.3000"),
            change_amount=Decimal("0.3000"),
            change_percent=Decimal("3.0000"),
            snapshot_time=datetime(2026, 3, 10, 15, 0, 0),
        )
    )
    session.add(
        Announcement(
            security_id=seeded_security.id,
            title="2025 annual results released",
            source="SZSE",
            url="https://example.com/announcements/1",
            summary="Net profit increased year over year.",
            published_at=datetime(2026, 3, 9, 18, 0),
        )
    )
    session.add(
        NewsItem(
            security_id=seeded_security.id,
            title="Broker raises target price",
            source="Market News",
            url="https://example.com/news/1",
            summary="Analyst cited improving fundamentals.",
            published_at=datetime(2026, 3, 10, 8, 30),
        )
    )
    session.commit()

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

    response = client.get(f"/api/stocks/{seeded_security.id}")

    assert response.status_code == 200
    assert response.json() == {
        "security": {
            "security_id": seeded_security.id,
            "market": "SZ",
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "status": "active",
        },
        "price_context": [
            {
                "last_price": "10.3000",
                "change_amount": "0.3000",
                "change_percent": "3.0000",
                "snapshot_time": "2026-03-10T15:00:00Z",
            }
        ],
        "announcements": [
            {
                "title": "2025 annual results released",
                "source": "SZSE",
                "url": "https://example.com/announcements/1",
                "summary": "Net profit increased year over year.",
                "published_at": "2026-03-09T18:00:00",
            }
        ],
        "news": [
            {
                "title": "Broker raises target price",
                "source": "Market News",
                "url": "https://example.com/news/1",
                "summary": "Analyst cited improving fundamentals.",
                "published_at": "2026-03-10T08:30:00",
            }
        ],
        "price_history": [
            {
                "trade_date": "2026-03-10",
                "open_price": "10.5000",
                "high_price": "10.8000",
                "low_price": "10.4000",
                "close_price": "10.7000",
                "volume": "1000000.0000",
                "amount": "10700000.0000",
            }
        ],
        "financial_metrics": [
            {
                "report_period": "2025Q4",
                "revenue": "1000000000.0000",
                "net_profit": "100000000.0000",
                "eps": "1.2500",
                "roe": "0.150000",
                "debt_to_asset_ratio": "0.450000",
            }
        ],
        "company_profile": {
            "full_name": "平安银行股份有限公司",
            "english_name": "Ping An Bank Co., Ltd.",
            "registered_capital": "19405918198.0000",
            "establishment_date": "1987-12-22",
            "website": "https://bank.pingan.com",
            "main_business": "商业银行业务",
            "employees": 35000,
        },
    }


def test_get_stock_detail_returns_price_context_newest_first(
    client,
    seeded_security,
    session,
) -> None:
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.1000"),
            change_amount=Decimal("0.1000"),
            change_percent=Decimal("1.0000"),
            snapshot_time=datetime(2026, 3, 10, 9, 0, 0),
        )
    )
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.4000"),
            change_amount=Decimal("0.4000"),
            change_percent=Decimal("4.0000"),
            snapshot_time=datetime(2026, 3, 10, 15, 0, 0),
        )
    )
    session.commit()

    response = client.get(f"/api/stocks/{seeded_security.id}")

    assert response.status_code == 200
    assert response.json()["price_context"] == [
        {
            "last_price": "10.4000",
            "change_amount": "0.4000",
            "change_percent": "4.0000",
            "snapshot_time": "2026-03-10T15:00:00Z",
        },
        {
            "last_price": "10.1000",
            "change_amount": "0.1000",
            "change_percent": "1.0000",
            "snapshot_time": "2026-03-10T09:00:00Z",
        },
    ]



def test_get_stock_detail_returns_404_for_unknown_security(client) -> None:
    response = client.get("/api/stocks/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "security not found"}
