"""Error taxonomy for the worker.

The only distinction that matters to the consumer is **retryable vs terminal**,
because it decides whether a message is acked or left pending for another
worker to reclaim:

* *retryable*   — the job might succeed later (dependency down, timeout, 5xx).
  Left un-acked so Redis redelivers it to whoever claims it next.
* *terminal*    — the job will never succeed (not a PDF, no text layer, 4xx).
  Acked immediately and recorded FAILED. Retrying it would burn the attempt
  budget on an outcome that cannot change, and in aggregate would keep a
  poison message circulating forever.
"""

from __future__ import annotations


class ProcessingError(Exception):
    """Base error. ``code`` is what lands in ``processing_jobs.error_code``."""

    code = "ERR_PROCESSING"
    retryable = False

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


# --------------------------------------------------------------------------
# Terminal — the job cannot succeed on a later attempt.
# --------------------------------------------------------------------------
class MalformedJobError(ProcessingError):
    """The stream message is missing required fields or has an unknown version."""

    code = "ERR_MALFORMED_JOB"


class DocumentNotFoundError(ProcessingError):
    """The object named by ``storage_key`` does not exist."""

    code = "ERR_DOCUMENT_NOT_FOUND"


class DocumentTooLargeError(ProcessingError):
    code = "ERR_DOCUMENT_TOO_LARGE"


class InvalidDocumentError(ProcessingError):
    """Not a readable PDF."""

    code = "ERR_INVALID_DOCUMENT"


class NoTextLayerError(ProcessingError):
    """A scanned, image-only PDF.

    OCR is out of scope for this platform (no tesseract in the image, and no
    OCI Vision integration), so this is an honest terminal outcome rather than
    a job that retries three times and fails anyway.
    """

    code = "ERR_NO_TEXT_LAYER"


class UpstreamRejectedError(ProcessingError):
    """A downstream service returned 4xx — our request was wrong, not its state."""

    code = "ERR_UPSTREAM_REJECTED"


# --------------------------------------------------------------------------
# Retryable — a later attempt may well succeed.
# --------------------------------------------------------------------------
class RetryableProcessingError(ProcessingError):
    retryable = True


class StorageUnavailableError(RetryableProcessingError):
    code = "ERR_STORAGE_UNAVAILABLE"


class UpstreamUnavailableError(RetryableProcessingError):
    """Transport failure or 5xx from ai-service / search-service."""

    code = "ERR_UPSTREAM_UNAVAILABLE"


class UpstreamTimeoutError(RetryableProcessingError):
    code = "ERR_UPSTREAM_TIMEOUT"


class CircuitOpenError(RetryableProcessingError):
    """Rejected without a call because the dependency is known to be failing."""

    code = "ERR_CIRCUIT_OPEN"


class JobTimeoutError(RetryableProcessingError):
    """The whole pipeline exceeded ``job_timeout_s``."""

    code = "ERR_JOB_TIMEOUT"
