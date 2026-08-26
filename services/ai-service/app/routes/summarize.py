"""POST /summarize - document summarisation.

Named as an ai-service endpoint in three places (``services/README.md``,
``docs/team/ROLES.md`` role 4, and ``docs/PROJECT-PROPOSAL.md``), so it is part
of the contract other roles will code against.

Unlike /classify and /extract, this has no deterministic equivalent worth
serving: a summary is genuinely a generation task. The offline mock does
extractive selection instead - it picks the most central real sentences rather
than generating text - which keeps the endpoint usable with no credential
without pretending a stand-in wrote prose.

The response splits ``summary`` from ``key_points`` because the two get used
differently: the frontend shows the paragraph, and the key points are what a
reviewer scans. Parsing them apart here means every caller does not have to.
"""

from __future__ import annotations

import time

from fastapi import APIRouter

from app import pipeline, prompts
from app.adapters.base import ChatMessage
from app.analysis import classify_rules
from app.budget import check_text_budget
from app.config import settings
from app.schemas import SummarizeRequest, SummarizeResponse

router = APIRouter(tags=["summarization"])

ENDPOINT = "/summarize"

#: The exact string the prompt instructs the model to return when there is not
#: enough text. Matched to set ``insufficient_text``.
INSUFFICIENT = "does not contain enough text to summarise"


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest) -> SummarizeResponse:
    started = time.monotonic()
    check_text_budget(request.text, limit=settings.token_budget_per_request, endpoint=ENDPOINT)

    document_type = request.document_type
    if document_type is None:
        document_type, _confidence, _scores, _rationale = classify_rules.classify(request.text)

    text_for_provider, redaction = pipeline.prepare_text(request.text)

    outcome = pipeline.chat(
        [
            ChatMessage(
                "user",
                prompts.render(
                    "summarize",
                    text=text_for_provider,
                    document_type=document_type,
                    style=request.style,
                    max_sentences=request.max_sentences,
                    max_points=request.max_points,
                ),
            )
        ],
        task="summarize",
        endpoint=ENDPOINT,
        context={
            "text": text_for_provider,
            "max_sentences": request.max_sentences,
            "max_points": request.max_points,
        },
    )

    raw = outcome.text.strip()
    if redaction is not None:
        # The tenant owns this document; redaction protects it from the
        # provider, not from the person who uploaded it.
        raw = redaction.restore(raw)

    summary, key_points = _split(raw, request.max_points)

    return SummarizeResponse(
        document_id=request.document_id,
        document_type=document_type,  # type: ignore[arg-type]
        summary=summary,
        key_points=key_points,
        insufficient_text=INSUFFICIENT in raw.lower(),
        meta=pipeline.build_meta(
            started=started,
            outcome=outcome,
            endpoint=ENDPOINT,
            request_id=request.request_id,
            redaction=redaction,
        ),
    )


def _split(text: str, max_points: int) -> tuple[str, list[str]]:
    """Separate the prose paragraph from the bulleted key points.

    Tolerant of the three bullet characters models actually emit, and of a
    model that ignores the format entirely - in which case everything becomes
    the summary and ``key_points`` is empty, rather than raising.
    """
    summary_lines: list[str] = []
    points: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0] in "-*•":
            point = stripped.lstrip("-*•").strip()
            if point:
                points.append(point)
        elif not points:
            # Prose before the first bullet is the summary; anything after a
            # bullet that is not itself a bullet is trailing commentary we drop.
            summary_lines.append(stripped)

    return " ".join(summary_lines).strip(), points[:max_points]
