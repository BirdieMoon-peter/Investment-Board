from sqlmodel import select

from app.db.models import Holding



def test_upsert_holding_creates_and_updates_position(client, seeded_security, session) -> None:
    create_response = client.post(
        "/api/holdings",
        json={
            "security_id": seeded_security.id,
            "quantity": "100.0000",
            "average_cost": "12.3400",
            "notes": "core position",
            "target_horizon": "long_term",
        },
    )

    assert create_response.status_code == 200
    created_payload = create_response.json()
    assert created_payload == {
        "holding_id": created_payload["holding_id"],
        "security_id": seeded_security.id,
        "security": {
            "security_id": seeded_security.id,
            "market": "SZ",
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "status": "active",
        },
        "quantity": "100.0000",
        "average_cost": "12.3400",
        "notes": "core position",
        "target_horizon": "long_term",
    }

    second_response = client.post(
        "/api/holdings",
        json={
            "security_id": seeded_security.id,
            "quantity": "120.0000",
            "average_cost": "11.8800",
            "notes": "updated",
            "target_horizon": "swing",
        },
    )

    assert second_response.status_code == 200
    assert second_response.json()["holding_id"] == created_payload["holding_id"]
    assert second_response.json()["quantity"] == "120.0000"
    assert second_response.json()["average_cost"] == "11.8800"
    assert len(session.exec(select(Holding)).all()) == 1



def test_list_holdings_returns_latest_positions(client, seeded_security, session) -> None:
    client.post(
        "/api/holdings",
        json={
            "security_id": seeded_security.id,
            "quantity": "50.0000",
            "average_cost": "10.5000",
        },
    )

    response = client.get("/api/holdings")

    assert response.status_code == 200
    assert response.json() == [
        {
            "holding_id": response.json()[0]["holding_id"],
            "security_id": seeded_security.id,
            "security": {
                "security_id": seeded_security.id,
                "market": "SZ",
                "code": "000001",
                "name": "Ping An Bank",
                "industry": "Banking",
                "status": "active",
            },
            "quantity": "50.0000",
            "average_cost": "10.5000",
            "notes": None,
            "target_horizon": None,
        }
    ]



def test_update_holding_returns_404_when_missing(client, seeded_security) -> None:
    response = client.put(
        "/api/holdings/999",
        json={
            "security_id": seeded_security.id,
            "quantity": "50.0000",
            "average_cost": "10.5000",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "holding not found"}



def test_update_holding_rejects_security_change(client, seeded_security, session) -> None:
    second_security = seeded_security.__class__(
        market="SH",
        code="600000",
        name="Shanghai Pudong Bank",
        industry="Banking",
        status="active",
    )
    session.add(second_security)
    session.commit()
    session.refresh(second_security)

    created = client.post(
        "/api/holdings",
        json={
            "security_id": seeded_security.id,
            "quantity": "50.0000",
            "average_cost": "10.5000",
        },
    ).json()

    response = client.put(
        f"/api/holdings/{created['holding_id']}",
        json={
            "security_id": second_security.id,
            "quantity": "80.0000",
            "average_cost": "9.9000",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "security_id cannot be changed"}



def test_remove_holding_returns_removed_response(client, seeded_security) -> None:
    created = client.post(
        "/api/holdings",
        json={
            "security_id": seeded_security.id,
            "quantity": "20.0000",
            "average_cost": "10.0000",
        },
    ).json()

    response = client.delete(f"/api/holdings/{created['holding_id']}")

    assert response.status_code == 200
    assert response.json() == {"removed": True, "holding_id": created["holding_id"]}



def test_remove_holding_returns_404_when_missing(client) -> None:
    response = client.delete("/api/holdings/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "holding not found"}
