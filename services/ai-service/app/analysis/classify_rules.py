"""Deterministic document classifier.

Weighted keyword evidence per document type. Reproducible, unit-testable, and
fast enough to sit in the request path.

Role in the service
-------------------
* With ``AI_BACKEND=mock`` this **is** the classifier - which is why the whole
  pipeline works offline.
* With a real backend it is the fallback used when the model is unreachable or
  returns an unparseable label, so /classify degrades instead of failing.
"""

from __future__ import annotations

import re

from app.analysis.text import snippet

# (pattern, weight). Patterns are matched case-insensitively as whole phrases.
_SIGNALS: dict[str, list[tuple[str, int]]] = {
    "invoice": [
        (r"\binvoice\s*(no\.?|number|#)", 5),
        (r"\binvoice\b", 3),
        (r"\bbill\s+to\b", 3),
        (r"\bremit\s+to\b", 3),
        (r"\bamount\s+due\b", 3),
        (r"\bsubtotal\b", 2),
        (r"\btotal\s+due\b", 3),
        (r"\bpurchase\s+order\b", 2),
        (r"\bunit\s+price\b", 2),
        (r"\bqty\b|\bquantity\b", 1),
        (r"\bdue\s+date\b", 2),
        (r"\btax\b|\bvat\b", 1),
    ],
    "contract": [
        (r"\bthis\s+agreement\b", 5),
        (r"\bagreement\b", 2),
        (r"\bwhereas\b", 3),
        (r"\bthe\s+parties\b|\bbetween\s+.{0,60}\band\b.{0,60}\(", 3),
        (r"\bgoverning\s+law\b", 3),
        (r"\bconfidential(ity)?\b", 2),
        (r"\bindemnif(y|ication)\b", 3),
        (r"\blimitation\s+of\s+liability\b", 3),
        (r"\bterminat(e|ion)\b", 2),
        (r"\bin\s+witness\s+whereof\b", 4),
        (r"\beffective\s+date\b", 2),
        (r"\bshall\b", 1),
    ],
    "receipt": [
        (r"\breceipt\b", 5),
        (r"\bchange\s+due\b", 4),
        (r"\bcard\s+ending\b", 4),
        (r"\btransaction\s+id\b", 3),
        (r"\bmerchant\b", 2),
        (r"\bthank\s+you\s+for\s+your\s+(purchase|business)\b", 3),
        (r"\bcashier\b", 2),
    ],
    "report": [
        (r"\bexecutive\s+summary\b", 5),
        (r"\bmethodolog(y|ies)\b", 4),
        (r"\bfindings\b", 3),
        (r"\bconclusions?\b", 2),
        (r"\bappendix\b", 3),
        (r"\bfigure\s+\d+\b", 2),
        (r"\btable\s+\d+\b", 2),
        (r"\bquarterly\b|\bannual\s+report\b", 3),
    ],
}

_COMPILED: dict[str, list[tuple[re.Pattern[str], int]]] = {
    label: [(re.compile(p, re.IGNORECASE), w) for p, w in sigs]
    for label, sigs in _SIGNALS.items()
}

#: Below this raw score the document is 'unknown' rather than a bad guess.
MIN_CONFIDENT_SCORE = 5

RULES_VERSION = "classify-1.0"


def classify(text: str) -> tuple[str, float, dict[str, float], str]:
    """Return ``(label, confidence, scores, rationale)``.

    ``scores`` are normalised to sum to 1.0 across the candidate labels so the
    caller can see how close the runner-up was - a 0.51/0.49 split is very
    different from 0.95/0.05 and the API should not hide that.
    """
    raw: dict[str, int] = {}
    hits: dict[str, list[str]] = {}

    for label, patterns in _COMPILED.items():
        score = 0
        matched: list[str] = []
        for pattern, weight in patterns:
            match = pattern.search(text)
            if match:
                score += weight
                matched.append(snippet(text, match.start(), 60))
        raw[label] = score
        hits[label] = matched

    total = sum(raw.values())
    best_label = max(raw, key=lambda k: raw[k])
    best_raw = raw[best_label]

    if best_raw < MIN_CONFIDENT_SCORE:
        scores = {k: 0.0 for k in raw}
        return (
            "unknown",
            0.0,
            scores,
            "No document-type signal passed the confidence floor "
            f"(best was '{best_label}' with {best_raw} points, "
            f"minimum {MIN_CONFIDENT_SCORE}).",
        )

    scores = {k: (v / total if total else 0.0) for k, v in raw.items()}
    confidence = scores[best_label]

    evidence = "; ".join(hits[best_label][:3]) or "no quotable span"
    rationale = (
        f"Matched {len(hits[best_label])} '{best_label}' signals "
        f"({best_raw} weighted points). Evidence: {evidence}"
    )
    return best_label, round(confidence, 4), {k: round(v, 4) for k, v in scores.items()}, rationale
