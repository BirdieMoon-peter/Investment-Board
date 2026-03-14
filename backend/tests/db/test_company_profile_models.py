from datetime import date
from decimal import Decimal

from sqlalchemy import inspect

from app.core.settings import Settings
from app.db.models import CompanyProfile
from app.db.session import create_db_and_tables, make_engine, make_session


def test_company_profile_model_registers_expected_schema_and_fields(tmp_path):
    profile = CompanyProfile(
        security_id=1,
        full_name="Ping An Bank Co., Ltd.",
        english_name="Ping An Bank Co., Ltd.",
        registered_capital=Decimal("19405918198.0000"),
        establishment_date=date(1987, 12, 22),
        website="https://bank.pingan.com",
        main_business="Commercial banking services",
        employees=35000,
    )

    assert profile.security_id == 1
    assert profile.full_name == "Ping An Bank Co., Ltd."
    assert profile.registered_capital == Decimal("19405918198.0000")
    assert profile.establishment_date == date(1987, 12, 22)
    assert profile.employees == 35000

    db_path = tmp_path / "company-profile.db"
    engine = make_engine(Settings(database_url=f"sqlite:///{db_path}"))
    create_db_and_tables(engine)

    inspector = inspect(engine)
    assert "company_profiles" in set(inspector.get_table_names())

    foreign_keys = {
        tuple(foreign_key["constrained_columns"]): (
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("company_profiles")
    }
    assert foreign_keys[("security_id",)] == ("securities", ("id",))

    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("company_profiles")
    }
    assert ("security_id",) in set(indexes.values())

    unique_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("company_profiles")
    }
    assert unique_constraints["uq_company_profiles_security_id"] == ("security_id",)


def test_company_profile_model_persists_round_trip(session, seeded_security):
    profile = CompanyProfile(
        security_id=seeded_security.id,
        full_name="Ping An Bank Co., Ltd.",
        english_name="Ping An Bank Co., Ltd.",
        registered_capital=Decimal("19405918198.0000"),
        establishment_date=date(1987, 12, 22),
        website="https://bank.pingan.com",
        main_business="Commercial banking services",
        employees=35000,
    )

    session.add(profile)
    session.commit()
    session.refresh(profile)

    with make_session(session.bind) as verification_session:
        persisted_profile = verification_session.get(CompanyProfile, profile.id)

    assert persisted_profile is not None
    assert persisted_profile.security_id == seeded_security.id
    assert persisted_profile.full_name == "Ping An Bank Co., Ltd."
    assert persisted_profile.registered_capital == Decimal("19405918198.0000")
    assert persisted_profile.establishment_date == date(1987, 12, 22)
    assert persisted_profile.website == "https://bank.pingan.com"
    assert persisted_profile.main_business == "Commercial banking services"
    assert persisted_profile.employees == 35000
