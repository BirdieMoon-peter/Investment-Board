from dataclasses import dataclass

from sqlmodel import select

from app.api.watchlist import get_security_lookup_service
from app.db.models import Security, WatchlistItem
from app.db.repositories.security_repository import SecurityRepository
from app.schemas import SecuritySearchResult
from app.services.security_lookup import (
    SecurityLookupNotFoundError,
    SecurityLookupProviderError,
    SecurityLookupService,
)
from app.services.providers.raw_types import RawSecurityLookup


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


@dataclass
class StubLookupSource:
    result: RawSecurityLookup | None = None
    error: Exception | None = None
    calls: list[tuple[str, str]] | None = None

    def fetch(self, market: str, code: str) -> RawSecurityLookup:
        if self.calls is not None:
            self.calls.append((market, code))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result



def test_add_watchlist_item_by_market_code_creates_missing_security_and_returns_it(
    client,
    override_dependency,
    session,
) -> None:
    calls: list[tuple[str, str]] = []
    override_dependency(
        get_security_lookup_service,
        lambda: SecurityLookupService(
            repository=SecurityRepository(session),
            source=StubLookupSource(
                result=RawSecurityLookup(
                    market=" sz ",
                    code=" 002594 ",
                    name="BYD",
                    industry="Auto",
                ),
                calls=calls,
            ),
        ),
    )

    response = client.post(
        "/api/watchlist/items/custom",
        json={"market": " sz ", "code": " 002594 "},
    )

    created_security = session.exec(
        select(Security).where(Security.market == "SZ", Security.code == "002594")
    ).one()

    assert response.status_code == 200
    assert response.json() == {
        "security_id": created_security.id,
        "security": SecuritySearchResult.from_model(created_security).model_dump(mode="json"),
    }
    assert calls == [("SZ", "002594")]
    assert len(session.exec(select(WatchlistItem)).all()) == 1



def test_add_watchlist_item_by_market_code_returns_422_for_invalid_market(client) -> None:
    response = client.post(
        "/api/watchlist/items/custom",
        json={"market": "HK", "code": "00700"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "market must be SH or SZ"}



def test_add_watchlist_item_by_market_code_returns_422_for_blank_code(client) -> None:
    response = client.post(
        "/api/watchlist/items/custom",
        json={"market": "SZ", "code": "   "},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "code"]
    assert "code must not be blank" in response.json()["detail"][0]["msg"]



def test_add_watchlist_item_by_market_code_returns_404_when_lookup_has_no_match(
    client,
    override_dependency,
    session,
) -> None:
    override_dependency(
        get_security_lookup_service,
        lambda: SecurityLookupService(
            repository=SecurityRepository(session),
            source=StubLookupSource(error=ValueError("security lookup returned no matches")),
        ),
    )

    response = client.post(
        "/api/watchlist/items/custom",
        json={"market": "SZ", "code": "002594"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "security not found"}



def test_add_watchlist_item_by_market_code_returns_502_for_provider_failure(
    client,
    override_dependency,
    session,
) -> None:
    override_dependency(
        get_security_lookup_service,
        lambda: SecurityLookupService(
            repository=SecurityRepository(session),
            source=StubLookupSource(error=RuntimeError("upstream unavailable")),
        ),
    )

    response = client.post(
        "/api/watchlist/items/custom",
        json={"market": "SZ", "code": "002594"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "security lookup unavailable"}



def test_remove_watchlist_item_returns_404_when_missing(client) -> None:
    response = client.delete("/api/watchlist/items/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "watchlist item not found"}
