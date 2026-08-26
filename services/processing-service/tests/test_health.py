"""Probe behaviour.

The distinction these pin down is the one a worker gets wrong most easily:
liveness must track *the consumer*, not the HTTP server. A pod whose consumer
task has died still answers HTTP perfectly — it is Running, Ready, and using no
CPU while the queue silently grows. Nothing else in the platform detects that.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import health


class FakeConsumer:
    def __init__(self, *, running: bool = True, group: bool = True) -> None:
        self.is_running = running
        self._group = group

    async def group_exists(self) -> bool:
        return self._group


class FakeRedisClient:
    def __init__(self, *, up: bool = True) -> None:
        self._up = up

    async def ping(self) -> bool:
        if not self._up:
            raise ConnectionError("redis is down")
        return True


class FakeReader:
    def __init__(self, *, up: bool = True) -> None:
        self._up = up

    def health_check(self) -> None:
        if not self._up:
            raise RuntimeError("storage is unreachable")


def build_app(**state) -> FastAPI:
    app = FastAPI()
    app.include_router(health.router)
    app.state.shutting_down = state.get("shutting_down", False)
    app.state.consumer_task = state.get("consumer_task")
    app.state.consumer = state.get("consumer", FakeConsumer())
    app.state.redis = state.get("redis", FakeRedisClient())
    app.state.reader = state.get("reader", FakeReader())
    return app


class FakeTask:
    """Stands in for the consumer task.

    The route asks it exactly one question — ``done()`` — so a real asyncio
    task here would only add an event loop to manage and a "coroutine was never
    awaited" warning to explain.
    """

    def __init__(self, *, finished: bool = False) -> None:
        self._finished = finished

    def done(self) -> bool:
        return self._finished


@pytest.fixture
def live_task() -> FakeTask:
    return FakeTask()


# --------------------------------------------------------------------------
# Liveness
# --------------------------------------------------------------------------
def test_liveness_ok_while_the_consumer_task_runs(live_task):
    with TestClient(build_app(consumer_task=live_task)) as client:
        response = client.get("/liveness")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_liveness_fails_when_the_consumer_task_has_died():
    """The failure no other signal catches.

    Kubernetes restarting the pod is the correct response: a dead asyncio task
    cannot be revived in place.
    """
    with TestClient(build_app(consumer_task=FakeTask(finished=True))) as client:
        response = client.get("/liveness")

    assert response.status_code == 503
    assert response.json()["reason"] == "consumer_task_not_running"


def test_liveness_stays_ok_while_draining(live_task):
    """During drain the task is finishing on purpose.

    Reporting dead here would have the kubelet SIGKILL a pod that is doing
    exactly what it was asked to do.
    """
    with TestClient(
        build_app(consumer_task=live_task, shutting_down=True)
    ) as client:
        assert client.get("/liveness").status_code == 200


# --------------------------------------------------------------------------
# Readiness
# --------------------------------------------------------------------------
def test_readiness_ok_when_every_dependency_is_up(live_task):
    with TestClient(build_app(consumer_task=live_task)) as client:
        response = client.get("/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {
        "postgres": "ok",
        "redis": "ok",
        "storage": "ok",
        "consumer": "ok",
    }


@pytest.mark.parametrize(
    ("state", "failing"),
    [
        ({"redis": FakeRedisClient(up=False)}, "redis"),
        ({"reader": FakeReader(up=False)}, "storage"),
        ({"consumer": FakeConsumer(running=False)}, "consumer"),
        ({"consumer": FakeConsumer(group=False)}, "consumer"),
    ],
)
def test_readiness_503_when_a_dependency_is_down(live_task, state, failing):
    with TestClient(build_app(consumer_task=live_task, **state)) as client:
        response = client.get("/readiness")

    assert response.status_code == 503
    assert response.json()["checks"][failing] != "ok"


def test_readiness_reports_draining_immediately_on_shutdown(live_task):
    """This is what takes the pod out of the endpoints list before it drains."""
    with TestClient(
        build_app(consumer_task=live_task, shutting_down=True)
    ) as client:
        response = client.get("/readiness")

    assert response.status_code == 503
    assert response.json()["status"] == "draining"


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def test_metrics_exposes_the_queue_depth_series(live_task):
    """Queue depth is the HPA/KEDA signal — its absence would be silent."""
    with TestClient(build_app(consumer_task=live_task)) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "documind_processing_stream_pending" in response.text
    assert "documind_processing_jobs_total" in response.text
