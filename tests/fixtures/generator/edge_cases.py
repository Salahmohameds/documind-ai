"""Malformed and boundary-case documents.

The main generator produces well-formed documents. These are the ones
that break things: files that claim to be PDFs and are not, files with
no text to extract, files large enough to hit limits, and filenames
crafted to escape a storage directory.

Every case is generated rather than committed, so the repo carries no
binary blobs and no file that a scanner would flag.

    python edge_cases.py

Writes to tests/fixtures/edge-cases/ alongside a manifest describing
what each file is and what should happen to it.
"""

import json
import os
import zlib

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "edge-cases")


def _valid_pdf_bytes(pages=1, text="Edge case document."):
    """A minimal but genuinely valid PDF, in memory."""
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i in range(pages):
        c.setFont("Courier", 10)
        c.drawString(20 * mm, 270 * mm, f"{text} Page {i + 1}.")
        c.showPage()
    c.save()
    return buf.getvalue()


def case_empty(path):
    """Zero bytes. Nothing to validate, nothing to extract."""
    open(path, "wb").close()
    return {
        "what": "zero-byte file with a .pdf extension",
        "expected": "rejected at upload — no magic bytes to check",
    }


def case_not_a_pdf(path):
    """Plain text wearing a .pdf extension.

    Extension checks alone let this through; magic-byte checks do not.
    """
    with open(path, "wb") as f:
        f.write(b"This is plain text pretending to be a PDF.\n" * 20)
    return {
        "what": "text file named .pdf",
        "expected": "rejected — no %PDF- header",
    }


def case_truncated(path):
    """A real PDF cut off mid-stream.

    Header is valid, so upload validation passes. It fails later, during
    extraction — which is the interesting part: the failure has to be
    reported, not swallowed.
    """
    full = _valid_pdf_bytes(pages=3)
    with open(path, "wb") as f:
        f.write(full[: len(full) // 2])
    return {
        "what": "valid PDF header, body truncated at 50%",
        "expected": "accepted at upload, FAILED during processing with a "
                    "readable error",
    }


def case_corrupt_body(path):
    """Valid header and trailer, garbage in between."""
    full = _valid_pdf_bytes(pages=2)
    head, tail = full[:200], full[-200:]
    with open(path, "wb") as f:
        f.write(head + os.urandom(2000) + tail)
    return {
        "what": "valid header and trailer, random bytes between",
        "expected": "accepted at upload, FAILED during processing",
    }


def case_no_text(path):
    """A PDF whose pages are blank.

    Stands in for a scanned document: structurally fine, but text
    extraction yields nothing. The system must say so rather than
    silently indexing an empty document.
    """
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for _ in range(2):
        c.showPage()
    c.save()
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return {
        "what": "structurally valid PDF with no extractable text",
        "expected": "must not silently index an empty document — either "
                    "FAILED or flagged as requiring OCR",
    }


def case_long(path):
    """One hundred pages.

    Exercises chunking, timeouts, and per-document token budgets.
    """
    with open(path, "wb") as f:
        f.write(_valid_pdf_bytes(
            pages=100,
            text="Payment is due within 45 days of receipt of a valid invoice.",
        ))
    return {
        "what": "100-page PDF",
        "expected": "processes to completion, or fails with a clear "
                    "size/timeout error — never hangs",
    }


def case_oversized(path):
    """Above the 25 MB upload cap.

    Padded with an incompressible comment so the file is genuinely large
    rather than large-on-paper.
    """
    base = _valid_pdf_bytes(pages=1)
    target = 28 * 1024 * 1024
    padding = b"\n% " + os.urandom(target).hex().encode()[:target]
    with open(path, "wb") as f:
        f.write(base[:-6] + padding + b"\n%%EOF\n")
    return {
        "what": "PDF over the 25 MB limit",
        "expected": "rejected at upload with a size error",
    }


def case_null_bytes_in_name(path):
    """A filename containing a null byte.

    Some path handling truncates at the null, so a name that looks safe
    can resolve somewhere else entirely.
    """
    with open(path, "wb") as f:
        f.write(_valid_pdf_bytes())
    return {
        "what": "valid PDF, to be uploaded under a filename containing \\x00",
        "expected": "filename sanitised or rejected — never used raw",
        "upload_as": "safe\u0000.pdf",
    }


def case_traversal_name(path):
    """A filename that walks out of the storage directory."""
    with open(path, "wb") as f:
        f.write(_valid_pdf_bytes())
    return {
        "what": "valid PDF, to be uploaded under a traversal filename",
        "expected": "written inside the storage directory regardless",
        "upload_as": "../../../etc/passwd.pdf",
    }


def case_unicode_name(path):
    """Non-ASCII filename.

    Not an attack, just a case that breaks naive path handling.
    """
    with open(path, "wb") as f:
        f.write(_valid_pdf_bytes())
    return {
        "what": "valid PDF with a non-ASCII filename",
        "expected": "accepted; name preserved or transliterated, not mangled",
        "upload_as": "عقد-الخدمات-٢٠٢٦.pdf",
    }


CASES = [
    ("empty.pdf", case_empty),
    ("not_a_pdf.pdf", case_not_a_pdf),
    ("truncated.pdf", case_truncated),
    ("corrupt_body.pdf", case_corrupt_body),
    ("no_text.pdf", case_no_text),
    ("long_100_pages.pdf", case_long),
    ("oversized.pdf", case_oversized),
    ("null_byte_name.pdf", case_null_bytes_in_name),
    ("traversal_name.pdf", case_traversal_name),
    ("unicode_name.pdf", case_unicode_name),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    manifest = {}
    for filename, builder in CASES:
        path = os.path.join(OUT_DIR, filename)
        info = builder(path)
        info["size_bytes"] = os.path.getsize(path)
        manifest[filename] = info
        print(f"  {filename:24} {info['size_bytes']:>12,} bytes")

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n{len(CASES)} edge cases written to {OUT_DIR}")
    print(f"Manifest: {manifest_path}\n")


if __name__ == "__main__":
    main()
    