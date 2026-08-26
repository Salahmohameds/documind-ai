"""Per-request token budget.

A runaway prompt is a cost incident, and on a shared intern tenancy with a hard
budget it is the kind that ends a demo. The budget is checked **before** any
provider call, using a local estimate - you cannot ask a provider what a request
will cost without paying to find out.

Enforcement is deliberately a 413 rather than silent truncation: quietly
dropping half a contract and answering anyway produces a confident, wrong
answer, which is worse than an error the caller can act on.
"""

from __future__ import annotations

import logging

from app.adapters.base import estimate_tokens
from app.errors import BatchTooLargeError, TokenBudgetExceededError
from app.metrics import BUDGET_REJECTIONS

logger = logging.getLogger("ai-service")


def check_text_budget(text: str, *, limit: int, endpoint: str) -> int:
    """Reject a single oversized payload. Returns the estimated token count."""
    estimated = estimate_tokens(text)
    if estimated > limit:
        BUDGET_REJECTIONS.labels(endpoint=endpoint, reason="token_budget").inc()
        logger.warning(
            "token_budget_exceeded",
            extra={
                "event": "token_budget_exceeded",
                "endpoint": endpoint,
                "estimated_tokens": estimated,
                "limit": limit,
            },
        )
        raise TokenBudgetExceededError(
            f"Estimated {estimated} tokens exceeds TOKEN_BUDGET_PER_REQUEST={limit}. "
            "Split the document into smaller requests."
        )
    return estimated


def check_batch(texts: list[str], *, max_batch: int, limit: int, endpoint: str) -> int:
    """Reject an oversized embedding batch, then budget-check the whole batch."""
    if len(texts) > max_batch:
        BUDGET_REJECTIONS.labels(endpoint=endpoint, reason="batch_size").inc()
        raise BatchTooLargeError(
            f"{len(texts)} texts exceeds MAX_EMBED_BATCH={max_batch}. "
            "Send multiple batches."
        )

    estimated = sum(estimate_tokens(t) for t in texts)
    if estimated > limit:
        BUDGET_REJECTIONS.labels(endpoint=endpoint, reason="token_budget").inc()
        raise TokenBudgetExceededError(
            f"Estimated {estimated} tokens across {len(texts)} texts exceeds "
            f"TOKEN_BUDGET_PER_REQUEST={limit}. Send smaller batches."
        )
    return estimated


def trim_context(
    chunks: list[dict],
    *,
    max_chunks: int,
    token_limit: int,
) -> tuple[list[dict], bool]:
    """Fit retrieved chunks inside the budget, best-scoring first.

    Returns ``(kept, trimmed)``. Unlike the single-payload path this *does*
    drop content, because a caller sending 40 chunks is asking for the best
    available context, not for all of it - and ``trimmed`` tells them it
    happened so it can be surfaced rather than hidden.
    """
    ordered = sorted(
        chunks,
        key=lambda c: (c.get("score") if c.get("score") is not None else 0.0),
        reverse=True,
    )
    kept: list[dict] = []
    used = 0
    trimmed = False

    for chunk in ordered[:max_chunks]:
        cost = estimate_tokens(chunk.get("text", ""))
        if used + cost > token_limit:
            trimmed = True
            break
        kept.append(chunk)
        used += cost

    if len(ordered) > max_chunks:
        trimmed = True

    return kept, trimmed
