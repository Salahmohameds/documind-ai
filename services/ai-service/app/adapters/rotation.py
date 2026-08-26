"""Model rotation with per-model cooldown.

Why this exists
---------------
Measured against Google AI Studio's free tier on 2026-08-26: the evaluation
harness sent 12 questions in ~10 seconds and was rate-limited (HTTP 429) with
16 questions still to go. The dashboard confirmed it - ``18 / 15`` requests per
minute on Gemini 3.5 Flash Lite.

Retrying the *same* model harder does not help: the limit is per model, and
backing off just makes the run slower before it fails anyway. Rotating to a
different model does help, because each model carries its own quota.

Observed free-tier limits (Google AI Studio, 2026-08-26):

    Gemini 3.5 Flash Lite    15 RPM    500 RPD
    Gemini 3.1 Flash Lite    15 RPM    500 RPD
    Gemini 3.7 Flash          5 RPM     20 RPD
    Gemini 3 Flash            5 RPM     20 RPD

So two Flash-Lite models together give 30 RPM and 1000 RPD - double the
headroom for one config line. The Flash models are near-useless as fallbacks at
20 requests per *day*, but they are worth having as a last resort.

This is a free-tier workaround, not an architecture. It buys enough headroom to
run an evaluation; it will not survive a k6 load test, and that remains the
strongest practical argument for the OCI path (ADR-006).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class ModelRotation:
    """Ordered model list where a rate-limited model is skipped for a while.

    Thread-safe: FastAPI serves sync routes from a worker threadpool, so several
    requests can discover the same 429 at once.
    """

    def __init__(
        self,
        models: list[str],
        cooldown_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not models:
            raise ValueError("ModelRotation needs at least one model")
        # Preserve order, drop duplicates and blanks.
        seen: set[str] = set()
        self._models: list[str] = []
        for model in models:
            name = model.strip()
            if name and name not in seen:
                seen.add(name)
                self._models.append(name)

        self._cooldown_s = cooldown_s
        self._clock = clock
        self._blocked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def models(self) -> list[str]:
        return list(self._models)

    def available(self) -> list[str]:
        """Models not currently in cooldown, in preference order."""
        now = self._clock()
        with self._lock:
            return [m for m in self._models if self._blocked_until.get(m, 0.0) <= now]

    def candidates(self) -> list[str]:
        """Models to try, best first.

        If every model is cooling down we still return the full list rather than
        nothing: a stale cooldown must never turn into a hard outage, and the
        provider is the authority on whether the limit has actually lifted.
        """
        available = self.available()
        return available or list(self._models)

    def mark_limited(self, model: str) -> None:
        """Take ``model`` out of rotation for the cooldown period."""
        with self._lock:
            self._blocked_until[model] = self._clock() + self._cooldown_s

    def clear(self, model: str) -> None:
        """Return a model to rotation early - e.g. after a success."""
        with self._lock:
            self._blocked_until.pop(model, None)

    def reset(self) -> None:
        with self._lock:
            self._blocked_until.clear()
