"""Health probes, and the property that makes them worth having."""

from __future__ import annotations

from app.pipeline import breaker


def test_liveness_is_ok(client):
    response = client.get("/liveness")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-service"}


def test_readiness_reports_the_provider(client):
    response = client.get("/readiness")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ready"
    assert body["provider"] == "mock"
    assert body["checks"]["provider"] == "ok"
    assert body["checks"]["circuit_breaker"] == "closed"
    assert body["checks"]["embedding_dim"] == 384


def test_readiness_goes_unready_when_the_circuit_opens(client):
    """The point of a readiness probe: it must be able to say no.

    A pod that cannot reach its provider should leave the Service endpoints
    rather than accept traffic it will fail.
    """
    for _ in range(20):
        breaker.record_failure()
    assert breaker.state == "open"

    response = client.get("/readiness")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_liveness_ignores_the_provider(client):
    """Liveness must NOT depend on downstream systems.

    If it did, a provider outage would make Kubernetes restart every healthy
    pod in the deployment and turn a degraded dependency into an outage.
    """
    for _ in range(20):
        breaker.record_failure()

    assert client.get("/liveness").status_code == 200


def test_metrics_endpoint_exposes_prometheus_text(client):
    client.post("/embed", json={"texts": ["hello"]})
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "documind_ai_requests_total" in response.text
    assert "documind_ai_tokens_total" in response.text
