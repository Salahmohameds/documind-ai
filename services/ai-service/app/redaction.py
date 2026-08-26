"""PII detection and redaction, applied before any text leaves the cluster.

This is the security control behind the claim role 7 gets to make in the threat
model: *customer document content never leaves the cluster in identifiable
form.* It runs in :mod:`app.pipeline` ahead of every external provider call and
is skipped only for the mock provider, which performs no egress at all.

What is redacted, and what deliberately is not
----------------------------------------------
Redaction targets **personal** identifiers - email addresses, phone numbers,
payment instruments, government IDs, IPs.

It does **not** touch business fields: invoice numbers, totals, dates, party
names as they appear in a contract's operative text. Redacting those would
destroy the extraction the product exists to perform, and they are not personal
data. That line is a decision, and it is written down here so it can be argued
with rather than discovered.

Bias
----
Patterns are tuned to over-redact rather than under-redact. A false positive
costs a slightly less useful prompt; a false negative sends someone's card
number to a third party. Where the two conflict, over-redaction wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Match:
    type: str
    placeholder: str
    start: int
    end: int
    value: str


@dataclass
class RedactionResult:
    text: str
    matches: list[Match] = field(default_factory=list)
    #: placeholder -> original value. Lives for the duration of one request and
    #: is never logged, persisted, or returned unless explicitly requested.
    mapping: dict[str, str] = field(default_factory=dict)

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for m in self.matches:
            out[m.type] = out.get(m.type, 0) + 1
        return out

    def restore(self, text: str) -> str:
        """Substitute original values back into model output.

        Used when a placeholder legitimately belongs in the answer (for example
        a RAG answer quoting a contact address). Applied to text coming *back*
        from the provider, never to text going out.
        """
        for placeholder, original in self.mapping.items():
            text = text.replace(placeholder, original)
        return text


def _luhn_ok(digits: str) -> bool:
    """Luhn checksum - keeps long invoice/reference numbers out of CARD hits."""
    total = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        digit = int(char)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


# Spans that are claimed BEFORE any PII pattern runs, and never redacted.
#
# Dates are the important one. "2026-09-01" is eight digits with separators,
# which is a perfectly good phone number as far as a regex is concerned - so
# the loose PHONE pattern swallowed every date on every invoice and contract,
# destroying exactly the fields extraction depends on. Reserving date shapes
# first is more robust than trying to make PHONE clever enough to decline them.
_RESERVED: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # ISO
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),  # DD/MM/YYYY and friends
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September"
        r"|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
)

# Order matters: earlier patterns claim their spans first, so the more specific
# identifiers (IBAN, card, IP) win over the looser numeric ones. PHONE is
# deliberately last of the numeric patterns because it is the greediest.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "IBAN",
        re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    ),
    (
        "CREDIT_CARD",
        re.compile(r"\b(?:\d[ \-]?){13,19}\b"),
    ),
    (
        "SSN",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ),
    (
        # Egypt: 14 digits. Saudi: 10 digits starting 1 or 2.
        "NATIONAL_ID",
        re.compile(r"\b(?:\d{14}|[12]\d{9})\b"),
    ),
    (
        "IP_ADDRESS",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    ),
    (
        "PHONE",
        re.compile(
            r"(?<![\w.])(?:\+\d{1,3}[\s\-.]?)?(?:\(\d{1,4}\)[\s\-.]?)?"
            r"\d{2,4}(?:[\s\-.]\d{2,4}){1,3}(?![\w.])"
        ),
    ),
)

#: Digit-count window in which PHONE is plausible. Outside it the match is
#: almost always a reference number, an amount, or a date range.
_PHONE_MIN_DIGITS = 7
_PHONE_MAX_DIGITS = 15


def _accept(kind: str, value: str) -> bool:
    """Second-stage validation to suppress the obvious false positives."""
    digits = re.sub(r"\D", "", value)

    if kind == "CREDIT_CARD":
        return 13 <= len(digits) <= 19 and _luhn_ok(digits)
    if kind == "PHONE":
        return _PHONE_MIN_DIGITS <= len(digits) <= _PHONE_MAX_DIGITS
    if kind == "IP_ADDRESS":
        return all(0 <= int(part) <= 255 for part in value.split("."))
    if kind == "NATIONAL_ID":
        return len(digits) in (10, 14)
    return True


def detect(text: str) -> list[Match]:
    """Find PII spans. Overlapping matches are resolved by pattern order."""
    claimed: list[tuple[int, int]] = []
    matches: list[Match] = []
    counters: dict[str, int] = {}

    def overlaps(start: int, end: int) -> bool:
        return any(start < c_end and end > c_start for c_start, c_end in claimed)

    # Reserve non-PII spans first so no pattern can claim them.
    for reserved in _RESERVED:
        for match in reserved.finditer(text):
            claimed.append((match.start(), match.end()))

    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            value = match.group()
            if not _accept(kind, value):
                continue
            if overlaps(match.start(), match.end()):
                continue
            counters[kind] = counters.get(kind, 0) + 1
            matches.append(
                Match(
                    type=kind,
                    placeholder=f"[{kind}_{counters[kind]}]",
                    start=match.start(),
                    end=match.end(),
                    value=value,
                )
            )
            claimed.append((match.start(), match.end()))

    matches.sort(key=lambda m: m.start)
    return matches


def redact(text: str) -> RedactionResult:
    """Replace every detected PII span with a stable placeholder.

    Placeholders are numbered per type, so a document mentioning the same email
    twice yields two placeholders - the model still sees that two references
    exist without seeing the value.
    """
    matches = detect(text)
    if not matches:
        return RedactionResult(text=text, matches=[], mapping={})

    out: list[str] = []
    cursor = 0
    mapping: dict[str, str] = {}

    for match in matches:
        out.append(text[cursor : match.start])
        out.append(match.placeholder)
        mapping[match.placeholder] = match.value
        cursor = match.end
    out.append(text[cursor:])

    return RedactionResult(text="".join(out), matches=matches, mapping=mapping)
