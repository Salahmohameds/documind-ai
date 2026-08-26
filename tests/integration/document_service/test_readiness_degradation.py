"""Readiness and liveness under dependency failure.

Kubernetes treats the two probes differently, and conflating them is a
real outage mode: if liveness also fails when a dependency is down, the
kubelet restarts a healthy container instead of routing traffic away
from it — and keeps restarting it for as long as the dependency is
unavailable.

These tests stop and start real containers, so they mutate cluster
state. They are marked `disruptive` and excluded from the default run.

    docker compose up -d postgres redis
    # document-service on :8081

    pytest tests/integration/document_service/test_readiness_degradation.py \
        -m disruptive -v

Every test restores the container in a finally block, including on
failure. If a run is killed mid-test, restore manually with
`docker compose start redis postgres`.
"""

import shutil
import subprocess
import time

import pytest

pytestmark = pytest.mark.disruptive

COMPOSE = ["docker", "compose"]
SETTLE_SECONDS = 2


def _compose(action, service):
    subprocess.run(
        COMPOSE + [action, service],
        check=True,
        capture_output=True,
        timeout=60,
    )
    time.sleep(SETTLE_SECONDS)


@pytest.fixture(scope="module", autouse=True)
def require_docker():
    if shutil.which("docker") is None:
        pytest.skip("docker not available")


@pytest.fixture
def redis_down():
    """Stop redis for the duration of a test, then always bring it back."""
    _compose("stop", "redis")
    try:
        yield
    finally:
        _compose("start", "redis")


@pytest.fixture
def postgres_down():
    _compose("stop", "postgres")
    try:
        yield
    finally:
        _compose("start", "postgres")


# ───────────────────────── healthy baseline ─────────────────────────

def test_readiness_is_200_when_all_dependencies_are_up(client):
    r = client.get("/readiness")
    assert r.status_code == 200
    checks = r.json()["checks"]
    assert checks["postgres"] == "ok"
    assert checks["redis"] == "ok"


# ───────────────────────────── redis ─────────────────────────────

def test_readiness_is_503_when_redis_is_down(client, redis_down):
    r = client.get("/readiness")
    assert r.status_code == 503
    assert r.json()["checks"]["redis"] != "ok"


def test_readiness_still_names_the_healthy_dependency(client, redis_down):
    """A 503 must be diagnosable.

    Reporting only that something is wrong sends an operator looking at
    every dependency instead of the one that failed.
    """
    checks = client.get("/readiness").json()["checks"]
    assert checks["postgres"] == "ok"
    assert checks["redis"] == "unavailable"


def test_liveness_stays_200_when_redis_is_down(client, redis_down):
    """The process is alive; only a dependency is not.

    If this ever returns non-200, Kubernetes will restart a healthy
    container in a loop for as long as redis is unavailable.
    """
    r = client.get("/liveness")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_does_not_silently_accept_when_the_queue_is_down(
    client, sample_pdf, pdf_upload, redis_down
):
    """Redis is the job queue.

    A 202 with no queue behind it means the file is stored and nothing
    will ever process it — a lost job the client believes succeeded.
    """
    r = client.post("/documents", files=pdf_upload(sample_pdf))
    assert r.status_code == 503, (
        f"expected 503 with the queue down, got {r.status_code} — "
        "an accepted upload that cannot be queued is a silently lost job"
    )
    body = r.json()
    assert body["code"] == "ERR_QUEUE_UNAVAILABLE"
    assert body["retryable"] is True


# ──────────────────────────── postgres ────────────────────────────

def test_readiness_is_503_when_postgres_is_down(client, postgres_down):
    r = client.get("/readiness")
    assert r.status_code == 503
    assert r.json()["checks"]["postgres"] != "ok"


def test_liveness_stays_200_when_postgres_is_down(client, postgres_down):
    r = client.get("/liveness")
    assert r.status_code == 200


# ───────────────────────────── recovery ─────────────────────────────

def test_readiness_recovers_after_redis_returns(client):
    """Degradation must be transient, not sticky.

    A cached or one-shot health result would leave the pod out of
    rotation permanently after a brief dependency blip.
    """
    _compose("stop", "redis")
    try:
        assert client.get("/readiness").status_code == 503
    finally:
        _compose("start", "redis")

    deadline = time.time() + 30
    while time.time() < deadline:
        if client.get("/readiness").status_code == 200:
            return
        time.sleep(1)

    pytest.fail("readiness did not recover within 30s of redis returning")