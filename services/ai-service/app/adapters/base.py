"""The provider interface every backend implements.

One interface, three implementations (mock / OCI Generative AI / OpenAI-
compatible). Swapping providers is an environment-variable change, never a code
change - that is the whole point of ADR-006's adapter layer.

About the ``task`` and ``context`` arguments on :meth:`AIProvider.chat`
--------------------------------------------------------------------
Real providers ignore both. They exist so the **mock** provider can stay a
genuinely useful offline implementation instead of returning lorem ipsum: it
routes on ``task`` to a deterministic local engine and produces output that is
correct for the document in front of it. That is what lets roles 3, 5, 6 and 8
build and test the whole pipeline while decision D1 is still open.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass
class ChatResult:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    # True when the counts are a local estimate rather than provider-reported.
    estimated: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbedResult:
    vectors: list[list[float]]
    dim: int
    model: str
    tokens_in: int = 0
    estimated: bool = False


def estimate_tokens(text: str) -> int:
    """Cheap local token estimate: ~4 characters per token.

    Used for budget enforcement *before* a call is made (you cannot ask the
    provider how much a request will cost without making it) and as the
    reported count for providers that do not return usage. Anything derived
    from this is flagged ``estimated=True`` so no report can quietly present an
    estimate as a measurement.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


class AIProvider(ABC):
    """Base class for every model backend."""

    #: Short stable identifier used in logs, metrics labels and responses.
    name: str = "base"

    #: True when calls leave the cluster. Drives PII redaction and egress logs.
    is_external: bool = True

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        task: str = "generic",
        context: dict[str, Any] | None = None,
    ) -> ChatResult:
        """Single-turn completion. Implementations must be thread-safe."""

    @abstractmethod
    def embed(
        self,
        texts: list[str],
        *,
        input_type: str = "document",
    ) -> EmbedResult:
        """Embed a batch of texts. Implementations must be thread-safe."""

    @abstractmethod
    def probe(self) -> bool:
        """Cheap reachability check used by /readiness.

        MUST NOT perform a billable generation call. Implementations should
        prefer a metadata/list operation, and must return ``False`` rather than
        raising when the provider is unreachable.
        """

    @property
    @abstractmethod
    def chat_model(self) -> str:
        """Model identifier reported in responses and metrics."""

    @property
    @abstractmethod
    def embed_model(self) -> str:
        """Embedding model identifier reported in responses and metrics."""

    @property
    @abstractmethod
    def embed_dim(self) -> int:
        """Embedding dimensionality. Must match the vector column in Postgres."""
