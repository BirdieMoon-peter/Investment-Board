from app.db.repositories import SecurityRepository, WatchlistRepository
from app.db.services.bootstrap_data import bootstrap_market_data
from sqlmodel import Session

DEMO_SECURITIES = [
    {
        "market": "SH",
        "code": "600519",
        "name": "Kweichow Moutai",
        "industry": "Beverages",
        "status": "active",
    },
    {
        "market": "SZ",
        "code": "000001",
        "name": "Ping An Bank",
        "industry": "Banking",
        "status": "active",
    },
    {
        "market": "SZ",
        "code": "300750",
        "name": "CATL",
        "industry": "Battery",
        "status": "active",
    },
]

DEMO_QUOTE_SNAPSHOTS = [
    {
        "market": "SH",
        "code": "600519",
        "last_price": "1688.0000",
        "change_amount": "12.3400",
        "change_percent": "0.7362",
        "snapshot_time": "2026-03-11T09:30:00+00:00",
    },
    {
        "market": "SZ",
        "code": "000001",
        "last_price": "10.5000",
        "change_amount": "0.5000",
        "change_percent": "5.0000",
        "snapshot_time": "2026-03-11T09:30:00+00:00",
    },
    {
        "market": "SZ",
        "code": "300750",
        "last_price": "210.2500",
        "change_amount": "-3.7500",
        "change_percent": "-1.7539",
        "snapshot_time": "2026-03-11T09:30:00+00:00",
    },
]

DEMO_WATCHLIST_KEYS = [("SH", "600519"), ("SZ", "000001")]



def seed_demo_data(session: Session) -> None:
    bootstrap_market_data(
        session,
        securities=DEMO_SECURITIES,
        quote_snapshots=DEMO_QUOTE_SNAPSHOTS,
    )

    security_repository = SecurityRepository(session)
    watchlist_repository = WatchlistRepository(session)
    for security in security_repository.list_by_market_code(DEMO_WATCHLIST_KEYS):
        watchlist_repository.add(security.id)
