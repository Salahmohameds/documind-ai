

from typing import List, Union
from .chunking import chunk_text, chunk_multi_page_document, Chunk
from .embeddings import get_embedder
from .vector_store import get_vector_store, SearchResult
from .config import Config

_embedder = None
_store = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = get_embedder()
    return _embedder


def _get_store():
    global _store
    if _store is None:
        _store = get_vector_store()
    return _store


def index_document(document_id: str, content: Union[str, List[str]]) -> int:
  
    if isinstance(content, list):
        chunks: List[Chunk] = chunk_multi_page_document(content, document_id)
    else:
        chunks = chunk_text(content, document_id=document_id)

    if not chunks:
        return 0

    embedder = _get_embedder()
    store = _get_store()

    texts = [c.text for c in chunks]
    embeddings = embedder.embed_batch(texts)

    for c, emb in zip(chunks, embeddings):
        store.add_chunk(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            text=c.text,
            embedding=emb,
            page=c.page,
        )

    return len(chunks)


def search(question: str, top_k: int = None) -> List[SearchResult]:
   
    embedder = _get_embedder()
    store = _get_store()

    query_embedding = embedder.embed(question)
    return store.search(query_embedding, top_k=top_k or Config.TOP_K)


def build_context_string(results: List[SearchResult]) -> str:
    lines = []
    for r in results:
        loc = f"{r.document_id}" + (f", page {r.page}" if r.page else "")
        lines.append(f"[Source: {loc}]\n{r.text}")
    return "\n\n".join(lines)
