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
    """Real embeddings via sentence-transformers. Requires internet on first run."""

    def __init__(self, model_name: str = None):
        from sentence_transformers import SentenceTransformer  # lazy import

        self.model_name = model_name or Config.EMBEDDING_MODEL
        self.model = SentenceTransformer(self.model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()


class OCIGenerativeAIEmbedder(BaseEmbedder):
  
    def __init__(self, model_name: str = None):
        self.model_name = model_name or Config.EMBEDDING_MODEL
        self.dim = Config.EMBEDDING_DIM
        # TODO: initialize OCI Generative AI client here (auth via OCI IAM,
        # not API keys, per the project's architecture decisions)

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError(
            "OCI Generative AI embedding call not yet wired up. "
            "Coordinate with the AI Engineer for the client/config, then "
            "implement this method - the interface is already correct."
        )


def get_embedder() -> BaseEmbedder:
    """Factory: returns the embedder configured via EMBEDDING_BACKEND."""
    backend = Config.EMBEDDING_BACKEND
    if backend == "mock":
        return MockEmbedder()
    elif backend == "local_st":
        return LocalSentenceTransformerEmbedder()
    elif backend == "oci":
        return OCIGenerativeAIEmbedder()
    else:
        raise ValueError(f"Unknown EMBEDDING_BACKEND: {backend}")
