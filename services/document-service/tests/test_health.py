"""Tests for health probe endpoints.

Covers:
  1. GET /liveness — always 200, no dependency check.
  2. GET /readiness — 200 when deps healthy, 503 when degraded.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestLiveness:
    """GET /liveness must always return 200 without touching Postgres/Redis."""

    def test_returns_200(self, client):
        resp = client.get("/liveness")
        assert resp.status_code == 200

    def test_response_shape(self, client):
        data = client.get("/liveness").json()
        assert data["status"] == "ok"
        assert data["service"] == "document-service"


class TestReadiness:
    """GET /readiness checks both Postgres and Redis."""

    def test_ready_when_both_healthy(self, client):
        """With the test SQLite DB, Postgres check passes.
        We mock Redis to also pass."""
        with patch("app.routes.health.redis") as mock_redis:
            mock_conn = MagicMock()
            mock_redis.from_url.return_value = mock_conn
            mock_conn.ping.return_value = True

            resp = client.get("/readiness")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ready"
            assert data["checks"]["postgres"] == "ok"
            assert data["checks"]["redis"] == "ok"

    def test_degraded_when_redis_unavailable(self, client):
        """If Redis is down, readiness should return 503."""
        with patch("app.routes.health.redis") as mock_redis:
            mock_redis.from_url.side_effect = Exception("Connection refused")

            resp = client.get("/readiness")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["checks"]["redis"] == "unavailable"
