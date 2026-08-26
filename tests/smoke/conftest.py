"""Post-deploy smoke checks.

Runs against a deployed environment to answer one question: did this
deployment come up correctly? Not a functional suite — it must finish in
seconds and must not mutate anything, because it runs against whatever
was just deployed, including production.

Each service is optional. A service with no URL configured is skipped
rather than failed, so the same suite works during a partial rollout.

    API_GATEWAY_URL=https://gateway.dev.example \
    DOCUMENT_SERVICE_URL=https://documents.dev.example \
    SEARCH_SERVICE_URL=https://search.dev.example \
    AI_SERVICE_URL=https://ai.dev.example \
        pytest tests/smoke -v
"""

import os

import httpx
import pytest

# Deliberately tight. A deployed service that needs longer than this to
# answer a health probe is not healthy, and a slow smoke suite gets
# skipped by the people who need it most.
TIMEOUT = float(os.environ.get("SMOKE_TIMEOUT", "5"))

SERVICES = {
    "api-gateway": os.environ.get("API_GATEWAY_URL"),
    "document-service": os.environ.get("DOCUMENT_SERVICE_URL"),
    "search-service": os.environ.get("SEARCH_SERVICE_URL"),
    "ai-service": os.environ.get("AI_SERVICE_URL"),
}


def pytest_generate_tests(metafunc):
    """Parametrise over whichever services are configured."""
    if "service" in metafunc.fixturenames:
        configured = [(n, u) for n, u in SERVICES.items() if u]
        if not configured:
            pytest.skip("no service URLs configured")
        metafunc.parametrize(
            "service",
            configured,
            ids=[n for n, _ in configured],
        )


@pytest.fixture
def service_client(service):
    name, url = service
    with httpx.Client(base_url=url.rstrip("/"), timeout=TIMEOUT) as c:
        yield name, c


def client_for(name):
    """A client for one named service, or skip if it is not configured."""
    url = SERVICES.get(name)
    if not url:
        pytest.skip(f"{name} not configured")
    return httpx.Client(base_url=url.rstrip("/"), timeout=TIMEOUT)


@pytest.fixture
def gateway():
    with client_for("api-gateway") as c:
        yield c


@pytest.fixture
def documents():
    with client_for("document-service") as c:
        yield c


@pytest.fixture
def search():
    with client_for("search-service") as c:
        yield c


@pytest.fixture
def ai():
    with client_for("ai-service") as c:
        yield c