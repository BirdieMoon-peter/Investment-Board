from app.db.models import Security


def test_search_securities_returns_active_matches_in_repository_order(client, session) -> None:
    ping_an_bank = Security(
        market="SZ",
        code="000001",
        name="Ping An Bank",
        industry="Banking",
        status="active",
    )
    shanghai_pudong_bank = Security(
        market="SH",
        code="600000",
        name="Shanghai Pudong Bank",
        industry="Banking",
        status="active",
    )
    tech_ping = Security(
        market="SZ",
        code="300001",
        name="Tech Ping",
        industry="Technology",
        status="active",
    )
    ping_inactive = Security(
        market="SH",
        code="688001",
        name="Ping Inactive",
        industry="Technology",
        status="inactive",
    )

    session.add_all([ping_an_bank, shanghai_pudong_bank, tech_ping, ping_inactive])
    session.flush()

    response = client.get("/api/watchlist/securities/search", params={"query": "Ping"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "security_id": ping_an_bank.id,
            "market": "SZ",
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "status": "active",
        },
        {
            "security_id": tech_ping.id,
            "market": "SZ",
            "code": "300001",
            "name": "Tech Ping",
            "industry": "Technology",
            "status": "active",
        },
    ]


def test_search_securities_returns_empty_list_when_no_match(client, session) -> None:
    session.connection()

    response = client.get("/api/watchlist/securities/search", params={"query": "no-match"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_securities_rejects_whitespace_only_query(client) -> None:
    response = client.get("/api/watchlist/securities/search", params={"query": "   "})

    assert response.status_code == 422



def test_search_securities_returns_empty_list_and_preserves_custom_add_path(client, session) -> None:
    session.connection()

    response = client.get("/api/watchlist/securities/search", params={"query": "002594"})

    assert response.status_code == 200
    assert response.json() == []


