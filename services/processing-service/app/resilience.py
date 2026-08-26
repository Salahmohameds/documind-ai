"""Timeout, bounded retry with jittered backoff, and a circuit breaker.

Adapted from ``services/ai-service/app/resilience.py`` — same semantics, same
state machine, same full-jitter backoff, same total-deadline cap. The one real
change is that the retry driver is ``async``: this service runs several jobs
concurrently on one event loop, and a ``time.sleep`` in a backoff would stall
every other in-flight job in the pod, not just the one that failed.

Why the worker needs its own copy rather than importing ai-service's: the two
services are separately built, separately deployed images with no shared
package. Vendoring ~150 lines is the honest cost of that boundary; a shared
library would have to be published and versioned to be worth it.

Circuit breaker states
----------------------
``closed``    — normal. Consecutive failures are counted.
``open``      — threshold reached; calls are rejected immediately without
                touching the dependency. Lasts ``reset_after_s``.
``half_open`` — one trial call is admitted. Success closes the circuit;
                failure re-opens it for another full interval.

Scope: **per pod, in-process, deliberately.** A shared breaker would need a
coordination backend and would make one pod's network problem everybody's
outage. Each replica discovering ai-service is down independently is the
correct behaviour, and it keeps the worker stateless in the sense that matters
— no pod holds data another pod needs.

Why this matters here specifically: when ai-service is unhealthy, a worker
without a breaker sits in per-call timeouts, holding its concurrency slots and
its Redis pending entries. Queue depth climbs, the HPA scales out, and every
new pod parks on the same dead dependency. Failing fast keeps jobs cycling back
onto the stream where a healthy worker can pick them up later.
"""

from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

from app.errors import (
    CircuitOpenError,
    ProcessingError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.metrics import record_circuit_state

logger = logging.getLogger("processing-service")

T = TypeVar("T")

State = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    """Consecutive-failure breaker. Thread-safe."""

    def __init__(
        self,
        name: str,
        threshold: int,
        reset_after_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._name = name
        self._threshold = threshold
        self._reset_after_s = reset_after_s
        # Injected so tests can drive the reset interval deterministically
        # rather than sleeping through it.
        self._clock = clock
        self._failures = 0
        self._opened_at = 0.0
        self._state: State = "closed"
        self._lock = threading.Lock()
        record_circuit_state(self._name, "closed")

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> State:
        with self._lock:
            self._maybe_half_open()
            return self._state

    def _maybe_half_open(self) -> None:
        """Caller must hold the lock."""
        if (
            self._state == "open"
            and (self._clock() - self._opened_at) >= self._reset_after_s
        ):
            self._state = "half_open"
            record_circuit_state(self._name, "half_open")
            logger.info("circuit_half_open", extra={"dependency": self._name})

    def allow(self) -> bool:
        with self._lock:
            self._maybe_half_open()
            return self._state in ("closed", "half_open")

    def record_success(self) -> None:
        with self._lock:
            if self._state != "closed":
                logger.info("circuit_closed", extra={"dependency": self._name})
            self._failures = 0
            self._state = "closed"
            record_circuit_state(self._name, "closed")

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            # A failed trial call in half_open re-opens immediately, without
            # waiting to re-reach the threshold.
            if self._state == "half_open" or self._failures >= self._threshold:
                if self._state != "open":
                    logger.warning(
                        "circuit_opened",
                        extra={"dependency": self._name, "failures": self._failures},
                    )
                self._state = "open"
                self._opened_at = self._clock()
                record_circuit_state(self._name, "open")

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = "closed"
            self._opened_at = 0.0
            record_circuit_state(self._name, "closed")


def backoff_delay(attempt: int, base: float, cap: float) -> float:
    """Exponential backoff with full jitter.

    Full jitter (``uniform(0, computed)``) rather than fixed backoff: when a
    dependency blips, every worker pod fails at the same instant, and identical
    backoff would send them all back in one synchronised wave.
    """
    ceiling = min(cap, base * (2**attempt))
    return random.uniform(0.0, ceiling)


async def call_with_resilience(
    fn: Callable[[], Awaitable[T]],
    *,
    breaker: CircuitBreaker,
    max_retries: int,
    base_delay_s: float,
    max_delay_s: float,
    operation: str = "upstream_call",
    deadline_s: float | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> T:
    """Run ``fn`` under the breaker with bounded retries.

    Only errors flagged ``retryable`` are retried; a 4xx or a malformed payload
    fails immediately rather than burning the retry budget on an outcome that
    cannot change.

    ``deadline_s`` caps the **total** wall clock for the whole call, retries and
    backoff included. Without it the real worst case is
    ``(max_retries + 1) x timeout`` — which for the AI calls is minutes, spent
    holding a concurrency slot and a Redis pending entry. A per-attempt timeout
    alone does not bound a retrying call.
    """
    if not breaker.allow():
        raise CircuitOpenError(
            f"{operation} rejected: circuit for {breaker.name} is open after "
            "repeated failures"
        )

    last_error: Exception | None = None
    call_started = clock()

    def out_of_time() -> bool:
        return deadline_s is not None and (clock() - call_started) >= deadline_s

    for attempt in range(max_retries + 1):
        if attempt and out_of_time():
            logger.warning(
                "upstream_call_deadline_exceeded",
                extra={
                    "dependency": breaker.name,
                    "operation": operation,
                    "attempt": attempt,
                    "deadline_s": deadline_s,
                    "duration_ms": int((clock() - call_started) * 1000),
                },
            )
            break

        started = time.monotonic()
        try:
            result = await fn()
        except ProcessingError as exc:
            last_error = exc
            elapsed_ms = int((time.monotonic() - started) * 1000)
            breaker.record_failure()

            if not exc.retryable:
                logger.warning(
                    "upstream_call_failed",
                    extra={
                        "dependency": breaker.name,
                        "operation": operation,
                        "attempt": attempt,
                        "duration_ms": elapsed_ms,
                        "retryable": False,
                        "error_code": exc.code,
                        "error": str(exc),
                    },
                )
                raise

            if attempt >= max_retries:
                break

            delay = backoff_delay(attempt, base_delay_s, max_delay_s)
            if deadline_s is not None:
                remaining = deadline_s - (clock() - call_started)
                if remaining <= 0:
                    break
                delay = min(delay, remaining)

            logger.warning(
                "upstream_call_retry",
                extra={
                    "dependency": breaker.name,
                    "operation": operation,
                    "attempt": attempt,
                    "duration_ms": elapsed_ms,
                    "retry_in_ms": int(delay * 1000),
                    "error_code": exc.code,
                    "error": str(exc),
                },
            )
            await sleep(delay)
        except asyncio.CancelledError:
            # Shutdown or job timeout. Not a dependency failure — do not let it
            # count towards opening the breaker.
            raise
        except Exception as exc:  # transport errors the client did not wrap
            last_error = UpstreamUnavailableError(str(exc))
            breaker.record_failure()
            if attempt >= max_retries:
                break
            await sleep(backoff_delay(attempt, base_delay_s, max_delay_s))
        else:
            breaker.record_success()
            return result

    if isinstance(last_error, (UpstreamTimeoutError, UpstreamUnavailableError)):
        raise last_error
    raise UpstreamUnavailableError(
        f"{operation} failed after {max_retries + 1} attempt(s): {last_error}"
    )
