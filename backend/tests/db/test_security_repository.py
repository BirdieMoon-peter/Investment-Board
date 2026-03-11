from sqlmodel import select

from app.db.models import Security
from app.db.repositories.security_repository import SecurityRepository


def test_upsert_many_deduplicates_market_code_and_updates_existing_row(session):
    repository = SecurityRepository(session)

    repository.upsert_many(
        [
            Security(
                market="SZ",
                code="000001",
                name="Ping An Bank",
                industry="Banking",
                status="active",
            )
        ]
    )

    repository.upsert_many(
        [
            Security(
                market="SZ",
                code="000001",
                name="Ping An Bank Updated",
                industry="Financial Services",
                status="active",
            )
        ]
    )

    rows = session.exec(select(Security).where(Security.market == "SZ", Security.code == "000001")).all()

    assert len(rows) == 1
    assert rows[0].name == "Ping An Bank Updated"
    assert rows[0].industry == "Financial Services"


def test_upsert_many_returns_unique_rows_for_same_call_duplicate_inputs(session):
    repository = SecurityRepository(session)

    persisted = repository.upsert_many(
        [
            Security(
                market="SZ",
                code="000001",
                name="Ping An Bank",
                industry="Banking",
                status="active",
            ),
            Security(
                market="SZ",
                code="000001",
                name="Ping An Bank Latest",
                industry="Financial Services",
                status="active",
            ),
        ]
    )

    assert len(persisted) == 1
    assert [(security.market, security.code) for security in persisted] == [("SZ", "000001")]

    rows = session.exec(select(Security).where(Security.market == "SZ", Security.code == "000001")).all()
    assert len(rows) == 1
    assert rows[0].name == "Ping An Bank Latest"
    assert rows[0].industry == "Financial Services"


def test_search_prioritizes_exact_and_prefix_matches_filters_inactive_and_caps_results(session):
    repository = SecurityRepository(session)
    repository.upsert_many(
        [
            Security(market="SZ", code="000001", name="Ping An Exact Code", industry="Banking", status="active"),
            Security(market="SH", code="600001", name="000001", industry="Utilities", status="active"),
            Security(market="SZ", code="000001A", name="Prefix One", industry="Tech", status="active"),
            Security(market="SZ", code="000001B", name="Prefix Two", industry="Tech", status="active"),
            Security(market="SH", code="688001", name="Contains 000001 Name", industry="Tech", status="active"),
            Security(market="SZ", code="000001X", name="Inactive Prefix", industry="Tech", status="inactive"),
            *[
                Security(
                    market="SH",
                    code=f"7000{index:02d}",
                    name=f"Bulk 000001 Result {index:02d}",
                    industry="Bulk",
                    status="active",
                )
                for index in range(25)
            ],
        ]
    )

    results = repository.search(" 000001 ")

    assert [security.code for security in results[:5]] == [
        "000001",
        "600001",
        "000001A",
        "000001B",
        "688001",
    ]
    assert all(security.status == "active" for security in results)
    assert len(results) == 20
    assert all((security.market, security.code) != ("SZ", "000001X") for security in results)
    assert repository.search("   ") == []


def test_search_treats_percent_and_underscore_as_literal_characters(session):
    repository = SecurityRepository(session)
    repository.upsert_many(
        [
            Security(market="SZ", code="50%_1", name="Literal %_ code", industry="Special", status="active"),
            Security(market="SH", code="500001", name="Wildcard candidate", industry="Special", status="active"),
            Security(market="SZ", code="123456", name="Alpha%_Beta", industry="Special", status="active"),
            Security(market="SH", code="654321", name="AlphaXBeta", industry="Special", status="active"),
        ]
    )

    code_results = repository.search("50%_")
    name_results = repository.search("%_")

    assert [(security.market, security.code) for security in code_results] == [("SZ", "50%_1")]
    assert [(security.market, security.code) for security in name_results] == [
        ("SZ", "123456"),
        ("SZ", "50%_1"),
    ]
