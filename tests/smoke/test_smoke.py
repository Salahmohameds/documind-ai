"""Smoke checks — did this deployment come up correctly?

Read-only by design. These run against whatever was just deployed, so a
test that writes data would pollute the environment it is validating.
"""

import pytest


# ───────────────────────── every service ─────────────────────────

def test_liveness_responds(service_client):
    name, client = service_client
    r = client.get("/liveness")
    assert r.status_code == 200, f"{name} liveness returned {r.status_code}"


def test_readiness_responds(service_client):
    """Readiness is the deployment gate.

    Liveness only says the process started. Readiness says its
    dependencies resolved — which is what determines whether the pod
    should receive traffic at all.
    """
    name, client = service_client
    r = client.get("/readiness")
    assert r.status_code == 200, (
        f"{name} readiness returned {r.status_code}: {r.text[:200]}"
    )


def test_health_probes_need_no_auth(service_client):
    """Kubernetes cannot present a token.

    If a probe starts requiring auth, the kubelet sees 401, marks the
    pod unhealthy, and restarts it forever.
    """
    name, client = service_client
    for path in ("/liveness", "/readiness"):
        r = client.get(path)
        assert r.status_code != 401, f"{name} {path} requires auth"


def test_service_responds_quickly(service_client):
    """A healthy service answers a probe fast.

    Slow probes cause the kubelet to time out and restart pods that are
    merely overloaded, turning a load problem into an outage.
    """
    name, client = service_client
    r = client.get("/liveness")
    elapsed_ms = r.elapsed.total_seconds() * 1000
    assert elapsed_ms < 2000, (
        f"{name} liveness took {elapsed_ms:.0f}ms"
    )


def test_no_stack_traces_on_unknown_paths(service_client):
    """A 404 must not leak internals.

    Framework debug pages expose file paths, versions, and sometimes
    environment variables.
    """
    name, client = service_client
    r = client.get("/this-path-does-not-exist")
    assert r.status_code in (404, 405), f"{name} returned {r.status_code}"
    body = r.text.lower()
    for marker in ("traceback", "file \"/", "line 1,", "site-packages"):
        assert marker not in body, f"{name} leaked internals on 404"


# ──────────────────────── per-service checks ────────────────────────

def test_gateway_rejects_bad_credentials(gateway):
    """One real code path, exercised without creating anything.

    A gateway that returns 200 to a login it should reject is broken in
    a way health probes cannot see.
    """
    r = gateway.post("/auth/login", json={
        "email": "smoke-check@example.invalid",
        "password": "not-a-real-password",
    })
    assert r.status_code == 401, f"expected 401, got {r.status_code}"


def test_gateway_sets_request_id(gateway):
    r = gateway.get("/liveness")
    assert r.headers.get("X-Request-ID"), "no X-Request-ID on the response"


def test_documents_list_is_reachable(documents):
    r = documents.get("/documents", params={"page": 1, "page_size": 1})
    assert r.status_code == 200
    assert "rows" in r.json()


def test_documents_readiness_names_dependencies(documents):
    """A 503 has to be diagnosable at 3am."""
    checks = documents.get("/readiness").json().get("checks", {})
    assert "postgres" in checks
    assert "redis" in checks


def test_search_is_reachable(search):
    r = search.get("/search", params={"question": "smoke check", "top_k": 1})
    assert r.status_code in (200, 401), f"got {r.status_code}"
    if r.status_code == 200:
        assert isinstance(r.json()["results"], list)


def test_ai_service_is_reachable(ai):
    r = ai.get("/liveness")
    assert r.status_code == 200


# ───────────────────────────── summary ─────────────────────────────

def test_at_least_one_service_configured():
    """Guard against a green run that checked nothing.

    A smoke suite with no targets passes trivially, which is worse than
    failing — the pipeline reports success having verified nothing.

    Reads the environment directly rather than importing from conftest:
    under --import-mode=importlib, conftest is not importable by name.
    """
    import os

    configured = [
        name for name, var in (
            ("api-gateway", "API_GATEWAY_URL"),
            ("document-service", "DOCUMENT_SERVICE_URL"),
            ("search-service", "SEARCH_SERVICE_URL"),
            ("ai-service", "AI_SERVICE_URL"),
        )
        if os.environ.get(var)
    ]
    assert configured, (
        "no service URLs set — the smoke suite would pass without "
        "checking anything"
    )