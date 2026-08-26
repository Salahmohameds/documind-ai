"""Pydantic request/response models - the wire contract for ai-service.

This module IS the contract. docs/architecture/ai-service-contract.md is the
prose version of it; if the two ever disagree, this file wins and the doc is
the bug.

Two boundaries are deliberate:

* ai-service does **no retrieval**. ``/answer`` receives the chunks that
  search-service (role 6) already retrieved. Retrieval quality is role 6's
  metric; answer quality is role 4's.
* ai-service does **no chunking and no storage**. It converts text to vectors
  on request and forgets them.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DocumentType = Literal["invoice", "contract", "receipt", "report", "unknown"]
RiskBand = Literal["low", "medium", "high"]
Severity = Literal["low", "medium", "high"]


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------
class Usage(BaseModel):
    """Token accounting. Mirrors what the provider reports, estimated for mock."""

    tokens_in: int = 0
    tokens_out: int = 0
    estimated: bool = False


class ResponseMeta(BaseModel):
    """Attached to every successful response so callers can attribute cost.

    ``degraded`` is true when the answer was produced without a healthy model
    call (circuit open, provider error absorbed by a local fallback). The
    processing worker uses it to flag a job as completed-with-caveats rather
    than silently trusting the output.
    """

    provider: str
    model: str
    duration_ms: int
    usage: Usage
    request_id: str | None = None
    degraded: bool = False
    redacted: bool = False


class ErrorResponse(BaseModel):
    """Stable error envelope - identical shape across every endpoint."""

    code: str
    title: str
    detail: str
    retryable: bool
    request_id: str | None = None


class Evidence(BaseModel):
    """Where in the source document a value or finding came from."""

    snippet: str
    offset: int | None = None
    page: int | None = None


# --------------------------------------------------------------------------
# /embed
# --------------------------------------------------------------------------
class EmbedRequest(BaseModel):
    """Batch-first by design.

    A 40-page contract is hundreds of chunks; a one-string-per-call endpoint
    would put a network round-trip on the highest-volume path in the platform.
    """

    texts: list[str] = Field(min_length=1)
    # Cohere-family models embed documents and queries into different spaces.
    # search-service passes 'document' when indexing and 'query' when searching.
    input_type: Literal["document", "query"] = "document"
    request_id: str | None = None


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dim: int
    count: int
    meta: ResponseMeta


# --------------------------------------------------------------------------
# /classify
# --------------------------------------------------------------------------
class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1)
    document_id: str | None = None
    request_id: str | None = None


class ClassifyResponse(BaseModel):
    document_id: str | None = None
    label: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    scores: dict[str, float]
    rationale: str
    meta: ResponseMeta


# --------------------------------------------------------------------------
# /extract
# --------------------------------------------------------------------------
class ExtractedField(BaseModel):
    value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Evidence | None = None


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1)
    document_id: str | None = None
    # When omitted the service classifies first, then extracts the field set
    # appropriate to the detected type.
    document_type: DocumentType | None = None
    fields: list[str] | None = None
    request_id: str | None = None


class ExtractResponse(BaseModel):
    document_id: str | None = None
    document_type: DocumentType
    fields: dict[str, ExtractedField]
    meta: ResponseMeta


# --------------------------------------------------------------------------
# /analysis/risk
# --------------------------------------------------------------------------
class RiskFinding(BaseModel):
    """One deterministic rule that fired, with the text that triggered it."""

    rule_id: str
    title: str
    severity: Severity
    weight: int
    evidence: Evidence | None = None


class RiskScoring(BaseModel):
    """Makes the score auditable.

    The number is produced by deterministic rules, NOT by asking a model for a
    score. That is the difference between a figure a reviewer can check and a
    figure nobody can defend. The model only writes ``explanation``.
    """

    method: Literal["deterministic-rules"] = "deterministic-rules"
    rules_version: str
    points_scored: int
    points_possible: int
    rules_evaluated: int
    rules_fired: int


class RiskRequest(BaseModel):
    text: str = Field(min_length=1)
    document_id: str | None = None
    document_type: DocumentType | None = None
    # Skip the narrative when the caller only wants the number (load tests).
    explain: bool = True
    request_id: str | None = None


class RiskResponse(BaseModel):
    document_id: str | None = None
    score: int = Field(ge=0, le=100)
    band: RiskBand
    findings: list[RiskFinding]
    explanation: str
    scoring: RiskScoring
    meta: ResponseMeta


# --------------------------------------------------------------------------
# /answer  (RAG generation)
# --------------------------------------------------------------------------
class ContextChunk(BaseModel):
    """A chunk retrieved by search-service. ai-service never fetches these."""

    chunk_id: str
    text: str = Field(min_length=1)
    document_id: str | None = None
    page: int | None = None
    score: float | None = None


class Citation(BaseModel):
    chunk_id: str
    document_id: str | None = None
    page: int | None = None
    snippet: str


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    chunks: list[ContextChunk] = Field(default_factory=list)
    request_id: str | None = None


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    # False when the context did not support an answer. An honest refusal is a
    # correct outcome, and the evaluation harness scores it as one.
    grounded: bool
    refused: bool
    confidence: float = Field(ge=0.0, le=1.0)
    meta: ResponseMeta


# --------------------------------------------------------------------------
# /pii
# --------------------------------------------------------------------------
class PIIMatch(BaseModel):
    type: str
    placeholder: str
    start: int
    end: int
    # The raw value is returned ONLY when the caller explicitly asks. Default
    # off so a debug call cannot casually log personal data.
    value: str | None = None


class PIIRequest(BaseModel):
    text: str = Field(min_length=1)
    document_id: str | None = None
    return_redacted_text: bool = True
    include_values: bool = False
    request_id: str | None = None


class PIIResponse(BaseModel):
    document_id: str | None = None
    matches: list[PIIMatch]
    counts: dict[str, int]
    redacted_text: str | None = None


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------
class LivenessResponse(BaseModel):
    status: str
    service: str


class ReadinessResponse(BaseModel):
    status: str
    service: str
    provider: str
    checks: dict[str, Any]
