from dataclasses import dataclass

import pytest

from app.db.models import Security
from app.db.repositories.security_repository import SecurityRepository
from app.services.security_lookup import SecurityLookupNotFoundError, SecurityLookupService
from app.services.providers.raw_types import RawSecurityLookup


@dataclass
class StubLookupSource:
    result: RawSecurityLookup
    calls: list[tuple[str, str]]

    def fetch(self, market: str, code: str) -> RawSecurityLookup:
        self.calls.append((market, code))
        return self.result


def test_security_lookup_service_creates_missing_security_from_lookup_source(session):
    repository = SecurityRepository(session)
    source = StubLookupSource(
        RawSecurityLookup(
            market="SZ",
            code="002594",
            name="BYD",
            industry="Auto",
        ),
        [],
    )
    service = SecurityLookupService(repository=repository, source=source)

    security = service.lookup_or_create("sz", "002594")

    assert security.market == "SZ"
    assert security.code == "002594"
    assert security.name == "BYD"
    assert source.calls == [("SZ", "002594")]


def test_security_lookup_service_returns_existing_security_without_lookup(session):
    existing = Security(
        market="SH",
        code="600519",
        name="Kweichow Moutai",
        industry="Beverage",
        status="active",
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    repository = SecurityRepository(session)
    source = StubLookupSource(
        RawSecurityLookup(
            market="SH",
            code="600519",
            name="Should Not Be Used",
        ),
        [],
    )
    service = SecurityLookupService(repository=repository, source=source)

    security = service.lookup_or_create(" sh ", "600519")

    assert security.id == existing.id
    assert security.name == "Kweichow Moutai"
    assert source.calls == []



def test_security_lookup_service_persists_requested_identifiers_when_provider_returns_normalized_variants(
    session,
):
    repository = SecurityRepository(session)
    source = StubLookupSource(
        RawSecurityLookup(
            market=" sz ",
            code=" 002594 ",
            name="BYD",
            industry="Auto",
        ),
        [],
    )
    service = SecurityLookupService(repository=repository, source=source)

    security = service.lookup_or_create("SZ", "002594")

    assert security.market == "SZ"
    assert security.code == "002594"



def test_security_lookup_service_raises_not_found_for_market_code_mismatch(session):
    repository = SecurityRepository(session)
    source = StubLookupSource(
        RawSecurityLookup(
            market="SH",
            code="600000",
            name="Wrong Security",
        ),
        [],
    )
    service = SecurityLookupService(repository=repository, source=source)

    with pytest.raises(SecurityLookupNotFoundError, match="security not found"):
        service.lookup_or_create("SZ", "002594")
