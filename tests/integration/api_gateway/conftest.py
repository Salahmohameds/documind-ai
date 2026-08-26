"""Shared fixtures for api-gateway contract tests.

Start a local instance:

    cd services/api-gateway
    uvicorn app.main:app --port 8000

The user store is in-memory (M1 scope), so registrations do not survive
a restart and are not shared across replicas. Tests register their own
users under unique emails rather than assuming any seeded account.
"""

import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("API_GATEWAY_URL", "http://localhost:8000")
TIMEOUT = float(os.environ.get("API_GATEWAY_TIMEOUT", "10"))

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL.rstrip("/"), timeout=TIMEOUT) as c:
        try:
            c.get("/liveness")
        except httpx.ConnectError:
            pytest.skip(
                f"no api-gateway at {BASE_URL} — "
                "set API_GATEWAY_URL or start a local instance"
            )
        yield c


@pytest.fixture
def new_email():
    """A unique email per test.

    The store persists for the process lifetime, so reusing an address
    across tests would collide on the second registration.
    """
    return f"qa_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def registered(client, new_email):
    """Register a user and return (email, password)."""
    r = client.post("/auth/register", json={
        "email": new_email,
        "password": PASSWORD,
        "name": "QA Tester",
        "org": "DocuMind QA",
    })
    assert r.status_code == 200, r.text
    return new_email, PASSWORD


@pytest.fixture
def token(client, registered):
    """A valid JWT for a freshly registered user."""
    email, password = registered
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]