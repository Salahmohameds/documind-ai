"""Deterministic contract risk scoring.

Why this is not an LLM call
---------------------------
Asking a model for "72 out of 100" produces a number nobody can validate,
reproduce, or defend in a review. Here the score comes from a fixed, versioned
rule set: every point is attributable to a named rule with a quoted span from
the source document, and the same document always scores the same.

The language model's only job is to write the narrative in
``RiskResponse.explanation``. It cannot move the number.

Two kinds of rule
-----------------
* **presence** - risky language that is present ("automatically renew").
* **absence**  - protective language that is missing (no liability cap). These
  matter more in practice and are exactly what a keyword-spotting demo misses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.analysis.text import snippet

RULES_VERSION = "risk-1.0"

#: Raw weighted points that map to a score of 100.
#:
#: Calibration, not arithmetic: the rule weights sum to far more than any real
#: contract scores, so normalising by the theoretical maximum would squash every
#: document into the low teens. 60 points is roughly "several high-severity
#: findings at once". Changing this constant is a scoring change and MUST come
#: with a RULES_VERSION bump so historical scores stay interpretable.
CALIBRATION_MAX = 60

Severity = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    severity: Severity
    weight: int
    #: Regex that identifies the clause.
    pattern: str
    #: When True the rule fires because the pattern is ABSENT.
    absence: bool = False
    #: Optional guard: an absence rule only applies if this pattern IS present
    #: (e.g. only flag a missing liability cap in something that is a contract).
    applies_if: str | None = None
    #: Numeric threshold. When set, the rule fires only if capture group 1
    #: parses as a number >= this value. Regex alone cannot compare magnitudes,
    #: and trying to express "more than 60 days" or "above 2%" as a character
    #: pattern is how you end up matching the '5' inside '1.5%'.
    min_value: float | None = None


RULES: tuple[Rule, ...] = (
    Rule(
        "R01",
        "Automatic renewal",
        "medium",
        10,
        r"automatic(ally)?\s+renew|auto[- ]?renew|successive\s+(one|1)[- ]year\s+terms",
    ),
    Rule(
        "R02",
        "No limitation of liability",
        "high",
        20,
        # Real contracts write "Provider's total liability under this Agreement
        # shall not exceed ...", so the cap language must tolerate an
        # intervening clause. Anchoring on adjacent words produced a false
        # positive on a contract that plainly had a cap.
        r"limitation\s+of\s+liability"
        r"|liability[^.]{0,80}?(?:shall|will)\s+not\s+exceed"
        r"|aggregate\s+liability"
        r"|liability\s+cap"
        r"|not\s+be\s+liable\s+for\s+(?:any\s+)?(?:indirect|incidental|consequential)",
        absence=True,
        applies_if=r"\bagreement\b|\bparties\b|\bshall\b",
    ),
    Rule(
        "R03",
        "Short cure period",
        "medium",
        8,
        r"cure\s+(period\s+of\s+)?(within\s+)?(one|two|three|four|five|six|seven|"
        r"eight|nine|ten|[1-9]|10)\s+(business\s+)?days",
    ),
    Rule(
        "R04",
        "Termination for convenience",
        "medium",
        8,
        r"terminat\w*\s+(this\s+\w+\s+)?for\s+convenience|"
        r"terminat\w*\s+at\s+any\s+time\s+(for\s+any\s+reason|without\s+cause)",
    ),
    Rule(
        "R05",
        "Extended payment terms",
        "medium",
        10,
        # Anything beyond net-60 is a working-capital cost worth flagging.
        r"(?:net\s*|within\s+)(\d+)\s*days?",
        min_value=61,
    ),
    Rule(
        "R06",
        "Punitive late-payment interest",
        "low",
        5,
        # 1.5 %/month is the market convention; 2 %+ is punitive. The lookbehind
        # stops the digit after a decimal point being read as the whole rate.
        r"(?<![\d.])(\d+(?:\.\d+)?)\s*%\s*(?:per\s+month|monthly)",
        min_value=2.0,
    ),
    Rule(
        "R07",
        "No governing law clause",
        "medium",
        10,
        r"governing\s+law|shall\s+be\s+governed\s+by|jurisdiction\s+of",
        absence=True,
        applies_if=r"\bagreement\b|\bparties\b",
    ),
    Rule(
        "R08",
        "Uncapped indemnity",
        "high",
        15,
        r"indemnif(y|ies|ication)",
    ),
    Rule(
        "R09",
        "No confidentiality obligation",
        "medium",
        8,
        r"confidential(ity)?|non[- ]disclosure",
        absence=True,
        applies_if=r"\bagreement\b|\bparties\b",
    ),
    Rule(
        "R10",
        "No termination clause",
        "high",
        15,
        r"terminat(e|ion)",
        absence=True,
        applies_if=r"\bagreement\b|\bparties\b",
    ),
    Rule(
        "R11",
        "Broad IP assignment",
        "medium",
        8,
        r"assigns?\s+all\s+right,?\s+title\s+and\s+interest|"
        r"work\s+made\s+for\s+hire",
    ),
    Rule(
        "R12",
        "Non-compete restriction",
        "medium",
        8,
        r"non[- ]compet\w*|shall\s+not\s+(directly\s+or\s+indirectly\s+)?compete",
    ),
    Rule(
        "R13",
        "Unilateral amendment right",
        "high",
        12,
        r"may\s+(amend|modify|change)\s+.{0,60}(sole\s+discretion|at\s+any\s+time)",
    ),
    Rule(
        "R14",
        "No data-protection provision",
        "low",
        5,
        r"data\s+protection|personal\s+data|gdpr|privacy\s+polic",
        absence=True,
        applies_if=r"\bagreement\b|\bparties\b",
    ),
    Rule(
        "R15",
        "Liquidated damages / penalty",
        "medium",
        8,
        r"liquidated\s+damages|penalt(y|ies)\s+of",
    ),
)

_COMPILED = {
    r.rule_id: (
        re.compile(r.pattern, re.IGNORECASE),
        re.compile(r.applies_if, re.IGNORECASE) if r.applies_if else None,
    )
    for r in RULES
}

POINTS_POSSIBLE = sum(r.weight for r in RULES)


@dataclass
class Finding:
    rule_id: str
    title: str
    severity: Severity
    weight: int
    snippet: str | None
    offset: int | None


@dataclass
class RiskResult:
    score: int
    band: Literal["low", "medium", "high"]
    findings: list[Finding]
    points_scored: int
    points_possible: int
    rules_evaluated: int
    rules_fired: int
    rules_version: str


def _first_match_over(pattern: re.Pattern[str], text: str, threshold: float) -> re.Match[str] | None:
    """First match whose capture group 1 parses as a number >= ``threshold``."""
    for match in pattern.finditer(text):
        raw = match.group(1) if match.groups() else None
        if raw is None:
            continue
        try:
            if float(raw) >= threshold:
                return match
        except ValueError:
            continue
    return None


def band_for(score: int) -> Literal["low", "medium", "high"]:
    if score >= 65:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def score_document(text: str) -> RiskResult:
    """Evaluate every rule against ``text`` and return an auditable result."""
    findings: list[Finding] = []
    points = 0

    for rule in RULES:
        pattern, guard = _COMPILED[rule.rule_id]
        match = pattern.search(text)

        # A threshold rule only counts a match whose captured number clears the
        # bar. Scan onwards rather than giving up on the first sub-threshold
        # hit: "net 30 days ... net 90 days" must still fire.
        if match and rule.min_value is not None:
            match = _first_match_over(pattern, text, rule.min_value)

        if rule.absence:
            if guard is not None and not guard.search(text):
                continue  # rule does not apply to this kind of document
            if match:
                continue  # the protective clause is present - no finding
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    severity=rule.severity,
                    weight=rule.weight,
                    snippet=None,  # nothing to quote: the point is the absence
                    offset=None,
                )
            )
            points += rule.weight
        elif match:
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    severity=rule.severity,
                    weight=rule.weight,
                    snippet=snippet(text, max(0, match.start() - 40), 240),
                    offset=match.start(),
                )
            )
            points += rule.weight

    score = min(100, round(100 * points / CALIBRATION_MAX)) if points else 0
    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (severity_order[f.severity], -f.weight))

    return RiskResult(
        score=score,
        band=band_for(score),
        findings=findings,
        points_scored=points,
        points_possible=POINTS_POSSIBLE,
        rules_evaluated=len(RULES),
        rules_fired=len(findings),
        rules_version=RULES_VERSION,
    )
