"""PDF text extraction, including the scanned-document case.

The scanned case matters more than the happy path: sending an empty string to a
model and persisting whatever comes back is the failure mode this guards.
"""

from __future__ import annotations

import pytest

from app.errors import InvalidDocumentError, NoTextLayerError
from app.extraction import pdf
from tests.conftest import build_pdf


def test_extracts_text_and_page_structure(sample_pdf):
    result = pdf.extract(sample_pdf)

    assert "MASTER SERVICES AGREEMENT" in result.text
    assert result.page_count == 1
    assert result.char_count == len(result.text)
    # Pages are kept separately so search-service can record a page per chunk.
    assert len(result.pages) == 1


def test_scanned_pdf_with_no_text_layer_is_terminal():
    # A valid PDF whose text extracts to almost nothing — what an image-only
    # scan looks like to pypdf.
    with pytest.raises(NoTextLayerError) as excinfo:
        pdf.extract(build_pdf("x"))

    assert excinfo.value.retryable is False
    assert "OCR is not supported" in str(excinfo.value)


def test_garbage_bytes_are_terminal():
    with pytest.raises(InvalidDocumentError):
        pdf.extract(b"this is definitely not a pdf")


def test_empty_object_is_terminal():
    with pytest.raises(InvalidDocumentError):
        pdf.extract(b"")


def test_normalisation_strips_nulls_and_collapses_whitespace():
    # NUL bytes break Postgres TEXT inserts; PDF extractors emit them.
    assert pdf._normalise("a\x00b   c\n\n\n\nd") == "ab c\n\nd"
