"""POST /answer - RAG generation with page-level citations.

Boundary: **this endpoint does not retrieve.** search-service (role 6) passes
the chunks it retrieved; ai-service turns them into a cited answer. Retrieval
quality is measured by role 6's harness, answer quality by
``tests/rag-evaluation/evaluate_generation.py``. Neither can hide behind the
other, which is the point.

Citations are parsed from ``[n]`` markers and resolved against the passages that
were actually supplied. A marker pointing at a passage that does not exist is
dropped, not rendered - a citation the user can click and find nothing behind is
worse than no citation.

``confidence`` is deliberately narrow: it is the share of citation markers that
resolve to a supplied passage. It is not a semantic confidence, and it is
documented as such rather than dressed up as one.
"""

from __future__ import annotations

import re
import time

from fastapi import APIRouter

from app import pipeline, prompts
from app.adapters.base import ChatMessage
from app.budget import trim_context
from app.config import settings
from app.schemas import AnswerRequest, AnswerResponse, Citation

router = APIRouter(tags=["rag"])

ENDPOINT = "/answer"

#: The exact string the prompt instructs the model to return when the context
#: does not support an answer. Matched to set ``refused``.
REFUSAL = "I could not find an answer in the provided documents."

_CITATION_RE = re.compile(r"\[(\d{1,2})\]")


@router.post("/answer", response_model=AnswerResponse)
def answer(request: AnswerRequest) -> AnswerResponse:
    started = time.monotonic()

    chunk_dicts = [c.model_dump() for c in request.chunks]
    kept, trimmed = trim_context(
        chunk_dicts,
        max_chunks=settings.max_context_chunks,
        token_limit=settings.token_budget_per_request,
    )

    if not kept:
        # Nothing to ground an answer in. Refusing here costs no tokens and is
        # the correct outcome, not an error.
        return AnswerResponse(
            answer=REFUSAL,
            citations=[],
            grounded=False,
            refused=True,
            confidence=0.0,
            meta=pipeline.build_meta(
                started=started,
                outcome=None,
                endpoint=ENDPOINT,
                request_id=request.request_id,
                redaction=None,
            ),
        )

    # Redact each passage individually so passage boundaries - and therefore
    # citation offsets - survive.
    redacted_chunks = []
    redactions = []
    for chunk in kept:
        text, redaction = pipeline.prepare_text(chunk.get("text", ""))
        redacted_chunks.append({**chunk, "text": text})
        redactions.append(redaction)

    question, question_redaction = pipeline.prepare_text(request.question)

    context_block = "\n\n".join(
        f"[{index}] {chunk['text']}" for index, chunk in enumerate(redacted_chunks, start=1)
    )

    outcome = pipeline.chat(
        [ChatMessage("user", prompts.render("answer", context=context_block, question=question))],
        task="answer",
        endpoint=ENDPOINT,
        context={"question": question, "chunks": redacted_chunks},
    )

    answer_text = outcome.text.strip()

    # Restore redacted values in the answer itself. Redaction protects the
    # document from the *provider*; it is not meant to hide the tenant's own
    # data from the tenant. Snippets below come from the unredacted originals.
    for redaction in [*redactions, question_redaction]:
        if redaction is not None:
            answer_text = redaction.restore(answer_text)

    refused = REFUSAL.lower() in answer_text.lower()
    citations, valid, total = _resolve_citations(answer_text, kept)

    confidence = 0.0 if refused or total == 0 else round(valid / total, 4)
    grounded = bool(not refused and citations and valid == total)

    if trimmed:
        answer_text += (
            f"\n\n(Context was limited to the {len(kept)} highest-scoring passages.)"
        )

    return AnswerResponse(
        answer=answer_text,
        citations=citations,
        grounded=grounded,
        refused=refused,
        confidence=confidence,
        meta=pipeline.build_meta(
            started=started,
            outcome=outcome,
            endpoint=ENDPOINT,
            request_id=request.request_id,
            redaction=redactions[0] if redactions else None,
        ),
    )


def _resolve_citations(text: str, chunks: list[dict]) -> tuple[list[Citation], int, int]:
    """Map ``[n]`` markers onto the passages that were actually supplied.

    Returns ``(citations, valid_marker_count, total_marker_count)``. Markers
    outside the supplied range are counted but not rendered.
    """
    markers = _CITATION_RE.findall(text)
    total = len(markers)
    seen: set[int] = set()
    citations: list[Citation] = []
    valid = 0

    for marker in markers:
        index = int(marker)
        if not (1 <= index <= len(chunks)):
            continue
        valid += 1
        if index in seen:
            continue
        seen.add(index)

        chunk = chunks[index - 1]
        snippet = " ".join(chunk.get("text", "").split())
        citations.append(
            Citation(
                chunk_id=chunk.get("chunk_id", f"chunk-{index}"),
                document_id=chunk.get("document_id"),
                page=chunk.get("page"),
                snippet=snippet[:300] + ("..." if len(snippet) > 300 else ""),
            )
        )

    return citations, valid, total
