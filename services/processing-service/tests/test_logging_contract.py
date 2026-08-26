"""Structured-logging fields must not collide with LogRecord's own attributes.

`logging` raises ``KeyError: Attempt to overwrite 'filename' in LogRecord``
when an ``extra`` key shadows a built-in record attribute. It is an easy
mistake — ``filename``, ``module``, ``process`` and ``name`` are all natural
names for things a document worker logs — and it fails at *emit* time, inside
whatever code path happened to log, not at import.

That makes it exactly the wrong shape of bug to leave to runtime discovery: it
took down a job on the first real document processed through this service. A
static scan of every ``extra={...}`` in the package costs milliseconds and
covers log lines that no test happens to exercise.
"""

from __future__ import annotations

import ast
import logging
import pathlib

APP_ROOT = pathlib.Path(__file__).resolve().parents[1] / "app"

# The attributes logging puts on every record, plus the two the Formatter adds.
RESERVED = set(
    logging.LogRecord("n", logging.INFO, "p", 1, "m", None, None).__dict__
) | {"message", "asctime", "taskName"}


def _extra_keys() -> list[tuple[str, int, str]]:
    """Every literal key passed as ``extra=`` anywhere in the package."""
    keys: list[tuple[str, int, str]] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg == "extra" and isinstance(keyword.value, ast.Dict):
                    for key in keyword.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            keys.append(
                                (path.relative_to(APP_ROOT.parent).as_posix(),
                                 key.lineno,
                                 key.value)
                            )
    return keys


def test_no_log_extra_shadows_a_logrecord_attribute():
    collisions = [entry for entry in _extra_keys() if entry[2] in RESERVED]
    assert not collisions, (
        "These log calls would raise KeyError at emit time. Rename the field "
        "(e.g. 'filename' -> 'document_filename'):\n"
        + "\n".join(f"  {f}:{line} -> extra={{{key!r}: ...}}" for f, line, key in collisions)
    )


def test_the_scan_actually_finds_log_fields():
    """Guards the guard: a broken scan would pass the test above vacuously."""
    assert len(_extra_keys()) > 50
