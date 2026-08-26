"""Parsing the stream event into a validated job.

The contract is whatever ``document-service`` publishes today
(``app/services/documents.py``):

    event_version, document_id, storage_key, filename, content_type,
    size_bytes, uploaded_at

Three fields the brief for this worker assumed are **not** in it, and are
handled rather than demanded:

* ``job_id``       — the Redis message id is used instead. Redis assigns it,
                     it is unique and stable across redelivery.
* ``document_type``— produced by ai-service /classify, not supplied by the
                     producer. Nothing upstream knows it at publish time.
* ``user_id``      — there is no auth/user model in M1. Read if present so the
                     producer can start sending it with no change here.

Unknown fields are ignored, which is what makes the contract additive: role 3
can add a field without coordinating a deploy. An unknown ``event_version`` is
the opposite case — guessing at the meaning of a payload shaped differently is
how silent corruption happens — so it is rejected as terminal.
"""

from __future__ import annotations

from app.errors import MalformedJobError
from app.pipeline import JobEvent

SUPPORTED_EVENT_VERSIONS = {"1"}

_REQUIRED = ("document_id", "storage_key")


def parse(message_id: str, fields: dict[str, str], *, attempt: int) -> JobEvent:
    """Validate one stream message. Raises MalformedJobError (terminal)."""
    version = (fields.get("event_version") or "1").strip()
    if version not in SUPPORTED_EVENT_VERSIONS:
        raise MalformedJobError(
            f"Unsupported event_version {version!r}; this worker understands "
            f"{sorted(SUPPORTED_EVENT_VERSIONS)}"
        )

    missing = [key for key in _REQUIRED if not (fields.get(key) or "").strip()]
    if missing:
        raise MalformedJobError(
            f"Event is missing required field(s): {', '.join(missing)}"
        )

    return JobEvent(
        job_id=message_id,
        document_id=fields["document_id"].strip(),
        storage_key=fields["storage_key"].strip(),
        filename=(fields.get("filename") or "").strip(),
        attempt=attempt,
        user_id=(fields.get("user_id") or "").strip() or None,
        uploaded_at=(fields.get("uploaded_at") or "").strip() or None,
        raw=dict(fields),
    )
