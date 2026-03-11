from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlmodel import select

from app.db.models import QuoteSnapshot
from app.db.repositories import SecurityRepository, WatchlistViewRepository
from app.db.services.bootstrap_data import bootstrap_market_data



def test_bootstrap_market_data_ingests_securities_and_quote_snapshots_without_creating_watchlist_rows(
    session,
):
    bootstrap_market_data(
        session,
        securities=[
            {
                "market": "SZ",
                "code": "000001",
                "name": "Ping An Bank",
                "industry": "Banking",
                "status": "active",
            }
        ],
        quote_snapshots=[
            {
                "market": "SZ",
                "code": "000001",
                "last_price": "10.5000",
                "change_amount": "0.5000",
                "change_percent": "5.0000",
                "snapshot_time": "2026-03-10T09:35:00+00:00",
            }
        ],
    )

    security = SecurityRepository(session).list_by_market_code([("SZ", "000001")])[0]
    quote_snapshots = session.exec(select(QuoteSnapshot)).all()

    assert WatchlistViewRepository(session).list_rows() == []
    assert security.name == "Ping An Bank"
    assert len(quote_snapshots) == 1
    assert quote_snapshots[0].security_id == security.id
    assert quote_snapshots[0].last_price == Decimal("10.5000")
    assert quote_snapshots[0].change_amount == Decimal("0.5000")
    assert quote_snapshots[0].change_percent == Decimal("5.0000")
    assert quote_snapshots[0].snapshot_time == datetime(2026, 3, 10, 9, 35)
    assert quote_snapshots[0].snapshot_time.replace(tzinfo=timezone.utc) == datetime.fromisoformat(
        "2026-03-10T09:35:00+00:00"
    )



def test_bootstrap_market_data_rejects_unknown_quote_snapshot_keys_without_partial_writes(session):
    with pytest.raises(ValueError, match=r"Unknown security keys in quote_snapshots: \[\('SH', '600000'\)\]"):
        bootstrap_market_data(
            session,
            securities=[
                {
                    "market": "SZ",
                    "code": "000001",
                    "name": "Ping An Bank",
                    "industry": "Banking",
                    "status": "active",
                }
            ],
            quote_snapshots=[
                {
                    "market": "SH",
                    "code": "600000",
                    "last_price": "12.3400",
                    "change_amount": "0.1200",
                    "change_percent": "0.9800",
                    "snapshot_time": "2026-03-10T09:35:00+00:00",
                }
            ],
        )

    assert SecurityRepository(session).list_by_market_code([("SZ", "000001")]) == []
    assert session.exec(select(QuoteSnapshot)).all() == []
    assert WatchlistViewRepository(session).list_rows() == []



def test_bootstrap_market_data_rejects_extra_security_keys_without_partial_writes(session):
    with pytest.raises(ValueError, match=r"Unexpected keys in securities: \['exchange_name'\]"):
        bootstrap_market_data(
            session,
            securities=[
                {
                    "market": "SZ",
                    "code": "000001",
                    "name": "Ping An Bank",
                    "industry": "Banking",
                    "status": "active",
                    "exchange_name": "Shenzhen",
                }
            ],
            quote_snapshots=[],
        )

    assert SecurityRepository(session).list_by_market_code([("SZ", "000001")]) == []
    assert session.exec(select(QuoteSnapshot)).all() == []
    assert WatchlistViewRepository(session).list_rows() == []



def test_bootstrap_market_data_rejects_extra_quote_snapshot_keys_without_partial_writes(session):
    with pytest.raises(ValueError, match=r"Unexpected keys in quote_snapshots: \['currency'\]"):
        bootstrap_market_data(
            session,
            securities=[
                {
                    "market": "SZ",
                    "code": "000001",
                    "name": "Ping An Bank",
                    "industry": "Banking",
                    "status": "active",
                }
            ],
            quote_snapshots=[
                {
                    "market": "SZ",
                    "code": "000001",
                    "last_price": "10.5000",
                    "change_amount": "0.5000",
                    "change_percent": "5.0000",
                    "snapshot_time": "2026-03-10T09:35:00+00:00",
                    "currency": "CNY",
                }
            ],
        )

    assert SecurityRepository(session).list_by_market_code([("SZ", "000001")]) == []
    assert session.exec(select(QuoteSnapshot)).all() == []
    assert WatchlistViewRepository(session).list_rows() == []



def test_bootstrap_market_data_accepts_missing_security_status_and_defaults_to_active(session):
    bootstrap_market_data(
        session,
        securities=[
            {
                "market": "SZ",
                "code": "000001",
                "name": "Ping An Bank",
                "industry": "Banking",
            }
        ],
        quote_snapshots=[],
    )

    security = SecurityRepository(session).list_by_market_code([("SZ", "000001")])[0]

    assert security.name == "Ping An Bank"
    assert security.status == "active"
    assert session.exec(select(QuoteSnapshot)).all() == []
    assert WatchlistViewRepository(session).list_rows() == []



def test_bootstrap_market_data_rejects_missing_quote_snapshot_keys_without_partial_writes(session):
    with pytest.raises(ValueError, match=r"Missing required keys in quote_snapshots: \['change_percent'\]"):
        bootstrap_market_data(
            session,
            securities=[
                {
                    "market": "SZ",
                    "code": "000001",
                    "name": "Ping An Bank",
                    "industry": "Banking",
                    "status": "active",
                }
            ],
            quote_snapshots=[
                {
                    "market": "SZ",
                    "code": "000001",
                    "last_price": "10.5000",
                    "change_amount": "0.5000",
                    "snapshot_time": "2026-03-10T09:35:00+00:00",
                }
            ],
        )

    assert SecurityRepository(session).list_by_market_code([("SZ", "000001")]) == []
    assert session.exec(select(QuoteSnapshot)).all() == []
    assert WatchlistViewRepository(session).list_rows() == []
