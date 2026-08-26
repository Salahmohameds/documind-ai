"""POST /classify - document type detection.

Deterministic first, model second:

1. The rule engine always runs. It is fast, free, reproducible and produces the
   ``scores`` breakdown so a caller can see how close the runner-up was.
2. When a real provider is configured, the model is consulted and its label
   wins if it is one of the five valid labels.
3. If the model is unreachable or returns something unparseable, the rules'
   verdict is served and ``meta.degraded`` is set.

The endpoint therefore never fails because the provider is down - it gets
quietly worse, and says so.
"""

from __future__ import annotations

import json
import logging
import time
from typing import get_args

from fastapi import APIRouter

from app import pipeline, prompts
from app.adapters import get_provider
from app.adapters.base import ChatMessage
from app.budget import check_text_budget
from app.config import settings
from app.errors import AIServiceError
from app.analysis import classify_rules
from app.schemas import ClassifyRequest, ClassifyResponse, DocumentType

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["classification"])

ENDPOINT = "/classify"
VALID_LABELS = frozenset(get_args(DocumentType))


@router.post("/classify", response_model=ClassifyResponse)
def classify(request: ClassifyRequest) -> ClassifyResponse:
    started = time.monotonic()
    check_text_budget(request.text, limit=settings.token_budget_per_request, endpoint=ENDPOINT)

    label, confidence, scores, rationale = classify_rules.classify(request.text)

    provider = get_provider()
    outcome = None
    degraded = False
    redaction = None

    # The mock provider's classify task runs this very rule engine, so calling
    # it would be pure overhead. Skip straight to the rules' answer offline.
    if provider.is_external:
        text_for_provider, redaction = pipeline.prepare_text(request.text)
        try:
            outcome = pipeline.chat(
                [ChatMessage("user", prompts.render("classify", text=text_for_provider))],
                task="classify",
                endpoint=ENDPOINT,
                context={"text": text_for_provider},
            )
            parsed = _parse(outcome.text)
            if parsed:
                label, confidence, rationale = parsed
            else:
                degraded = True
                logger.warning(
                    "classify_model_output_unparseable",
                    extra={"event": "classify_model_output_unparseable"},
                )
        except AIServiceError as exc:
            degraded = True
            logger.warning(
                "classify_degraded_to_rules",
                extra={"event": "classify_degraded_to_rules", "error": str(exc)},
            )

    return ClassifyResponse(
        document_id=request.document_id,
        label=label,  # type: ignore[arg-type]
        confidence=confidence,
        scores=scores,
        rationale=rationale,
        meta=pipeline.build_meta(
            started=started,
            outcome=outcome,
            endpoint=ENDPOINT,
            request_id=request.request_id,
            redaction=redaction,
            degraded=degraded,
        ),
    )


def _parse(text: str) -> tuple[str, float, str] | None:
    """Pull ``{label, confidence, rationale}`` out of a model response.

    Models wrap JSON in prose and fences often enough that locating the first
    object is worth the six lines it costs.
    """
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None

    label = str(data.get("label", "")).strip().lower()
    if label not in VALID_LABELS:
        return None

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    rationale = str(data.get("rationale", "")).strip() or "No rationale supplied by the model."
    return label, max(0.0, min(1.0, confidence)), rationale
