from importlib import reload

from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.db.services.seed_demo_data import seed_demo_data
from app.db.session import create_db_and_tables, make_engine, make_session



def test_runtime_app_serves_seeded_watchlist_items_from_configured_database(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "runtime-smoke.db"
    database_url = f"sqlite:///{database_path}"
    settings = Settings(database_url=database_url)
    engine = make_engine(settings)
    create_db_and_tables(engine)
    with make_session(engine) as session:
        seed_demo_data(session)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)

    import app.api.dependencies as dependencies_module
    import app.main as main_module

    reload(dependencies_module)
    reload(main_module)

    with TestClient(main_module.create_app()) as client:
        watchlist_response = client.get("/api/watchlist/items")
        search_response = client.get("/api/watchlist/securities/search", params={"query": "Ping"})

    assert watchlist_response.status_code == 200
    assert watchlist_response.json() == [
        {
            "security_id": 1,
            "market": "SH",
            "code": "600519",
            "name": "Kweichow Moutai",
            "industry": "Beverages",
            "last_price": "1688.0000",
            "change_percent": "0.7362",
            "snapshot_time": "2026-03-11T09:30:00Z",
        },
        {
            "security_id": 2,
            "market": "SZ",
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "last_price": "10.5000",
            "change_percent": "5.0000",
            "snapshot_time": "2026-03-11T09:30:00Z",
        },
    ]
    assert search_response.status_code == 200
    assert search_response.json() == [
        {
            "security_id": 2,
            "market": "SZ",
            "code": "000001",
            "name": "Ping An Bank",
            "industry": "Banking",
            "status": "active",
        }
    ]
