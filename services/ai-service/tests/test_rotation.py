"""Model rotation under rate limits.

Driven by a real incident: on 2026-08-26 the evaluation harness was cut off by
HTTP 429 after 12 questions against Google AI Studio's free tier, with 16 still
to run. Rate limits are per model, so rotating buys headroom that retrying the
same model cannot.
"""

from __future__ import annotations

import pytest

from app.adapters.rotation import ModelRotation
from app.config import Settings


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_preferred_model_is_first():
    rotation = ModelRotation(["a", "b", "c"])
    assert rotation.candidates()[0] == "a"


def test_limited_model_is_skipped():
    rotation = ModelRotation(["a", "b", "c"], cooldown_s=60, clock=FakeClock())
    rotation.mark_limited("a")

    assert rotation.candidates() == ["b", "c"]


def test_model_returns_after_the_cooldown():
    clock = FakeClock()
    rotation = ModelRotation(["a", "b"], cooldown_s=60, clock=clock)
    rotation.mark_limited("a")
    assert rotation.candidates() == ["b"]

    clock.advance(61)
    assert rotation.candidates() == ["a", "b"]


def test_all_limited_falls_back_to_the_full_list():
    """A stale cooldown must never become a hard outage.

    The provider is the authority on whether a limit has lifted, so when every
    model is parked we try them all rather than refusing locally.
    """
    rotation = ModelRotation(["a", "b"], cooldown_s=60, clock=FakeClock())
    rotation.mark_limited("a")
    rotation.mark_limited("b")

    assert rotation.candidates() == ["a", "b"]
    assert rotation.available() == []


def test_clear_returns_a_model_early():
    rotation = ModelRotation(["a", "b"], cooldown_s=60, clock=FakeClock())
    rotation.mark_limited("a")
    rotation.clear("a")

    assert rotation.candidates() == ["a", "b"]


def test_duplicates_and_blanks_are_dropped():
    rotation = ModelRotation(["a", " a ", "", "b", "a"])
    assert rotation.models == ["a", "b"]


def test_empty_rotation_is_rejected():
    with pytest.raises(ValueError):
        ModelRotation([])


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
def test_model_chain_puts_the_primary_first(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "primary")
    monkeypatch.setenv("MODEL_FALLBACKS", "second,third")

    assert Settings().model_chain() == ["primary", "second", "third"]


def test_model_chain_without_fallbacks_is_just_the_primary(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "only")
    monkeypatch.setenv("MODEL_FALLBACKS", "")

    assert Settings().model_chain() == ["only"]


def test_model_chain_ignores_empty_entries(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "primary")
    monkeypatch.setenv("MODEL_FALLBACKS", "a,,  ,b")

    assert Settings().model_chain() == ["primary", "a", "b"]


# --------------------------------------------------------------------------
# Error semantics
# --------------------------------------------------------------------------
def test_rate_limited_error_is_retryable_and_distinct():
    """The worker needs to tell 'no quota' apart from 'provider is broken'.

    Both are retryable, but exhausted quota only recovers with time, so the
    worker should back off generously rather than re-queue immediately.
    """
    from app.errors import ProviderRateLimitedError, ProviderUnavailableError

    assert ProviderRateLimitedError.status_code == 429
    assert ProviderRateLimitedError.retryable is True
    assert ProviderRateLimitedError.code != ProviderUnavailableError.code
