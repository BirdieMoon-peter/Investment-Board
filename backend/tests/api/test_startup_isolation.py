"""Both startup schema creation and route sessions must use isolated databases."""
from fastapi.testclient import TestClient
from app.core.settings import DEFAULT_DATABASE_URL
from app.main import create_app


def test_api_fixture_and_new_app_startup_use_isolated_engine(api_app, engine, monkeypatch):
    import app.main as main_module
    observed = []
    # Record the selected engine before any connection/schema creation; safe RED.
    monkeypatch.setattr(main_module, 'create_db_and_tables', lambda selected: observed.append(selected))
    monkeypatch.delenv('DATABASE_URL', raising=False)
    for app in (api_app, create_app()):
        with TestClient(app):
            pass
    assert len(observed) == 2
    assert all(selected is engine for selected in observed)
    assert all(str(selected.url) != DEFAULT_DATABASE_URL for selected in observed)
