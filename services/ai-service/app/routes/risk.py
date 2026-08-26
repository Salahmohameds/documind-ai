"""POST /analysis/risk - contract risk scoring.

The number is produced by :mod:`app.analysis.risk_rules`, a fixed versioned rule
set. The model writes the narrative and cannot move the score.

This is the deliberate answer to the obvious Q&A question, *"how did you
validate 72 out of 100?"* Every point traces to a named rule and a quoted span,
the same document always scores the same, and the rule set is unit-tested. A
model asked for a number could not survive that question, so it is not asked
for one.

If the explanation call fails, the score, band and findings are still returned
with ``meta.degraded=true``. The valuable half of this endpoint does not depend
on the provider being up.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from app import pipeline, prompts
from app.adapters.base import ChatMessage
from app.analysis import risk_rules
from app.budget import check_text_budget
from app.config import settings
from app.errors import AIServiceError
from app.schemas import Evidence, RiskFinding, RiskRequest, RiskResponse, RiskScoring

logger = logging.getLogger(settings.service_name)
router = APIRouter(tags=["risk"])

ENDPOINT = "/analysis/risk"


@router.post("/analysis/risk", response_model=RiskResponse)
def analyse_risk(request: RiskRequest) -> RiskResponse:
    started = time.monotonic()
    check_text_budget(request.text, limit=settings.token_budget_per_request, endpoint=ENDPOINT)

    result = risk_rules.score_document(request.text)

    findings = [
        RiskFinding(
            rule_id=f.rule_id,
            title=f.title,
            severity=f.severity,
            weight=f.weight,
            evidence=(
                Evidence(snippet=f.snippet, offset=f.offset) if f.snippet is not None else None
            ),
        )
        for f in result.findings
    ]

    explanation = ""
    outcome = None
    degraded = False
    redaction = None

    if request.explain:
        # Only the findings are sent, never the contract body. The findings are
        # already-quoted spans the rule engine selected, which keeps the prompt
        # small and dramatically narrows what egresses.
        rendered = _render_findings(result)
        text_for_provider, redaction = pipeline.prepare_text(rendered)
        try:
            outcome = pipeline.chat(
                [
                    ChatMessage(
                        "user",
                        prompts.render(
                            "risk_explain",
                            score=result.score,
                            band=result.band,
                            finding_count=result.rules_fired,
                            rules_evaluated=result.rules_evaluated,
                            findings=text_for_provider,
                        ),
                    )
                ],
                task="risk_explain",
                endpoint=ENDPOINT,
                context={
                    "score": result.score,
                    "band": result.band,
                    "findings": [
                        {"title": f.title, "severity": f.severity, "rule_id": f.rule_id}
                        for f in result.findings
                    ],
                },
            )
            explanation = outcome.text.strip()
            if redaction is not None:
                explanation = redaction.restore(explanation)
        except AIServiceError as exc:
            degraded = True
            explanation = _fallback_explanation(result)
            logger.warning(
                "risk_explanation_degraded",
                extra={"event": "risk_explanation_degraded", "error": str(exc)},
            )
    else:
        explanation = _fallback_explanation(result)

    return RiskResponse(
        document_id=request.document_id,
        score=result.score,
        band=result.band,
        findings=findings,
        explanation=explanation,
        scoring=RiskScoring(
            rules_version=result.rules_version,
            points_scored=result.points_scored,
            points_possible=result.points_possible,
            rules_evaluated=result.rules_evaluated,
            rules_fired=result.rules_fired,
        ),
        meta=pipeline.build_meta(
            started=started,
            outcome=outcome,
            endpoint=ENDPOINT,
            request_id=request.request_id,
            redaction=redaction,
            degraded=degraded,
        ),
    )


def _render_findings(result: risk_rules.RiskResult) -> str:
    if not result.findings:
        return "No rules matched."
    lines = []
    for f in result.findings:
        quote = f'"{f.snippet}"' if f.snippet else "(clause absent from the document)"
        lines.append(f"- [{f.rule_id}] {f.title} (severity: {f.severity}) {quote}")
    return "\n".join(lines)


def _fallback_explanation(result: risk_rules.RiskResult) -> str:
    """Explanation with no model involved at all.

    Used when ``explain=false`` (load tests, which must not burn tokens) and
    when the provider call fails.
    """
    if not result.findings:
        return (
            f"No risk rules matched. Calibrated score {result.score}/100 "
            f"({result.band} risk) from {result.rules_evaluated} rules evaluated."
        )
    titles = ", ".join(f.title for f in result.findings[:5])
    return (
        f"Calibrated score {result.score}/100 ({result.band} risk). "
        f"{result.rules_fired} of {result.rules_evaluated} rules matched: {titles}."
    )
