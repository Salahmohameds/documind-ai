import hashlib
import struct
from typing import List
from .config import Config


class BaseEmbedder:
    dim: int

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class MockEmbedder(BaseEmbedder):
   

    def __init__(self, dim: int = None):
        self.dim = dim or Config.EMBEDDING_DIM

    def embed(self, text: str) -> List[float]:
        vector = []
        seed = text.encode("utf-8")
        # derive `dim` pseudo-random-but-deterministic floats from a hash chain
        current = seed
        while len(vector) < self.dim:
            current = hashlib.sha256(current).digest()
            # unpack 8 floats (4 bytes each) per hash round
            for i in range(0, len(current) - 3, 4):
                if len(vector) >= self.dim:
                    break
                val = struct.unpack("I", current[i : i + 4])[0]
                vector.append((val % 20000 - 10000) / 10000.0)  # roughly [-1, 1]
        return vector


class LocalSentenceTransformerEmbedder(BaseEmbedder):

    def __init__(self, model_name: str = None):
        from sentence_transformers import SentenceTransformer  # lazy import

        self.model_name = model_name or Config.EMBEDDING_MODEL
        self.model = SentenceTransformer(self.model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()


class AIServiceEmbedder(BaseEmbedder):

    def __init__(self, base_url: str = None, timeout: float = None, max_batch: int = None):
        self.base_url = (base_url or Config.AI_SERVICE_URL).rstrip("/")
        self.timeout = timeout or Config.AI_SERVICE_TIMEOUT
        self.max_batch = max_batch or Config.AI_SERVICE_MAX_EMBED_BATCH
        self.dim = Config.EMBEDDING_DIM  # sanity-checked against server response below

    def _headers(self, request_id: str = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if request_id:
            headers["X-Request-ID"] = request_id
        if Config.AI_SERVICE_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {Config.AI_SERVICE_AUTH_TOKEN}"
        return headers

    def _call_embed(self, texts: List[str], input_type: str) -> List[List[float]]:
        import requests

        resp = requests.post(
            f"{self.base_url}/embed",
            json={"texts": texts, "input_type": input_type},
            headers=self._headers(),
            timeout=self.timeout,
        )

        if resp.status_code != 200:
            try:
                body = resp.json()
            except ValueError:
                body = resp.text
            raise RuntimeError(
                f"ai-service /embed failed: HTTP {resp.status_code} - {body}"
            )

        data = resp.json()
        server_dim = data.get("dim")
        if server_dim and server_dim != self.dim:
            raise RuntimeError(
                f"Embedding dimension mismatch: ai-service returned dim={server_dim}, "
                f"but EMBEDDING_DIM={self.dim} (search-service config / schema.sql). "
                f"A schema migration is required before switching backends - "
                f"see database/migrations/002_update_embedding_dim.sql template."
            )

        return data["embeddings"]

    def embed(self, text: str) -> List[float]:
        # Single text at query time -> input_type "query"
        return self._call_embed([text], input_type="query")[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Documents at index time -> input_type "document", chunked to
        # respect ai-service's MAX_EMBED_BATCH.
        results: List[List[float]] = []
        for i in range(0, len(texts), self.max_batch):
            batch = texts[i : i + self.max_batch]
            results.extend(self._call_embed(batch, input_type="document"))
        return results

OCIGenerativeAIEmbedder = AIServiceEmbedder


def get_embedder() -> BaseEmbedder:
    backend = Config.EMBEDDING_BACKEND
    if backend == "mock":
        return MockEmbedder()
    elif backend == "local_st":
        return LocalSentenceTransformerEmbedder()
    elif backend in ("ai_service", "oci"):  # "oci" kept as legacy alias
        return AIServiceEmbedder()
    else:
        raise ValueError(f"Unknown EMBEDDING_BACKEND: {backend}")
