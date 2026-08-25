"""Pydantic schemas — the API's external contract.

Every response shape defined here maps 1:1 to the TypeScript types in
``frontend/documind/lib/types.ts``.  Field names use **camelCase** to match
the frontend contract (Pydantic ``model_config.populate_by_name`` +
``alias_generator`` handle the Python ↔ JSON translation).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    """Convert snake_case to camelCase for JSON serialisation."""
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


# ---------------------------------------------------------------------------
# Shared sub-models (match frontend/documind/lib/types.ts exactly)
# ---------------------------------------------------------------------------


class ProgressSchema(BaseModel):
    """``{ step: number; pct: number }``"""

    step: int
    pct: int


class DocErrorSchema(BaseModel):
    """``DocError`` from types.ts."""

    model_config = ConfigDict(
        alias_generator=_to_camel, populate_by_name=True
    )

    code: str
    title: str
    detail: str
    job: str
    at: str
    retryable: bool


class ClassificationSchema(BaseModel):
    """``classification`` block inside ``DocumentDetail``."""

    model_config = ConfigDict(
        alias_generator=_to_camel, populate_by_name=True
    )

    label: str
    subtype: str
    confidence: float
    runner_up: str
    runner_up_confidence: float


class ExtractedFieldSchema(BaseModel):
    """``ExtractedField`` from types.ts."""

    key: str
    value: str
    confidence: float
    page: int


class PiiFindingSchema(BaseModel):
    """``PiiFinding`` from types.ts."""

    id: str
    type: str
    masked: str
    value: str
    page: int


class RiskCategorySchema(BaseModel):
    """``RiskCategory`` from types.ts."""

    name: str
    score: int


class FindingSchema(BaseModel):
    """``Finding`` from types.ts."""

    id: str
    title: str
    severity: Literal["High", "Medium", "Low"]
    description: str
    page: int


# ---------------------------------------------------------------------------
# Document response schemas
# ---------------------------------------------------------------------------


class DocumentSummarySchema(BaseModel):
    """Maps to ``DocumentSummary`` in types.ts.

    Returned by ``GET /documents`` (inside ``rows``) and ``POST /documents``.
    """

    model_config = ConfigDict(
        alias_generator=_to_camel, populate_by_name=True, from_attributes=True
    )

    id: str
    name: str
    ext: str
    type: str
    status: str
    risk: int | None
    pages: int
    size_mb: float = Field(alias="sizeMb")
    counterparty: str
    uploaded: str
    uploaded_at: int = Field(alias="uploadedAt")
    time: str
    flags: int
    verdict: str
    progress: ProgressSchema | None = None
    error: DocErrorSchema | None = None


class DocumentDetailSchema(DocumentSummarySchema):
    """Maps to ``DocumentDetail`` in types.ts (extends ``DocumentSummary``).

    Returned by ``GET /documents/{id}``.
    """

    classification: ClassificationSchema | None = None
    processed_in: str | None = Field(None, alias="processedIn")
    model: str | None = None
    fields: list[ExtractedFieldSchema] = []
    fields_expected: int = Field(0, alias="fieldsExpected")
    pii: list[PiiFindingSchema] = []
    risk_categories: list[RiskCategorySchema] = Field(
        default=[], alias="riskCategories"
    )
    findings: list[FindingSchema] = []
    partial: dict[str, Any] | None = None


class DocumentStatusSchema(BaseModel):
    """Lightweight polling response for ``GET /documents/{id}/status``."""

    model_config = ConfigDict(
        alias_generator=_to_camel, populate_by_name=True
    )

    id: str
    status: str
    risk: int | None
    verdict: str
    progress: ProgressSchema | None = None
    error: DocErrorSchema | None = None


# ---------------------------------------------------------------------------
# List / pagination
# ---------------------------------------------------------------------------


class DocumentPageSchema(BaseModel):
    """Paginated document list — matches the ``DocumentPage`` type in api.ts."""

    model_config = ConfigDict(
        alias_generator=_to_camel, populate_by_name=True
    )

    rows: list[DocumentSummarySchema]
    total: int
    unfiltered_total: int = Field(alias="unfilteredTotal")
    page: int
    page_size: int = Field(alias="pageSize")
    page_count: int = Field(alias="pageCount")


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------


class BulkRequestSchema(BaseModel):
    """Request body for reprocess / delete."""

    ids: list[str]


class BulkFailedItemSchema(BaseModel):
    id: str
    name: str
    reason: str


class BulkResultSchema(BaseModel):
    """Response for bulk reprocess / delete — matches ``BulkResult`` in api.ts."""

    requested: int
    succeeded: list[str]
    failed: list[BulkFailedItemSchema]


# ---------------------------------------------------------------------------
# Error responses
# ---------------------------------------------------------------------------


class ErrorResponseSchema(BaseModel):
    """Standard error envelope returned to clients."""

    error: str
    detail: str
    code: str = "ERR_INTERNAL"
