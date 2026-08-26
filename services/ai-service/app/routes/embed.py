"""POST /embed - the endpoint search-service (role 6) consumes.

Ownership boundary, agreed in docs/architecture/ai-service-contract.md:

* **ai-service** owns the model client, the credentials, and the token budget.
  It turns text into vectors and forgets them.
* **search-service** owns chunking, storage, indexing and retrieval.

That means role 6's ``OCIGenerativeAIEmbedder`` becomes a thin HTTP call to
this endpoint instead of a second place where OCI credentials live.

Batch-first: a 40-page contract is hundreds of chunks, and a one-string-per-call
endpoint would put a network round-trip on the highest-volume path in the
platform. ``MAX_EMBED_BATCH`` bounds the batch; oversized batches are rejected,
not silently truncated.
"""

from __future__ import annotations

import time

from fastapi import APIRouter

from app import pipeline
from app.budget import check_batch
from app.config import settings
from app.schemas import EmbedRequest, EmbedResponse

router = APIRouter(tags=["embeddings"])

ENDPOINT = "/embed"


@router.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest) -> EmbedResponse:
    started = time.monotonic()

    check_batch(
        request.texts,
        max_batch=settings.max_embed_batch,
        limit=settings.token_budget_per_request,
        endpoint=ENDPOINT,
    )

    # Embeddings are not redacted. The vectors never leave the platform as text,
    # and redacting first would change the vector for a document the tenant
    # already owns - degrading their own retrieval to protect them from
    # themselves. Redaction guards *generation* prompts, which is where content
    # leaves in readable form.
    outcome = pipeline.embed(
        request.texts, input_type=request.input_type, endpoint=ENDPOINT
    )

    return EmbedResponse(
        embeddings=outcome.vectors,
        dim=outcome.dim,
        count=len(outcome.vectors),
        meta=pipeline.build_meta(
            started=started,
            outcome=outcome,
            endpoint=ENDPOINT,
            request_id=request.request_id,
            redaction=None,
        ),
    )
