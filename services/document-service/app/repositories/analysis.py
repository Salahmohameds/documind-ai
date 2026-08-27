"""Read access to the analysis processing-service writes.

The pipeline classifies, extracts, summarises, scores and indexes every
document, and stores the results in `extracted_fields`, `risk_assessments` and
`document_summaries`. Until now nothing read them back, so a fully processed
document still answered `GET /documents/{id}` with `risk: null`, `fields: []`
and no findings — the analysis existed but never reached anyone.

Read-only by design. This service owns the `documents` row; these three tables
belong to processing-service and are only ever selected from here.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentSummary, ExtractedFields, RiskAssessment
from app.schemas import (
    ExtractedFieldSchema,
    FindingSchema,
    RiskCategorySchema,
)

# ai-service reports per-category risk as a band, derived from which rules
# fired rather than asked of a model, so there is no numeric truth stored. The
# frontend renders a number and derives its own label from it with thresholds
# at 33 and 66 — these are the midpoints of those ranges, chosen so the label
# the UI derives always matches the band it came from. The band travels
# alongside so the UI can show the real value rather than the stand-in.
_BAND_SCORE = {"Low": 17, "Medium": 50, "High": 84}

# Order matters: it is the order the categories appear in the UI.
_CATEGORIES = ("financial", "legal", "operational")

_SEVERITY = {"low": "Low", "medium": "Medium", "high": "High"}


class AnalysisRepository:
    """Selects the pipeline's output for one document."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # -- extraction --------------------------------------------------------

    def extracted_fields(
        self, document_id: str
    ) -> tuple[list[ExtractedFieldSchema], int]:
        """Return the fields that were found, and how many were looked for.

        ai-service reports every field in the document type's schema, including
        the ones it could not find — those carry `value: null`. Only the found
        ones are returned; the total is the count the UI shows as "n of m
        fields extracted", which is the only thing the misses are useful for.
        """
        row = self._db.get(ExtractedFields, document_id)
        if row is None or not isinstance(row.fields, dict):
            return [], 0

        found: list[ExtractedFieldSchema] = []
        for key, raw in row.fields.items():
            if not isinstance(raw, dict):
                continue
            value = raw.get("value")
            if value in (None, ""):
                continue
            evidence = raw.get("evidence") or {}
            found.append(
                ExtractedFieldSchema(
                    key=key,
                    value=str(value),
                    confidence=_as_float(raw.get("confidence")),
                    # Page is null whenever the extractor worked from the
                    # document's full text rather than a located span. The UI
                    # links a field to a page, so 1 is the honest fallback for
                    # a single-page read.
                    page=_as_int(evidence.get("page"), default=1),
                )
            )

        found.sort(key=lambda f: f.key)
        return found, len(row.fields)

    # -- risk --------------------------------------------------------------

    def risk(self, document_id: str) -> RiskAssessment | None:
        return self._db.get(RiskAssessment, document_id)

    @staticmethod
    def risk_categories(row: RiskAssessment | None) -> list[RiskCategorySchema]:
        if row is None:
            return []

        bands = {
            "financial": row.financial_risk,
            "legal": row.legal_risk,
            "operational": row.operational_risk,
        }

        categories: list[RiskCategorySchema] = []
        for name in _CATEGORIES:
            band = bands.get(name)
            if band is None:
                continue
            categories.append(
                RiskCategorySchema(
                    name=name.capitalize(),
                    score=_BAND_SCORE.get(band, 0),
                    band=band,
                )
            )
        return categories

    @staticmethod
    def findings(row: RiskAssessment | None) -> list[FindingSchema]:
        """The rules that fired, as the UI's findings list.

        Each entry is a rule from ai-service's risk rule set — it carries the
        rule id, what it matched and the text that triggered it, which is why
        the snippet is used as the description rather than a generated one.
        """
        if row is None or not isinstance(row.risk_reasons, list):
            return []

        findings: list[FindingSchema] = []
        for index, raw in enumerate(row.risk_reasons, start=1):
            if not isinstance(raw, dict):
                continue
            evidence = raw.get("evidence") or {}
            snippet = evidence.get("snippet")
            category = raw.get("category")

            findings.append(
                FindingSchema(
                    id=str(raw.get("rule_id") or f"finding-{index}"),
                    title=str(raw.get("title") or "Unnamed rule"),
                    severity=_SEVERITY.get(str(raw.get("severity", "")).lower(), "Low"),
                    description=(
                        str(snippet)
                        if snippet
                        else f"Matched the {category} rule set."
                        if category
                        else "This rule fired without recorded evidence."
                    ),
                    page=_as_int(evidence.get("page"), default=1),
                )
            )

        # Worst first: a High buried under two Lows is the thing a reviewer
        # opened the document to find.
        order = {"High": 0, "Medium": 1, "Low": 2}
        findings.sort(key=lambda f: order.get(f.severity, 3))
        return findings

    def risk_scores(self, document_ids: list[str]) -> dict[str, int]:
        """Risk scores for a page of documents, in one query.

        The library renders a risk column and a verdict for every row, and the
        dashboard derives its whole risk distribution from them. Fetching them
        per row would be a query per document on every list and every poll.
        """
        if not document_ids:
            return {}

        rows = self._db.execute(
            select(RiskAssessment.document_id, RiskAssessment.risk_score).where(
                RiskAssessment.document_id.in_(document_ids)
            )
        ).all()
        return {doc_id: score for doc_id, score in rows if score is not None}

    # -- summary -----------------------------------------------------------

    def summary(self, document_id: str) -> DocumentSummary | None:
        return self._db.get(DocumentSummary, document_id)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
