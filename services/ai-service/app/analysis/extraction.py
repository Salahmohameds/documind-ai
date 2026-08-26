"""Deterministic field extraction with source-anchored evidence.

Design rule: **a value we cannot locate in the source document is not a value.**

Every field returned carries the character offset and a quoted snippet from the
input. That applies to model-produced values too - :func:`verify_against_source`
searches the document for whatever the model claimed and drops the confidence
(and the evidence) when it is not there. It is a cheap, effective guard against
a model inventing an invoice total.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.analysis.text import snippet

RULES_VERSION = "extract-1.0"

_DATE = (
    r"(\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|(?:January|February|March|April|May|June|July|August|September|October"
    r"|November|December)\s+\d{1,2},?\s+\d{4})"
)
_CCY = r"USD|EUR|GBP|EGP|SAR|AED"
# Currency can lead ("EGP 980", "$980.00") or trail ("980 EGP"). Both appear in
# real invoices and the trailing form is the norm in the region this project
# targets, so it is not an edge case.
_MONEY = (
    rf"((?:{_CCY}|[$€£])\s?[\d,]+(?:\.\d{{2}})?"
    rf"|[\d,]+(?:\.\d{{2}})?\s?(?:{_CCY})"
    rf"|[\d,]+\.\d{{2}})"
)


@dataclass(frozen=True)
class FieldSpec:
    name: str
    patterns: tuple[str, ...]
    #: Confidence assigned when the first pattern matches. Later patterns are
    #: progressively weaker fallbacks and get scaled down.
    confidence: float = 0.9


@dataclass
class ExtractedValue:
    value: str | None
    confidence: float
    offset: int | None = None
    snippet: str | None = None


_INVOICE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("invoice_number", (r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Za-z0-9\-/]{3,})",)),
    # No loose `date:` fallback here on purpose: on an invoice that carries only
    # a "Due Date", the generic pattern happily reports the due date as the
    # invoice date. A confident wrong value is worse than an honest null.
    FieldSpec("invoice_date", (rf"invoice\s+date\s*[:\-]?\s*{_DATE}", rf"date\s+of\s+issue\s*[:\-]?\s*{_DATE}")),
    FieldSpec("due_date", (rf"due\s+date\s*[:\-]?\s*{_DATE}", rf"payable\s+by\s+{_DATE}")),
    FieldSpec("purchase_order", (r"(?:purchase\s+order|p\.?o\.?)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Za-z0-9\-/]{3,})",)),
    FieldSpec("subtotal", (rf"subtotal\s*[:\-]?\s*{_MONEY}",)),
    FieldSpec("tax", (rf"(?:tax|vat)\s*(?:\([\d.]+%\))?\s*[:\-]?\s*{_MONEY}",)),
    FieldSpec("total_amount", (rf"(?:total\s+due|amount\s+due|grand\s+total|balance\s+due)\s*[:\-]?\s*{_MONEY}", rf"\btotal\s*[:\-]?\s*{_MONEY}")),
    FieldSpec("currency", (r"\b(USD|EUR|GBP|EGP|SAR|AED)\b",)),
    FieldSpec("bill_to", (r"bill\s+to\s*[:\-]?\s*\n?\s*([^\n]{3,80})",)),
    FieldSpec("vendor_name", (r"(?:from|remit\s+to|vendor|supplier)\s*[:\-]?\s*\n?\s*([^\n]{3,80})",)),
    FieldSpec("payment_terms", (r"(net\s*\d+\s*(?:days)?|payment\s+(?:is\s+)?due\s+within\s+\d+\s+days)",)),
)

_CONTRACT_FIELDS: tuple[FieldSpec, ...] = (
    # [\s\S] rather than . : the parties clause almost always wraps across
    # lines, and a dot-based pattern silently finds nothing on real documents.
    FieldSpec(
        "parties",
        (
            r"between\s+([\s\S]{5,200}?)(?:,\s*collectively|\.\s|\n\s*\n)",
            r"by\s+and\s+between\s+([\s\S]{5,200}?)(?:\.\s|\n\s*\n)",
        ),
    ),
    FieldSpec("effective_date", (rf"(?:effective\s+(?:as\s+of\s+|date\s*[:\-]?\s*)|commences?\s+on\s+)\s*{_DATE}",)),
    FieldSpec("expiry_date", (rf"(?:until|expires?\s+on|through|in\s+effect\s+until)\s+{_DATE}",)),
    FieldSpec("term_length", (r"(?:term\s+of|for\s+a\s+period\s+of)\s+((?:one|two|three|four|five|\d+)\s+(?:year|month)s?)",)),
    FieldSpec("governing_law", (r"governed\s+by\s+(?:and\s+construed\s+in\s+accordance\s+with\s+)?the\s+laws\s+of\s+([A-Za-z ,\.]{3,60})",)),
    FieldSpec("termination_notice_days", (r"(\d+)\s+days[’']?\s+(?:prior\s+)?written\s+notice",)),
    FieldSpec("payment_terms", (r"(?:payment\s+(?:is\s+)?due\s+within\s+(\d+)\s+days|net\s+(\d+))",)),
    FieldSpec("liability_cap", (r"(?:shall\s+not\s+exceed|liability[^.]{0,40}?exceed)\s+([^.;]{3,120})",)),
    FieldSpec("late_payment_interest", (r"([\d.]+\s*%\s*per\s+month)",)),
    # Legal drafting spells the number then repeats it: "two (2) years".
    FieldSpec(
        "confidentiality_period",
        (r"((?:one|two|three|four|five|\d+)\s*(?:\(\d+\)\s*)?years?)\s+(?:following|after)\s+(?:the\s+)?termination",),
    ),
    FieldSpec("auto_renewal", (r"(automatic(?:ally)?\s+renew\w*|auto[- ]?renew\w*)",)),
)

_RECEIPT_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("merchant", (r"(?:merchant|store)\s*[:\-]?\s*([^\n]{3,60})",)),
    FieldSpec("transaction_id", (r"transaction\s*(?:id|no\.?|#)\s*[:\-]?\s*([A-Za-z0-9\-]{3,})",)),
    FieldSpec("total_amount", (rf"(?:total|amount)\s*[:\-]?\s*{_MONEY}",)),
    FieldSpec("date", (rf"\bdate\s*[:\-]?\s*{_DATE}", _DATE)),
)

# Keyed by the labels /classify can actually return. A receipt field set exists
# below but is unreachable by design: 'receipt' is not a storable document type
# (see classify_rules.STORABLE_LABELS), so those documents come through as
# 'unknown' and extract nothing rather than being mislabelled as invoices.
FIELD_SETS: dict[str, tuple[FieldSpec, ...]] = {
    "invoice": _INVOICE_FIELDS,
    "contract": _CONTRACT_FIELDS,
    "unknown": (),
}


def field_names_for(document_type: str) -> list[str]:
    return [spec.name for spec in FIELD_SETS.get(document_type, ())]


def extract(
    text: str,
    document_type: str,
    fields: list[str] | None = None,
) -> dict[str, ExtractedValue]:
    """Run the field set for ``document_type`` over ``text``.

    Fields that do not match are still returned, with ``value=None`` and
    ``confidence=0.0`` - an explicit "not found" is more useful to the caller
    than a missing key, and it keeps the response shape stable.
    """
    specs = FIELD_SETS.get(document_type, ())
    if fields:
        wanted = set(fields)
        specs = tuple(s for s in specs if s.name in wanted)

    out: dict[str, ExtractedValue] = {}

    for spec in specs:
        found = ExtractedValue(value=None, confidence=0.0)
        for index, pattern in enumerate(spec.patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            # First non-empty capture group, else the whole match.
            value = next((g for g in match.groups() if g), match.group(0))
            value = " ".join(value.split()).strip(" .,:;")
            if not value:
                continue
            # Each fallback pattern is a weaker signal than the one before it.
            confidence = round(spec.confidence * (0.85**index), 4)
            found = ExtractedValue(
                value=value,
                confidence=confidence,
                offset=match.start(),
                snippet=snippet(text, max(0, match.start() - 30), 200),
            )
            break
        out[spec.name] = found

    # Booleans read better as yes/no than as the matched phrase.
    if "auto_renewal" in out:
        av = out["auto_renewal"]
        out["auto_renewal"] = ExtractedValue(
            value="yes" if av.value else "no",
            confidence=av.confidence if av.value else 0.6,
            offset=av.offset,
            snippet=av.snippet,
        )

    return out


def verify_against_source(value: str, text: str) -> tuple[bool, int | None, str | None]:
    """Locate a model-produced ``value`` inside the source document.

    Returns ``(found, offset, snippet)``. Matching is whitespace-insensitive
    because models reflow text. A value that cannot be found is reported as
    unverified rather than silently trusted.
    """
    if not value:
        return False, None, None

    needle = " ".join(value.split())
    idx = text.find(needle)
    if idx == -1:
        idx = text.lower().find(needle.lower())
    if idx == -1:
        # Whitespace-tolerant search as a last resort.
        pattern = r"\s+".join(re.escape(tok) for tok in needle.split())
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return False, None, None
        idx = match.start()

    return True, idx, snippet(text, max(0, idx - 30), 200)
