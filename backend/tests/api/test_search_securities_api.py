from dataclasses import dataclass

from sqlmodel import select

from app.api.watchlist import get_security_search_service
from app.db.models import Security
from app.db.repositories.security_repository import SecurityRepository
from app.services.providers.raw_types import RawSecurityLookup
from app.services.security_search import SecuritySearchService


@dataclass
class StubSearchSource:
    results: list[RawSecurityLookup] | None = None
    error: Exception | None = None
    calls: list[tuple[str, int]] | None = None

    def search(self, query: str, limit: int = 20) -> list[RawSecurityLookup]:
        if self.calls is not None:
            self.calls.append((query, limit))
        if self.error is not None:
            raise self.error
        return list(self.results or [])


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


def test_search_securities_returns_empty_list_when_no_match(client, session, override_dependency) -> None:
    override_dependency(
        get_security_search_service,
        lambda: SecuritySearchService(repository=SecurityRepository(session), source=StubSearchSource()),
    )

    response = client.get("/api/watchlist/securities/search", params={"query": "no-match"})

    assert response.status_code == 200
    assert response.json() == []



def test_search_securities_falls_back_to_external_results_and_persists_them(
    client,
    override_dependency,
    session,
) -> None:
    calls: list[tuple[str, int]] = []
    override_dependency(
        get_security_search_service,
        lambda: SecuritySearchService(
            repository=SecurityRepository(session),
            source=StubSearchSource(
                results=[
                    RawSecurityLookup(market="SZ", code="002594", name="BYD", industry="Auto"),
                    RawSecurityLookup(market="SH", code="600036", name="China Merchants Bank", industry="Banking"),
                ],
                calls=calls,
            ),
        ),
    )

    response = client.get("/api/watchlist/securities/search", params={"query": "BYD"})

    assert response.status_code == 200
    assert [item["code"] for item in response.json()] == ["002594", "600036"]
    assert calls == [("BYD", 20)]
    assert session.exec(
        select(Security).where(Security.market == "SZ", Security.code == "002594")
    ).one().name == "BYD"



def test_search_securities_returns_empty_list_when_external_search_fails(
    client,
    override_dependency,
    session,
) -> None:
    override_dependency(
        get_security_search_service,
        lambda: SecuritySearchService(
            repository=SecurityRepository(session),
            source=StubSearchSource(error=RuntimeError("upstream unavailable")),
        ),
    )

    response = client.get("/api/watchlist/securities/search", params={"query": "002594"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_securities_rejects_whitespace_only_query(client) -> None:
    response = client.get("/api/watchlist/securities/search", params={"query": "   "})

    assert response.status_code == 422



def test_search_securities_returns_external_match_for_unknown_a_share_code(client, session, override_dependency) -> None:
    override_dependency(
        get_security_search_service,
        lambda: SecuritySearchService(
            repository=SecurityRepository(session),
            source=StubSearchSource(results=[RawSecurityLookup(market="SZ", code="002594", name="BYD", industry="Auto")]),
        ),
    )

    response = client.get("/api/watchlist/securities/search", params={"query": "002594"})

    assert response.status_code == 200
    assert response.json()[0]["market"] == "SZ"
    assert response.json()[0]["code"] == "002594"


