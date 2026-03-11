import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings
from app.db.models import Security
from app.db.session import create_db_and_tables, make_session
from sqlmodel import create_engine


@pytest.fixture(name="engine")
def engine_fixture() -> Engine:
    engine = create_engine(
        Settings(database_url="sqlite://").database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_db_and_tables(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine: Engine):
    with make_session(engine) as session:
        yield session


@pytest.fixture(name="seeded_security")
def seeded_security_fixture(session):
    security = Security(
        market="SZ",
        code="000001",
        name="Ping An Bank",
        industry="Banking",
        status="active",
    )
    session.add(security)
    session.commit()
    session.refresh(security)
    return security
