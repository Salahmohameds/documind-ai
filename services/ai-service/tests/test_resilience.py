"""Timeout, retry and circuit-breaker behaviour.

If this service hangs, the processing workers block, queue depth drives the HPA
into scaling workers that are all stuck on the same dead dependency, and the
demo stalls. Failing fast is the feature being tested here.
"""

from __future__ import annotations

import time

import pytest

from app.errors import (
    CircuitOpenError,
    ProviderConfigurationError,
    ProviderUnavailableError,
)
from app.resilience import CircuitBreaker, backoff_delay, call_with_resilience


def _no_sleep(_seconds: float) -> None:
    """Retries are tested for behaviour, not for wall-clock patience."""


def _run(fn, breaker, retries=2):
    return call_with_resilience(
        fn,
        breaker=breaker,
        max_retries=retries,
        base_delay_s=0.01,
        max_delay_s=0.02,
        timeout_s=1.0,
        operation="test",
        sleep=_no_sleep,
    )


def test_success_passes_straight_through():
    breaker = CircuitBreaker(threshold=3, reset_after_s=60)
    assert _run(lambda: "ok", breaker) == "ok"
    assert breaker.state == "closed"


def test_retryable_error_is_retried_then_succeeds():
    breaker = CircuitBreaker(threshold=10, reset_after_s=60)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ProviderUnavailableError("temporary")
        return "recovered"

    assert _run(flaky, breaker) == "recovered"
    assert calls["n"] == 3


def test_non_retryable_error_is_not_retried():
    """A misconfiguration fails identically on every attempt.

    Burning the retry budget on it just delays the error the operator needs.
    """
    breaker = CircuitBreaker(threshold=10, reset_after_s=60)
    calls = {"n": 0}

    def misconfigured():
        calls["n"] += 1
        raise ProviderConfigurationError("bad region")

    with pytest.raises(ProviderConfigurationError):
        _run(misconfigured, breaker)

    assert calls["n"] == 1


def test_retries_are_bounded():
    breaker = CircuitBreaker(threshold=100, reset_after_s=60)
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ProviderUnavailableError("down")

    with pytest.raises(ProviderUnavailableError):
        _run(always_fails, breaker, retries=2)

    assert calls["n"] == 3  # the initial attempt plus two retries


def test_circuit_opens_after_the_threshold():
    breaker = CircuitBreaker(threshold=3, reset_after_s=60)
    for _ in range(3):
        breaker.record_failure()

    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        _run(lambda: "never runs", breaker)


def test_open_circuit_rejects_without_calling_the_provider():
    """The whole point: stop hammering a dependency that is already down."""
    breaker = CircuitBreaker(threshold=1, reset_after_s=60)
    breaker.record_failure()
    calls = {"n": 0}

    def provider():
        calls["n"] += 1
        return "ok"

    with pytest.raises(CircuitOpenError):
        _run(provider, breaker)

    assert calls["n"] == 0


class FakeClock:
    """Drives the reset interval without sleeping through it."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_circuit_stays_open_for_the_whole_reset_interval():
    clock = FakeClock()
    breaker = CircuitBreaker(threshold=2, reset_after_s=30.0, clock=clock)
    breaker.record_failure()
    breaker.record_failure()

    assert breaker.state == "open"
    clock.advance(29.0)
    assert breaker.state == "open"


def test_circuit_half_opens_after_the_reset_interval():
    clock = FakeClock()
    breaker = CircuitBreaker(threshold=2, reset_after_s=30.0, clock=clock)
    breaker.record_failure()
    breaker.record_failure()

    clock.advance(31.0)
    assert breaker.state == "half_open"


def test_success_in_half_open_closes_the_circuit():
    clock = FakeClock()
    breaker = CircuitBreaker(threshold=2, reset_after_s=30.0, clock=clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(31.0)

    assert _run(lambda: "ok", breaker) == "ok"
    assert breaker.state == "closed"


def test_failed_trial_call_reopens_for_another_full_interval():
    """Recovery must be proven, not assumed after one interval of silence."""
    clock = FakeClock()
    breaker = CircuitBreaker(threshold=2, reset_after_s=30.0, clock=clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(31.0)
    assert breaker.state == "half_open"

    def still_down():
        raise ProviderUnavailableError("down")

    with pytest.raises(ProviderUnavailableError):
        _run(still_down, breaker, retries=0)

    assert breaker.state == "open"
    clock.advance(29.0)
    assert breaker.state == "open"


def test_success_resets_the_failure_count():
    breaker = CircuitBreaker(threshold=3, reset_after_s=60)
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    breaker.record_failure()

    assert breaker.state == "closed"


def test_backoff_is_bounded_and_jittered():
    """Full jitter: identical backoff would resend every pod in one wave."""
    delays = [backoff_delay(attempt=3, base=0.5, cap=8.0) for _ in range(50)]

    assert all(0.0 <= d <= 8.0 for d in delays)
    assert len(set(delays)) > 1  # not a constant


def test_backoff_grows_with_attempt_number():
    ceilings = [max(backoff_delay(n, base=0.5, cap=100.0) for _ in range(200)) for n in (0, 4)]
    assert ceilings[1] > ceilings[0]


# --------------------------------------------------------------------------
# Total deadline
# --------------------------------------------------------------------------
def test_deadline_stops_retrying_even_with_budget_left():
    """Regression, measured 2026-08-26.

    A single /answer took 241 seconds: max_retries=3 with a 60 s socket timeout
    is a four-minute worst case, and a per-attempt timeout does not bound a
    retrying call. That blocks a worker thread and backs the queue up behind it.
    """
    breaker = CircuitBreaker(threshold=100, reset_after_s=60)
    clock = FakeClock()
    calls = {"n": 0}

    def slow_and_failing():
        calls["n"] += 1
        clock.advance(20.0)  # each attempt burns 20 s
        raise ProviderUnavailableError("slow")

    with pytest.raises(ProviderUnavailableError):
        call_with_resilience(
            slow_and_failing,
            breaker=breaker,
            max_retries=10,
            base_delay_s=0.01,
            max_delay_s=0.02,
            timeout_s=20.0,
            deadline_s=45.0,
            operation="test",
            sleep=_no_sleep,
            clock=clock,
        )

    # 20 s + 20 s puts the clock at 40 s (still inside the 45 s budget, so a
    # third attempt starts), and that attempt ends at 60 s. The fourth is
    # refused. Without the deadline this would have run all 11 attempts and
    # burned 220 seconds.
    assert calls["n"] == 3


def test_no_deadline_keeps_the_old_behaviour():
    """deadline_s is optional - omitting it must not change anything."""
    breaker = CircuitBreaker(threshold=100, reset_after_s=60)
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ProviderUnavailableError("down")

    with pytest.raises(ProviderUnavailableError):
        call_with_resilience(
            always_fails,
            breaker=breaker,
            max_retries=2,
            base_delay_s=0.01,
            max_delay_s=0.02,
            timeout_s=1.0,
            operation="test",
            sleep=_no_sleep,
        )

    assert calls["n"] == 3


def test_deadline_already_exceeded_stops_after_one_attempt():
    breaker = CircuitBreaker(threshold=100, reset_after_s=60)
    calls = {"n": 0}

    def slow_failure():
        calls["n"] += 1
        time.sleep(0.05)
        raise ProviderUnavailableError("slow")

    with pytest.raises(ProviderUnavailableError):
        call_with_resilience(
            slow_failure,
            breaker=breaker,
            max_retries=5,
            base_delay_s=0.001,
            max_delay_s=0.002,
            timeout_s=1.0,
            deadline_s=0.01,  # already blown by the first attempt
            operation="test",
            sleep=_no_sleep,
        )

    assert calls["n"] == 1
