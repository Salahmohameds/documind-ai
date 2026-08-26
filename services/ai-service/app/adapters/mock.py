"""Offline provider - the DEFAULT backend.

This is not a stub. It is a working implementation that lets the whole platform
be built, tested, load-tested and demonstrated with no OCI credential, no API
key and no network access. Roles 3, 5, 6 and 8 are unblocked by this file while
decision D1 (which AI provider) is still open.

Two properties make it useful rather than decorative:

**Embeddings carry real lexical signal.** Feature hashing over word unigrams
and bigrams, L2-normalised. Documents that share vocabulary land near each
other, so ``/query`` returns plausible chunks and the pipeline can be exercised
end to end. Compare with the SHA-256 hash chain in search-service's own
MockEmbedder, where cosine similarity is pure noise.

**Answers are extractive and genuinely grounded.** ``/answer`` selects the
sentence with the strongest lexical overlap with the question and cites the
chunk it came from, using the same ``[n]`` marker format a real model is
prompted to emit - so one citation parser serves both paths.

What it is NOT
--------------
It is not a language model, and no retrieval or answer-quality metric measured
against it may be reported as a result. ``tests/rag-evaluation`` enforces that
in code rather than trusting a note in a README.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from app.adapters.base import AIProvider, ChatMessage, ChatResult, EmbedResult, estimate_tokens
from app.analysis import classify_rules
from app.analysis.text import overlap_score, sentences, tokenize

#: Below this lexical overlap the mock refuses instead of guessing. An honest
#: refusal is a correct outcome and the evaluation harness scores it as one.
ANSWER_MIN_OVERLAP = 0.15


class MockProvider(AIProvider):
    name = "mock"
    is_external = False  # no egress: nothing to redact, nothing to bill

    def __init__(self, model_name: str, embedding_model: str, embedding_dim: int) -> None:
        self._chat_model = model_name
        self._embed_model = embedding_model
        self._dim = embedding_dim

    # -- identity ---------------------------------------------------------
    @property
    def chat_model(self) -> str:
        return self._chat_model

    @property
    def embed_model(self) -> str:
        return self._embed_model

    @property
    def embed_dim(self) -> int:
        return self._dim

    def probe(self) -> bool:
        return True  # always reachable; it is in-process

    # -- embeddings -------------------------------------------------------
    def embed(self, texts: list[str], *, input_type: str = "document") -> EmbedResult:
        # input_type is intentionally ignored: documents and queries MUST land
        # in the same space or retrieval silently returns nothing.
        vectors = [self._hash_embed(t) for t in texts]
        return EmbedResult(
            vectors=vectors,
            dim=self._dim,
            model=self._embed_model,
            tokens_in=sum(estimate_tokens(t) for t in texts),
            estimated=True,
        )

    def _hash_embed(self, text: str) -> list[float]:
        """Signed feature hashing over unigrams + bigrams, L2-normalised."""
        vector = [0.0] * self._dim
        tokens = tokenize(text)
        if not tokens:
            return vector

        features = list(tokens)
        features.extend(f"{a}_{b}" for a, b in zip(tokens, tokens[1:]))

        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self._dim
            sign = 1.0 if (value >> 63) & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0.0:
            vector = [v / norm for v in vector]
        return vector

    # -- chat -------------------------------------------------------------
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        task: str = "generic",
        context: dict[str, Any] | None = None,
    ) -> ChatResult:
        context = context or {}
        handler = {
            "answer": self._task_answer,
            "risk_explain": self._task_risk_explain,
            "classify": self._task_classify,
            "extract": self._task_extract,
        }.get(task, self._task_generic)

        text = handler(context)
        tokens_in = sum(estimate_tokens(m.content) for m in messages)
        return ChatResult(
            text=text,
            model=self._chat_model,
            tokens_in=tokens_in,
            tokens_out=estimate_tokens(text),
            estimated=True,
            raw={"task": task},
        )

    # -- task implementations --------------------------------------------
    def _task_answer(self, context: dict[str, Any]) -> str:
        """Extractive QA over the supplied chunks, with real citations."""
        question: str = context.get("question", "")
        chunks: list[dict[str, Any]] = context.get("chunks", [])
        if not question or not chunks:
            return "I could not find an answer in the provided documents."

        q_tokens = tokenize(question)
        best_text = ""
        best_score = 0.0
        best_index = 0

        for index, chunk in enumerate(chunks, start=1):
            for _offset, sentence in sentences(chunk.get("text", "")):
                score = overlap_score(q_tokens, sentence)
                if score > best_score:
                    best_score, best_text, best_index = score, sentence, index

        if best_score < ANSWER_MIN_OVERLAP or not best_text:
            return "I could not find an answer in the provided documents."

        return f"{best_text.strip()} [{best_index}]"

    def _task_risk_explain(self, context: dict[str, Any]) -> str:
        """Deterministic narrative built from the rules that actually fired."""
        score = context.get("score", 0)
        band = context.get("band", "low")
        findings: list[dict[str, Any]] = context.get("findings", [])

        if not findings:
            return (
                f"No risk rules matched this document. Calibrated score {score}/100 "
                f"({band} risk). Note that an absence of findings reflects the rule "
                f"set, not a legal opinion."
            )

        highs = [f for f in findings if f.get("severity") == "high"]
        leading = ", ".join(f.get("title", "") for f in findings[:3])
        parts = [
            f"Calibrated score {score}/100 ({band} risk), from "
            f"{len(findings)} rule(s) that matched."
        ]
        if highs:
            parts.append(
                f"{len(highs)} high-severity finding(s) dominate the score: "
                + ", ".join(f.get("title", "") for f in highs)
                + "."
            )
        parts.append(f"Leading contributors: {leading}.")
        parts.append(
            "Each finding cites the clause that triggered it; the score is a "
            "weighted sum of matched rules, not a model judgement."
        )
        return " ".join(parts)

    def _task_classify(self, context: dict[str, Any]) -> str:
        """Return the rule engine's verdict in the JSON shape a model emits."""
        text = context.get("text", "")
        label, confidence, _scores, rationale = classify_rules.classify(text)
        return json.dumps({"label": label, "confidence": confidence, "rationale": rationale})

    def _task_extract(self, _context: dict[str, Any]) -> str:
        # The regex engine has already produced every field it can find, and the
        # mock has no additional knowledge to contribute.
        return "{}"

    def _task_generic(self, context: dict[str, Any]) -> str:
        return context.get(
            "fallback",
            "This response was produced by the offline mock provider "
            "(AI_BACKEND=mock). No language model was called.",
        )
