from dataclasses import dataclass

from sqlmodel import Session, create_engine

from app.db.repositories.security_repository import SecurityRepository
from app.services.providers.raw_types import RawSecurityLookup
from app.services.security_search import SecuritySearchService
from app.db.session import create_db_and_tables


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


def test_security_search_service_returns_local_results_without_external_call() -> None:
    engine = create_engine("sqlite://")
    create_db_and_tables(engine)

    with Session(engine) as session:
        repository = SecurityRepository(session)
        local = repository.upsert_many([
            __import__("app.db.models", fromlist=["Security"]).Security(
                market="SZ", code="000001", name="Ping An Bank", industry="Banking", status="active"
            )
        ])
        calls: list[tuple[str, int]] = []
        service = SecuritySearchService(repository=repository, source=StubSearchSource(calls=calls))

        results = service.search("Ping")

        assert [item.id for item in results] == [local[0].id]
        assert calls == []


def test_security_search_service_persists_external_results_when_local_empty() -> None:
    engine = create_engine("sqlite://")
    create_db_and_tables(engine)

    with Session(engine) as session:
        repository = SecurityRepository(session)
        service = SecuritySearchService(
            repository=repository,
            source=StubSearchSource(
                results=[RawSecurityLookup(market="SZ", code="002594", name="BYD", industry="Auto")]
            ),
        )

        results = service.search("BYD")

        assert [(item.market, item.code, item.name) for item in results] == [("SZ", "002594", "BYD")]
        assert repository.get_by_market_code("SZ", "002594") is not None


def test_security_search_service_returns_empty_list_when_external_search_fails() -> None:
    engine = create_engine("sqlite://")
    create_db_and_tables(engine)

    with Session(engine) as session:
        repository = SecurityRepository(session)
        service = SecuritySearchService(repository=repository, source=StubSearchSource(error=RuntimeError("boom")))

        assert service.search("BYD") == []
