"""Domain errors translated to stable HTTP responses by the route handlers.

Same shape as services/document-service/app/errors.py: a status code, a stable
machine-readable ``code``, a human ``title`` and a ``retryable`` flag.

``retryable`` is part of the contract with the processing worker (role 5): it
tells the worker whether to re-queue the job or send it straight to the
dead-letter stream. See docs/architecture/ai-service-contract.md.
"""

from __future__ import annotations


class AIServiceError(Exception):
    """Base error with a safe client-facing response."""

    status_code = 500
    code = "ERR_INTERNAL"
    title = "AI service error"
    retryable = False

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ProviderTimeoutError(AIServiceError):
    status_code = 504
    code = "ERR_PROVIDER_TIMEOUT"
    title = "Model provider timed out"
    retryable = True


class ProviderUnavailableError(AIServiceError):
    status_code = 503
    code = "ERR_PROVIDER_UNAVAILABLE"
    title = "Model provider unavailable"
    retryable = True


class CircuitOpenError(AIServiceError):
    status_code = 503
    code = "ERR_CIRCUIT_OPEN"
    title = "Model provider circuit breaker is open"
    retryable = True


class TokenBudgetExceededError(AIServiceError):
    status_code = 413
    code = "ERR_TOKEN_BUDGET_EXCEEDED"
    title = "Request exceeds the per-request token budget"
    # Retrying an oversized payload fails identically - the caller must split it.
    retryable = False


class BatchTooLargeError(AIServiceError):
    status_code = 413
    code = "ERR_BATCH_TOO_LARGE"
    title = "Embedding batch exceeds the configured maximum"
    retryable = False


class ProviderConfigurationError(AIServiceError):
    status_code = 500
    code = "ERR_PROVIDER_MISCONFIGURED"
    title = "Model provider is not configured correctly"
    retryable = False


class PromptNotFoundError(AIServiceError):
    status_code = 500
    code = "ERR_PROMPT_NOT_FOUND"
    title = "Prompt template missing"
    retryable = False


class UnsupportedOperationError(AIServiceError):
    status_code = 501
    code = "ERR_UNSUPPORTED_OPERATION"
    title = "Operation not supported by the active provider"
    retryable = False
