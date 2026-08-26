"""POST /pii - PII detection and redaction as a first-class endpoint.

The same :mod:`app.redaction` code that runs automatically before every external
provider call is exposed directly, which buys three things:

* role 7 can point the threat model at a control they can call and test, rather
  than at a claim in a README;
* role 8 can test PII detection as a functional requirement in its own right;
* the product feature ("we detect PII in your documents") and the security
  control ("PII never leaves the cluster in readable form") are demonstrably the
  same code, so they cannot drift apart.

Raw values are withheld unless ``include_values`` is explicitly set. The default
exists so that a casual debugging call, or a log line capturing a response,
cannot become the leak this service was built to prevent.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.redaction import redact
from app.schemas import PIIMatch, PIIRequest, PIIResponse

router = APIRouter(tags=["security"])

ENDPOINT = "/pii"


@router.post("/pii", response_model=PIIResponse)
def detect_pii(request: PIIRequest) -> PIIResponse:
    result = redact(request.text)

    return PIIResponse(
        document_id=request.document_id,
        matches=[
            PIIMatch(
                type=m.type,
                placeholder=m.placeholder,
                start=m.start,
                end=m.end,
                value=m.value if request.include_values else None,
            )
            for m in result.matches
        ],
        counts=result.counts,
        redacted_text=result.text if request.return_redacted_text else None,
    )
