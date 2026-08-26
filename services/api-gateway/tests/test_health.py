"""Health endpoint tests."""

from __future__ import annotations


def test_liveness_returns_200(client):
    response = client.get("/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_returns_200(client):
    response = client.get("/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
