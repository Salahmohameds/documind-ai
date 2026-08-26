"""POST /extract - structured field extraction.

The rule engine extracts what regexes can reach. A real provider is then asked
**only for the fields still missing**, which keeps the token spend proportional
to the hard part of the problem rather than re-deriving an invoice number a
regex already found.

Every model-supplied value is located in the source document before it is
accepted. A value that cannot be found is dropped, not returned with a caveat -
see :func:`app.analysis.extraction.verify_against_source`. That is the cheapest
effective guard against a model inventing a total, and it costs one string
search per field.
"""

from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter

from app import pipeline, prompts
from app.adapters import get_provider
from app.adapters.base import ChatMessage
from app.analysis import classify_rules, extraction
from app.budget import check_text_budget
from app.config import settings
from app.errors import AIServiceError
from app.schemas import Evidence, ExtractedField, ExtractRequest, ExtractResponse

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["extraction"])

ENDPOINT = "/extract"

#: Confidence assigned to a model-supplied value that was verified in the
#: source. Lower than a regex hit: the regex matched a labelled field, the
#: model matched a sentence.
MODEL_VERIFIED_CONFIDENCE = 0.6


@router.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest) -> ExtractResponse:
    started = time.monotonic()
    check_text_budget(request.text, limit=settings.token_budget_per_request, endpoint=ENDPOINT)

    document_type = request.document_type
    if document_type is None:
        document_type, _confidence, _scores, _rationale = classify_rules.classify(request.text)

    found = extraction.extract(request.text, document_type, request.fields)

    provider = get_provider()
    outcome = None
    degraded = False
    redaction = None

    missing = [name for name, value in found.items() if value.value is None]

    if provider.is_external and missing:
        text_for_provider, redaction = pipeline.prepare_text(request.text)
        try:
            outcome = pipeline.chat(
                [
                    ChatMessage(
                        "user",
                        prompts.render(
                            "extract",
                            text=text_for_provider,
                            document_type=document_type,
                            fields=", ".join(missing),
                        ),
                    )
                ],
                task="extract",
                endpoint=ENDPOINT,
                context={"text": text_for_provider, "fields": missing},
            )
            _merge_model_fields(outcome.text, missing, request.text, found)
        except AIServiceError as exc:
            degraded = True
            logger.warning(
                "extract_degraded_to_rules",
                extra={"event": "extract_degraded_to_rules", "error": str(exc)},
            )

    fields = {
        name: ExtractedField(
            value=value.value,
            confidence=value.confidence,
            evidence=(
                Evidence(snippet=value.snippet, offset=value.offset)
                if value.snippet is not None
                else None
            ),
        )
        for name, value in found.items()
    }

    return ExtractResponse(
        document_id=request.document_id,
        document_type=document_type,  # type: ignore[arg-type]
        fields=fields,
        meta=pipeline.build_meta(
            started=started,
            outcome=outcome,
            endpoint=ENDPOINT,
            request_id=request.request_id,
            redaction=redaction,
            degraded=degraded,
        ),
    )


def _merge_model_fields(
    response_text: str,
    requested: list[str],
    source_text: str,
    found: dict[str, extraction.ExtractedValue],
) -> None:
    """Accept model values only where they can be located in the source."""
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start == -1 or end <= start:
        return

    try:
        data = json.loads(response_text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        logger.warning("extract_model_output_unparseable", extra={"event": "extract_model_output_unparseable"})
        return

    if not isinstance(data, dict):
        return

    for name in requested:
        raw = data.get(name)
        if raw in (None, "", "null"):
            continue

        value = str(raw).strip()
        verified, offset, snippet = extraction.verify_against_source(value, source_text)
        if not verified:
            logger.info(
                "extract_value_unverified",
                extra={
                    "event": "extract_value_unverified",
                    "field": name,
                    # The value itself is not logged: it may be exactly the
                    # personal data this service exists to keep contained.
                    "reason": "not_found_in_source",
                },
            )
            continue

        found[name] = extraction.ExtractedValue(
            value=value,
            confidence=MODEL_VERIFIED_CONFIDENCE,
            offset=offset,
            snippet=snippet,
        )
