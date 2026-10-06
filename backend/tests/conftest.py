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


@pytest.fixture
def quant_dataset(seeded_security):
    """Clearly synthetic raw prices, calendar and ETF assumption; not market evidence."""
    from datetime import date, timedelta
    days = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(12)]
    return {'name': 'Synthetic fixture only', 'source': 'synthetic_test_fixture', 'retrieved_at': '2025-02-01T00:00:00Z', 'price_basis': 'raw', 'currency': 'CNY', 'volume_unit': 'shares', 'calendar': days, 'calendar_provenance': 'synthetic_observed_sessions', 'corporate_action_coverage': 'unknown', 'actions': [], 'instruments': [{'security_id': seeded_security.id, 'market': seeded_security.market, 'code': seeded_security.code, 'name': 'Synthetic ETF assumption', 'instrument_type': 'etf', 'lot_size': 100, 'settlement_lag': 1, 'limit_pct': None}], 'bars': [{'security_id': seeded_security.id, 'date': day, 'open': str(10+i), 'close': str(10+i), 'high': str(11+i), 'low': str(9+i), 'volume': '1000000'} for i, day in enumerate(days)]}


@pytest.fixture
def quant_strategy(seeded_security):
    return {'name': 'Synthetic trend', 'template': 'ma_trend', 'universe': [seeded_security.id], 'parameters': {'ma_window': 2, 'rebalance_every': 1}, 'max_exposure': '1'}


@pytest.fixture
def quant_costs():
    return {'commission_rate': '0', 'minimum_commission': '0', 'sell_tax': '0', 'slippage': '0', 'volume_cap': '1'}
