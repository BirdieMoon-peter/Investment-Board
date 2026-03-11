from datetime import date, datetime
from decimal import Decimal

from app.db.models import Announcement, NewsItem, PriceBarDaily


def test_get_stock_detail_returns_security_with_price_context_announcements_and_news(
    client,
    seeded_security,
    session,
) -> None:
    session.add(
        PriceBarDaily(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 10),
            open_price=Decimal("10.0000"),
            high_price=Decimal("10.5000"),
            low_price=Decimal("9.8000"),
            close_price=Decimal("10.3000"),
            volume=Decimal("1234567.0000"),
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
                "trade_date": "2026-03-10",
                "open_price": "10.0000",
                "high_price": "10.5000",
                "low_price": "9.8000",
                "close_price": "10.3000",
                "volume": "1234567.0000",
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
    }


def test_get_stock_detail_returns_404_for_unknown_security(client) -> None:
    response = client.get("/api/stocks/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "security not found"}
