from datetime import datetime
from decimal import Decimal

from app.db.models import QuoteSnapshot


def test_list_watchlist_items_returns_joined_security_and_latest_quote_fields(client, seeded_security, session) -> None:
    client.post("/api/watchlist/items", json={"security_id": seeded_security.id})
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.2000"),
            change_amount=Decimal("0.2000"),
            change_percent=Decimal("2.0000"),
            snapshot_time=datetime(2026, 3, 10, 10, 0),
        )
    )
    session.commit()

    response = client.get("/api/watchlist/items")

    assert response.status_code == 200
    assert response.json() == [
        {
            "security_id": seeded_security.id,
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "last_price": "10.2000",
            "change_percent": "2.0000",
            "snapshot_time": "2026-03-10T10:00:00",
        }
    ]


def test_list_watchlist_items_keeps_security_when_quote_snapshot_is_missing(client, seeded_security) -> None:
    client.post("/api/watchlist/items", json={"security_id": seeded_security.id})

    response = client.get("/api/watchlist/items")

    assert response.status_code == 200
    assert response.json() == [
        {
            "security_id": seeded_security.id,
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "last_price": None,
            "change_percent": None,
            "snapshot_time": None,
        }
    ]
