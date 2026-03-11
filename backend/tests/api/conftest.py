from collections.abc import Generator
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.dependencies import get_session
from app.main import create_app


@pytest.fixture(name="api_app")
def api_app_fixture(session: Session) -> Any:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    return app


@pytest.fixture(name="client")
def client_fixture(api_app) -> Generator[TestClient, None, None]:
    with TestClient(api_app) as test_client:
        yield test_client


@pytest.fixture(name="override_dependency")
def override_dependency_fixture(api_app) -> Callable[[Callable[..., Any], Callable[..., Any]], None]:
    def apply_override(dependency: Callable[..., Any], override: Callable[..., Any]) -> None:
        api_app.dependency_overrides[dependency] = override

    return apply_override


@pytest.fixture(autouse=True)
def clear_dependency_overrides(api_app) -> Generator[None, None, None]:
    yield
    api_app.dependency_overrides.clear()
