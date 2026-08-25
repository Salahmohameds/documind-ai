import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
import numpy as np

from .config import Config


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    text: str
    page: Optional[int]
    similarity: float


class BaseVectorStore:
    def add_chunk(self, chunk_id, document_id, text, embedding, page=None):
        raise NotImplementedError

    def add_chunks_batch(self, chunks_with_embeddings):
        for c in chunks_with_embeddings:
            self.add_chunk(**c)

    def search(self, query_embedding, top_k: int = None) -> List[SearchResult]:
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class InMemoryVectorStore(BaseVectorStore):

    def __init__(self, path: str = None):
        self.path = path or Config.LOCAL_STORE_PATH
        self._records = []
        if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, "r") as f:
                try:
                    self._records = json.load(f)
                except json.JSONDecodeError:
                    self._records = []

    def _persist(self):
        with open(self.path, "w") as f:
            json.dump(self._records, f)

    def add_chunk(self, chunk_id, document_id, text, embedding, page=None):
        self._records.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "text": text,
                "page": page,
                "embedding": list(embedding),
            }
        )
        self._persist()

    def search(self, query_embedding, top_k: int = None) -> List[SearchResult]:
        top_k = top_k or Config.TOP_K
        if not self._records:
            return []

        q = np.array(query_embedding, dtype=float)
        q_norm = np.linalg.norm(q) or 1e-8

        scored = []
        for rec in self._records:
            v = np.array(rec["embedding"], dtype=float)
            v_norm = np.linalg.norm(v) or 1e-8
            cosine_sim = float(np.dot(q, v) / (q_norm * v_norm))
            scored.append((cosine_sim, rec))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            SearchResult(
                chunk_id=rec["chunk_id"],
                document_id=rec["document_id"],
                text=rec["text"],
                page=rec.get("page"),
                similarity=round(sim, 4),
            )
            for sim, rec in scored[:top_k]
        ]

    def clear(self):
        self._records = []
        self._persist()

    def count(self) -> int:
        return len(self._records)


class PostgresVectorStore(BaseVectorStore):

    def __init__(self):
        import psycopg2  # lazy import so `memory` backend never needs this installed

        self.conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
        )
        self.conn.autocommit = True

    def add_chunk(self, chunk_id, document_id, text, embedding, page=None):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_chunks (chunk_id, document_id, page, text, embedding)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE
                    SET text = EXCLUDED.text, embedding = EXCLUDED.embedding
                """,
                (chunk_id, document_id, page, text, list(embedding)),
            )

    def search(self, query_embedding, top_k: int = None) -> List[SearchResult]:
        top_k = top_k or Config.TOP_K
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_id, document_id, text, page,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (list(query_embedding), list(query_embedding), top_k),
            )
            rows = cur.fetchall()
        return [
            SearchResult(
                chunk_id=r[0], document_id=r[1], text=r[2], page=r[3],
                similarity=round(float(r[4]), 4),
            )
            for r in rows
        ]

    def clear(self):
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE document_chunks")

    def count(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM document_chunks")
            return cur.fetchone()[0]


def get_vector_store() -> BaseVectorStore:
    """Factory: returns the vector store configured via VECTOR_STORE_BACKEND."""
    backend = Config.VECTOR_STORE_BACKEND
    if backend == "memory":
        return InMemoryVectorStore()
    elif backend == "postgres":
        return PostgresVectorStore()
    else:
        raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {backend}")
