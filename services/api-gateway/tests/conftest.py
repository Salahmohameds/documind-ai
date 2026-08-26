"""Shared test fixtures for the API Gateway tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.store import InMemoryUserStore


@pytest.fixture()
def client():
    """Provide a fresh TestClient for each test.

    The user store is re-initialised so tests are isolated: the module-level
    singleton in ``app.auth.store`` is replaced for the duration of each test.

    The proxy HTTP client is also reset so respx mocks work correctly.
    """
    # Re-import to ensure a fresh app state per test.
    import app.auth.store as store_module
    store_module.user_store = InMemoryUserStore()

    # Reset the proxy's httpx client so each test starts fresh
    # and respx can intercept the newly created client.
    import app.proxy as proxy_module
    proxy_module.http_client = None

    from app.main import app
    with TestClient(app) as c:
        yield c
