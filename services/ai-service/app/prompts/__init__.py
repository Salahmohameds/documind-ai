"""Prompt loading.

Prompts are **files, not string literals**. In Kubernetes ``PROMPTS_DIR`` points
at a mounted ConfigMap, so changing a prompt is a ``kubectl apply`` and a pod
restart - not an image rebuild, a Trivy scan, an OCIR push and a rollout. That
is the difference between iterating on prompts in an afternoon and iterating on
them once.

Placeholders use ``{{name}}`` rather than ``str.format``: contracts are full of
``$`` amounts and the model is asked to emit JSON, so both ``{}`` and ``$``
have to survive substitution untouched.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path

from app.config import settings
from app.errors import PromptNotFoundError

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")

_cache: dict[str, str] = {}
_lock = threading.Lock()


def load(name: str) -> str:
    """Read ``<PROMPTS_DIR>/<name>.txt``, cached unless caching is disabled."""
    if settings.prompt_cache_enabled:
        cached = _cache.get(name)
        if cached is not None:
            return cached

    path = Path(settings.prompts_dir) / f"{name}.txt"
    if not path.is_file():
        raise PromptNotFoundError(
            f"Prompt '{name}' not found at {path}. In Kubernetes this means the "
            "prompts ConfigMap is not mounted at PROMPTS_DIR."
        )

    text = path.read_text(encoding="utf-8")
    if settings.prompt_cache_enabled:
        with _lock:
            _cache[name] = text
    return text


def render(name: str, **values: object) -> str:
    """Load a prompt and substitute ``{{placeholders}}``.

    An unknown placeholder is left in place rather than raising: a prompt edited
    through the ConfigMap should never be able to take the service down.
    """
    template = load(name)

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(values[key]) if key in values else match.group(0)

    return _PLACEHOLDER.sub(replace, template)


def clear_cache() -> None:
    """Drop cached prompts. Used by tests and by a future SIGHUP reload."""
    with _lock:
        _cache.clear()
