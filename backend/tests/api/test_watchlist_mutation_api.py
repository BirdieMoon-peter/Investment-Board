from sqlmodel import select

from app.db.models import WatchlistItem


def test_add_watchlist_item_is_idempotent_and_returns_same_security_id(client, seeded_security, session) -> None:
    first_response = client.post(
        "/api/watchlist/items",
        json={"security_id": seeded_security.id},
    )
    second_response = client.post(
        "/api/watchlist/items",
        json={"security_id": seeded_security.id},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == {"security_id": seeded_security.id}
    assert second_response.json() == {"security_id": seeded_security.id}
    assert len(session.exec(select(WatchlistItem)).all()) == 1


def test_add_watchlist_item_returns_404_for_unknown_security(client) -> None:
    response = client.post("/api/watchlist/items", json={"security_id": 999})

    assert response.status_code == 404
    assert response.json() == {"detail": "security not found"}


def test_remove_watchlist_item_returns_removed_response(client, seeded_security) -> None:
    client.post("/api/watchlist/items", json={"security_id": seeded_security.id})

    response = client.delete(f"/api/watchlist/items/{seeded_security.id}")

    assert response.status_code == 200
    assert response.json() == {"removed": True, "security_id": seeded_security.id}


def test_remove_watchlist_item_returns_404_when_missing(client) -> None:
    response = client.delete("/api/watchlist/items/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "watchlist item not found"}
