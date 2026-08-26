"""End-to-end pipeline tests.

Exercises the whole path: upload to document-service, job published to
Redis, claimed by processing-service, text extracted, ai-service called
for classification, extraction and risk, chunks indexed via
search-service, status written back.

Needs all four services plus postgres and redis. Skips cleanly if any
one of them is unreachable, so it is safe to run anywhere.

    docker compose up -d postgres redis
    # document-service :8081, ai-service :8083,
    # search-service :8090, processing-service :8084

    pytest tests/integration/e2e -v
"""

import os

import httpx
import pytest

DOCUMENTS_URL = os.environ.get("DOCUMENT_SERVICE_URL", "http://127.0.0.1:8081")
SEARCH_URL = os.environ.get("SEARCH_SERVICE_URL", "http://127.0.0.1:8090")
PROCESSING_URL = os.environ.get("PROCESSING_SERVICE_URL", "http://127.0.0.1:8084")

# Processing is async and involves several network hops. Generous, but
# bounded: a test that waits forever is a test that hides a hang.
PROCESSING_TIMEOUT = float(os.environ.get("E2E_PROCESSING_TIMEOUT", "120"))
POLL_INTERVAL = 1.0

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "fixtures"
)

# document-service reports lowercase; the worker writes uppercase to
# processing_jobs; documents.status uses INDEXED rather than COMPLETED.
# Three vocabularies for one lifecycle, so terminal states are matched
# case-insensitively against every spelling in use.
TERMINAL_OK = {"completed", "indexed"}
TERMINAL_BAD = {"failed"}


def _reachable(url):
    try:
        httpx.get(f"{url.rstrip('/')}/liveness", timeout=3)
        return True
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session", autouse=True)
def require_full_stack():
    missing = [
        name for name, url in (
            ("document-service", DOCUMENTS_URL),
            ("search-service", SEARCH_URL),
            ("processing-service", PROCESSING_URL),
        )
        if not _reachable(url)
    ]
    if missing:
        pytest.skip(f"pipeline incomplete — unreachable: {', '.join(missing)}")


@pytest.fixture(scope="session")
def documents():
    with httpx.Client(base_url=DOCUMENTS_URL.rstrip("/"), timeout=30) as c:
        yield c


@pytest.fixture(scope="session")
def search():
    with httpx.Client(base_url=SEARCH_URL.rstrip("/"), timeout=30) as c:
        yield c


@pytest.fixture(scope="session")
def processing():
    with httpx.Client(base_url=PROCESSING_URL.rstrip("/"), timeout=30) as c:
        yield c


def load_fixture(kind, name):
    path = os.path.join(FIXTURES, kind, name)
    if not os.path.exists(path):
        pytest.skip(
            f"{name} not generated — run tests/fixtures/generator/"
            + ("edge_cases.py" if kind == "edge-cases" else "generate.py")
        )
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def contract_pdf():
    return load_fixture("documents", "contract_0000.pdf")


@pytest.fixture(scope="session")
def invoice_pdf():
    return load_fixture("documents", "invoice_0000.pdf")


@pytest.fixture(scope="session")
def ground_truth():
    """Expected values for contract_0000, built into the document."""
    import json
    path = os.path.join(FIXTURES, "ground-truth", "contract_0000.json")
    if not os.path.exists(path):
        pytest.skip("ground truth not generated")
    with open(path, encoding="utf-8") as f:
        return json.load(f)