"""Timeout, bounded retry with jittered backoff, and a circuit breaker.

Why this matters more than the prompts
--------------------------------------
ai-service sits in the middle of the async pipeline. If it hangs, the
processing workers block, the Redis stream backs up, queue depth drives the HPA
into scaling workers that are all stuck on the same dead dependency, and the
demo stalls in the most visible way possible. Failing fast is a feature.

Circuit breaker states
----------------------
``closed``    - normal. Consecutive failures are counted.
``open``      - threshold reached; calls are rejected immediately without
                touching the provider. Lasts ``circuit_breaker_reset_s``.
``half_open`` - one trial call is admitted. Success closes the circuit;
                failure re-opens it for another full interval.

Scope: **per pod, in-process, deliberately.** A shared breaker would need a
coordination backend and would make one pod's network problem everybody's
outage. Each replica discovering the provider is down independently is the
correct behaviour, and it keeps the service stateless in the sense that
matters - no pod holds data another pod needs, and `kubectl delete pod` costs
nothing but a re-probe.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable
from typing import Literal, TypeVar

from app.errors import AIServiceError, CircuitOpenError, ProviderTimeoutError, ProviderUnavailableError

logger = logging.getLogger("ai-service")

T = TypeVar("T")

State = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    """Consecutive-failure breaker. Thread-safe."""

    def __init__(
        self,
        threshold: int,
        reset_after_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._threshold = threshold
        self._reset_after_s = reset_after_s
        # Injected so tests can drive the reset interval deterministically
        # rather than sleeping through it.
        self._clock = clock
        self._failures = 0
        self._opened_at = 0.0
        self._state: State = "closed"
        self._lock = threading.Lock()

    @property
    def state(self) -> State:
        with self._lock:
            self._maybe_half_open()
            return self._state

    def _maybe_half_open(self) -> None:
        """Caller must hold the lock."""
        if self._state == "open" and (self._clock() - self._opened_at) >= self._reset_after_s:
            self._state = "half_open"
            logger.info("circuit_half_open", extra={"event": "circuit_half_open"})

    def allow(self) -> bool:
        with self._lock:
            self._maybe_half_open()
            return self._state in ("closed", "half_open")

    def record_success(self) -> None:
        with self._lock:
            if self._state != "closed":
                logger.info("circuit_closed", extra={"event": "circuit_closed"})
            self._failures = 0
            self._state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            # A failed trial call in half_open re-opens immediately, without
            # waiting to re-reach the threshold.
            if self._state == "half_open" or self._failures >= self._threshold:
                if self._state != "open":
                    logger.warning(
                        "circuit_opened",
                        extra={"event": "circuit_opened", "failures": self._failures},
                    )
                self._state = "open"
                self._opened_at = self._clock()

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = "closed"
            self._opened_at = 0.0


def backoff_delay(attempt: int, base: float, cap: float) -> float:
    """Exponential backoff with full jitter.

    Full jitter (``uniform(0, computed)``) rather than fixed backoff: when a
    provider blips, every worker pod fails at the same instant, and identical
    backoff would send them all back in one synchronised wave.
    """
    ceiling = min(cap, base * (2**attempt))
    return random.uniform(0.0, ceiling)


def call_with_resilience(
    fn: Callable[[], T],
    *,
    breaker: CircuitBreaker,
    max_retries: int,
    base_delay_s: float,
    max_delay_s: float,
    timeout_s: float,
    operation: str = "provider_call",
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run ``fn`` under the breaker with bounded retries.

    Only errors flagged ``retryable`` are retried; a misconfiguration or an
    oversized payload fails immediately rather than burning the retry budget on
    an outcome that cannot change.

    Note on ``timeout_s``: the provider clients are constructed with this same
    value as their socket timeout, which is where enforcement actually happens.
    It is passed here to be logged, so a slow call and a hard timeout are
    distinguishable in the logs.
    """
    if not breaker.allow():
        raise CircuitOpenError(
            f"{operation} rejected: circuit is open after repeated provider failures"
        )

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        started = time.monotonic()
        try:
            result = fn()
        except AIServiceError as exc:
            last_error = exc
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if not exc.retryable:
                breaker.record_failure()
                logger.warning(
                    "provider_call_failed",
                    extra={
                        "event": "provider_call_failed",
                        "operation": operation,
                        "attempt": attempt,
                        "duration_ms": elapsed_ms,
                        "retryable": False,
                        "error": str(exc),
                    },
                )
                raise
            breaker.record_failure()
            if attempt >= max_retries:
                break
            delay = backoff_delay(attempt, base_delay_s, max_delay_s)
            logger.warning(
                "provider_call_retry",
                extra={
                    "event": "provider_call_retry",
                    "operation": operation,
                    "attempt": attempt,
                    "duration_ms": elapsed_ms,
                    "retry_in_ms": int(delay * 1000),
                    "timeout_s": timeout_s,
                    "error": str(exc),
                },
            )
            sleep(delay)
        except Exception as exc:  # transport errors the adapter did not wrap
            last_error = ProviderUnavailableError(str(exc))
            breaker.record_failure()
            if attempt >= max_retries:
                break
            sleep(backoff_delay(attempt, base_delay_s, max_delay_s))
        else:
            breaker.record_success()
            return result

    if isinstance(last_error, (ProviderTimeoutError, ProviderUnavailableError)):
        raise last_error
    raise ProviderUnavailableError(
        f"{operation} failed after {max_retries + 1} attempt(s): {last_error}"
    )
