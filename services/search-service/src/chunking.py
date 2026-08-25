from dataclasses import dataclass, field
from typing import List, Optional
from .config import Config


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    page: Optional[int] = None
    metadata: dict = field(default_factory=dict)


def chunk_text(
    text: str,
    document_id: str,
    page: Optional[int] = None,
    chunk_size: int = None,
    overlap: int = None,
) -> List[Chunk]:
   
    chunk_size = chunk_size or Config.CHUNK_SIZE
    overlap = overlap or Config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks: List[Chunk] = []
    start = 0
    index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            search_window_start = start + int(chunk_size * 0.8)
            boundary = -1
            for sep in [". ", ".\n", "\n\n", "\n"]:
                pos = text.rfind(sep, search_window_start, end)
                if pos != -1:
                    boundary = pos + len(sep)
                    break
            if boundary != -1:
                end = boundary

        piece = text[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}_chunk_{index}",
                    document_id=document_id,
                    text=piece,
                    chunk_index=index,
                    page=page,
                )
            )
            index += 1

        if end >= len(text):
            break
        start = end - overlap  # step forward, keeping overlap

    return chunks


def chunk_multi_page_document(pages: List[str], document_id: str) -> List[Chunk]:
  
    all_chunks: List[Chunk] = []
    running_index = 0
    for page_num, page_text in enumerate(pages, start=1):
        page_chunks = chunk_text(page_text, document_id=document_id, page=page_num)
        for c in page_chunks:
            c.chunk_index = running_index
            c.chunk_id = f"{document_id}_chunk_{running_index}"
            running_index += 1
        all_chunks.extend(page_chunks)
    return all_chunks
