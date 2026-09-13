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
            "market": "SZ",
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "last_price": "10.2000",
            "change_percent": "2.0000",
            "snapshot_time": "2026-03-10T10:00:00Z",
        }
    ]


def test_list_watchlist_items_keeps_security_when_quote_snapshot_is_missing(client, seeded_security) -> None:
    client.post("/api/watchlist/items", json={"security_id": seeded_security.id})

    response = client.get("/api/watchlist/items")

    assert response.status_code == 200
    assert response.json() == [
        {
            "security_id": seeded_security.id,
            "market": "SZ",
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "last_price": None,
            "change_percent": None,
            "snapshot_time": None,
        }
    ]


def test_provider_utc_survives_sqlite_roundtrip_in_quote_apis(client, seeded_security, session):
    from datetime import UTC
    import httpx
    from app.services.providers.eastmoney_quote_snapshot import EastmoneyQuoteSnapshotSource

    source = EastmoneyQuoteSnapshotSource(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json={"data": {"f43": 1050, "f169": 20, "f170": 194, "f124": "20260911150000"}}
    )))
    quote = source.fetch("000001", "SZ")
    assert quote.snapshot_time == datetime(2026, 9, 11, 7, tzinfo=UTC)
    client.post("/api/watchlist/items", json={"security_id": seeded_security.id})
    session.add(QuoteSnapshot(
        security_id=seeded_security.id, last_price=quote.last_price,
        change_amount=quote.change_amount, change_percent=quote.change_percent,
        snapshot_time=quote.snapshot_time,
    ))
    session.commit()
    session.expire_all()
    assert client.get("/api/watchlist/items").json()[0]["snapshot_time"] == "2026-09-11T07:00:00Z"
    detail = client.get(f"/api/stocks/{seeded_security.id}")
    assert detail.json()["price_context"][0]["snapshot_time"] == "2026-09-11T07:00:00Z"
