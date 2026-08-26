"""PDF text extraction.

The one piece of real document processing the worker owns itself — everything
else is orchestration. Per the proposal §7, ``processing-service`` is
responsible for "text extraction"; ai-service receives text and never bytes.

Scope, stated plainly: **PDFs with a text layer.** A scanned, image-only PDF
produces no text, and this raises ``NoTextLayerError`` rather than sending an
empty string to a model and persisting whatever it hallucinates from nothing.
OCR would need tesseract in the image or OCI Vision behind another adapter;
neither is in scope, and failing honestly is the correct behaviour until one is.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import settings
from app.errors import InvalidDocumentError, NoTextLayerError

logger = logging.getLogger(settings.service_name)

# Collapse the runs of whitespace PDF layout extraction produces. Left as one
# pass over the page rather than per-line so a table does not become one word.
_WHITESPACE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass
class ExtractedDocument:
    """Text plus the structure downstream services need.

    ``pages`` is kept alongside ``text`` because search-service stores a page
    number per chunk (``document_chunks.page``); flattening to one string here
    would throw away the citation detail the RAG answers depend on.
    """

    text: str
    pages: list[str] = field(default_factory=list)
    page_count: int = 0
    char_count: int = 0
    encrypted: bool = False


def extract(data: bytes) -> ExtractedDocument:
    """Extract text from PDF bytes.

    Raises:
        InvalidDocumentError: not a parseable PDF (terminal).
        NoTextLayerError: parseable, but effectively no text (terminal).
    """
    if not data:
        raise InvalidDocumentError("The stored object is empty")

    try:
        reader = PdfReader(io.BytesIO(data))
    except (PdfReadError, OSError, ValueError) as exc:
        raise InvalidDocumentError(f"Could not parse the PDF: {exc}") from exc

    encrypted = bool(getattr(reader, "is_encrypted", False))
    if encrypted:
        # An empty user password is common for "print-protected" PDFs and
        # decrypts fine. A real password is a terminal failure — we have no
        # way to obtain one, and no attempt count will change that.
        try:
            if reader.decrypt("") == 0:
                raise InvalidDocumentError(
                    "The PDF is password-protected and cannot be read"
                )
        except InvalidDocumentError:
            raise
        except Exception as exc:
            raise InvalidDocumentError(
                f"The PDF is encrypted and could not be decrypted: {exc}"
            ) from exc

    pages: list[str] = []
    for index, page in enumerate(reader.pages):
        try:
            raw = page.extract_text() or ""
        except Exception as exc:
            # One malformed page should not lose the other thirty-nine.
            logger.warning(
                "page_extraction_failed",
                extra={"page": index + 1, "error": str(exc)},
            )
            raw = ""
        pages.append(_normalise(raw))

    text = "\n\n".join(page for page in pages if page).strip()

    if len(text) < settings.min_extracted_chars:
        raise NoTextLayerError(
            f"Extracted only {len(text)} characters from {len(pages)} page(s). "
            "The document appears to be a scan with no text layer; OCR is not "
            "supported."
        )

    return ExtractedDocument(
        text=text,
        pages=pages,
        page_count=len(pages),
        char_count=len(text),
        encrypted=encrypted,
    )


def _normalise(raw: str) -> str:
    """Tidy extractor output without destroying paragraph structure."""
    # PDF text frequently arrives with a NUL or two; they break Postgres TEXT
    # inserts and JSON encoding alike.
    cleaned = raw.replace("\x00", "")
    cleaned = _WHITESPACE.sub(" ", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    cleaned = _BLANK_LINES.sub("\n\n", cleaned)
    return cleaned.strip()
