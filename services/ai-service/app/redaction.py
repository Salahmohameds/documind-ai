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
from datetime import date


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


#: Egyptian governorate codes embedded at positions 8-9 of a national ID.
#: 88 means "born abroad".
_EG_GOVERNORATES = frozenset(
    {"01", "02", "03", "04"}
    | {f"{n:02d}" for n in range(11, 20)}
    | {f"{n:02d}" for n in range(21, 30)}
    | {f"{n:02d}" for n in range(31, 36)}
    | {"88"}
)


def _egypt_national_id_ok(digits: str) -> bool:
    """Structural check for an Egyptian national ID.

    14 digits: C YYMMDD GG SSSS X
      C   century - 2 for 1900s, 3 for 2000s
      YYMMDD  date of birth
      GG  governorate code
      SSSS sequence (last digit encodes gender)
      X   checksum

    This exists because Luhn is a *weak* signal at 14 digits: roughly one in
    ten national IDs passes it by chance, and those were being reported as
    CREDIT_CARD. Checking the century digit, a real calendar date and a real
    governorate code is far more specific than a checksum that was never meant
    to identify a number's type.
    """
    if len(digits) != 14 or digits[0] not in "23":
        return False

    century = 1900 if digits[0] == "2" else 2000
    year = century + int(digits[1:3])
    month = int(digits[3:5])
    day = int(digits[5:7])

    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False
    try:
        date(year, month, day)
    except ValueError:
        return False

    return digits[7:9] in _EG_GOVERNORATES


def _saudi_national_id_ok(digits: str) -> bool:
    """Saudi national ID: 10 digits starting 1 (citizen) or 2 (resident).

    Saudi mobile numbers start 05, so the leading digit separates the two
    cleanly enough for a redaction decision.
    """
    return len(digits) == 10 and digits[0] in "12"


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
        "SSN",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ),
    (
        # BEFORE credit cards on purpose. A 14-digit Egyptian national ID passes
        # the Luhn checksum roughly one time in ten, and while CREDIT_CARD was
        # checked first those IDs were reported as card numbers - reported by a
        # teammate, reproduced with 28503150212349. The structural validator is
        # far more specific than a checksum, so it gets first claim on the span.
        # Egypt: 14 digits. Saudi: 10 digits starting 1 or 2.
        "NATIONAL_ID",
        re.compile(r"\b(?:\d{14}|[12]\d{9})\b"),
    ),
    (
        "CREDIT_CARD",
        re.compile(r"\b(?:\d[ \-]?){13,19}\b"),
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
    (
        # Safety net, deliberately last. Tightening NATIONAL_ID and CREDIT_CARD
        # into precise validators made their labels correct but opened a hole:
        # a long digit run that is neither - a malformed ID, a foreign one, a
        # passport - matched nothing and left the cluster in the clear.
        #
        # This module's stated bias is that a false positive costs a slightly
        # worse prompt while a false negative leaks someone's identifier, so an
        # unclassified long digit run is redacted anyway. The label says only
        # that we could not tell what it was.
        "ID_NUMBER",
        re.compile(r"(?<![\d.\-])\d{9,19}(?![\d.\-])"),
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
        # Every major issuer range starts 3-6. Egyptian national IDs start 2 or
        # 3, so this rules out half of them outright, and NATIONAL_ID has
        # already had first claim on anything structurally valid.
        return 13 <= len(digits) <= 19 and digits[0] in "3456" and _luhn_ok(digits)
    if kind == "PHONE":
        return _PHONE_MIN_DIGITS <= len(digits) <= _PHONE_MAX_DIGITS
    if kind == "IP_ADDRESS":
        return all(0 <= int(part) <= 255 for part in value.split("."))
    if kind == "NATIONAL_ID":
        return _egypt_national_id_ok(digits) or _saudi_national_id_ok(digits)
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
