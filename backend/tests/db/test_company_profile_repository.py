from datetime import date
from decimal import Decimal

from app.db.models import CompanyProfile
from app.db.repositories.company_profile_repository import CompanyProfileRepository



def test_upsert_inserts_and_updates_company_profile(session, seeded_security):
    repository = CompanyProfileRepository(session)

    inserted = repository.upsert(
        CompanyProfile(
            security_id=seeded_security.id,
            full_name="Ping An Bank Co., Ltd.",
            english_name="Ping An Bank Co., Ltd.",
            registered_capital=Decimal("19405918198.0000"),
            establishment_date=date(1987, 12, 22),
            website="https://bank.pingan.com",
            main_business="Commercial banking services",
            employees=35000,
        )
    )

    assert inserted.id is not None
    assert inserted.security_id == seeded_security.id
    assert inserted.full_name == "Ping An Bank Co., Ltd."
    assert inserted.registered_capital == Decimal("19405918198.0000")

    updated = repository.upsert(
        CompanyProfile(
            security_id=seeded_security.id,
            full_name="Ping An Bank Company Limited",
            english_name="Ping An Bank Co., Ltd.",
            registered_capital=Decimal("20000000000.0000"),
            establishment_date=date(1987, 12, 22),
            website="https://bank.pingan.com.cn",
            main_business="Retail and corporate banking services",
            employees=36000,
        )
    )

    assert updated.id == inserted.id
    assert updated.full_name == "Ping An Bank Company Limited"
    assert updated.registered_capital == Decimal("20000000000.0000")
    assert updated.website == "https://bank.pingan.com.cn"
    assert updated.main_business == "Retail and corporate banking services"
    assert updated.employees == 36000



def test_get_by_security_id_returns_company_profile_or_none(session, seeded_security):
    repository = CompanyProfileRepository(session)

    assert repository.get_by_security_id(seeded_security.id) is None

    persisted = repository.upsert(
        CompanyProfile(
            security_id=seeded_security.id,
            full_name="Ping An Bank Co., Ltd.",
            english_name="Ping An Bank Co., Ltd.",
            registered_capital=Decimal("19405918198.0000"),
            establishment_date=date(1987, 12, 22),
            website="https://bank.pingan.com",
            main_business="Commercial banking services",
            employees=35000,
        )
    )

    fetched = repository.get_by_security_id(seeded_security.id)

    assert fetched is not None
    assert fetched.id == persisted.id
    assert fetched.security_id == seeded_security.id
    assert fetched.full_name == "Ping An Bank Co., Ltd."
