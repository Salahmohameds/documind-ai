"""Domain errors translated to stable HTTP responses by the document routes."""

from __future__ import annotations


class DocumentServiceError(Exception):
    """Base error with a safe client-facing response."""

    status_code = 500
    code = "ERR_INTERNAL"
    title = "Document service error"
    retryable = False

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidDocumentError(DocumentServiceError):
    status_code = 415
    code = "ERR_UNSUPPORTED_DOCUMENT"
    title = "Unsupported document"


class UploadTooLargeError(DocumentServiceError):
    status_code = 413
    code = "ERR_UPLOAD_TOO_LARGE"
    title = "Upload exceeds the size limit"


class QueueUnavailableError(DocumentServiceError):
    status_code = 503
    code = "ERR_QUEUE_UNAVAILABLE"
    title = "Document queued unsuccessfully"
    retryable = True


class DocumentNotFoundError(DocumentServiceError):
    status_code = 404
    code = "ERR_DOCUMENT_NOT_FOUND"
    title = "Document not found"
