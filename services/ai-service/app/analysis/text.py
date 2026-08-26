"""Small deterministic text utilities shared by the local analysis engines.

No third-party NLP dependency on purpose: these run inside the request path of
a service that must start with no network access and a small image.
"""

from __future__ import annotations

import math
import re

# Apostrophes are excluded deliberately. Legal text is full of possessives -
# "Provider's total liability" - and keeping the apostrophe makes "provider's"
# a different token from "provider", so a question about the Provider fails to
# match the one sentence that answers it. Splitting leaves a stray "s", which
# the stop-word list absorbs.
_WORD_RE = re.compile(r"[a-z0-9]+")

# Deliberately short. A large stop-word list would be a dependency; these are
# the words that actually distort short-query lexical overlap.
_STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those of in on at to for
    from by with without is are was were be been being it its as such any all
    what when where which who whom how does do did there here their his her
    s t
    """.split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stop-words removed."""
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS]


def unwrap(text: str) -> str:
    """Join soft-wrapped lines, preserving every character offset.

    Documents wrap sentences across lines. A splitter that treats a newline as
    a boundary either mangles those sentences or - worse - drops them: a line
    that ends in a soft newline never reaches a terminator, so a naive pattern
    skips it silently. That cost us the one sentence in the sample contract
    that states the liability cap.

    Single newlines become spaces and double newlines are left as paragraph
    breaks. The substitution is length-preserving, so offsets computed here
    still index correctly into the original text.
    """
    return re.sub(r"(?<!\n)\n(?!\n)", " ", text)


def sentences(text: str) -> list[tuple[int, str]]:
    """Split into ``(offset, sentence)`` pairs, preserving source offsets.

    Offsets are kept so every extracted value and risk finding can point back
    at the exact span of the source document. Evidence that cannot be located
    in the source is evidence we refuse to report.
    """
    flat = unwrap(text)
    out: list[tuple[int, str]] = []
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n{2,}|$)", flat):
        raw = match.group()
        stripped = raw.strip()
        if not stripped:
            continue
        offset = match.start() + (len(raw) - len(raw.lstrip()))
        out.append((offset, stripped))
    return out


def overlap_score(question_tokens: list[str], candidate: str) -> float:
    """Jaccard-ish lexical overlap, normalised by the question length.

    Used by the mock provider for extractive answering and by the extraction
    engine to rank candidate spans. It is a retrieval heuristic, not a
    semantic model - and it is labelled as such everywhere it surfaces.
    """
    if not question_tokens:
        return 0.0
    cand = set(tokenize(candidate))
    if not cand:
        return 0.0
    hits = sum(1 for t in set(question_tokens) if t in cand)
    return hits / len(set(question_tokens))


def snippet(text: str, offset: int, length: int = 240) -> str:
    """A readable window of the source around ``offset``."""
    start = max(0, offset)
    end = min(len(text), start + length)
    out = text[start:end].strip()
    if end < len(text):
        out += "..."
    return " ".join(out.split())


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity - used by tests to prove the mock embedder is sane."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
