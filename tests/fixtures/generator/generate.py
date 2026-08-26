import textwrap

"""Synthetic corpus generator for DocuMind AI.

Produces, for every document, three artifacts:
  - a PDF   (for document-service, which accepts PDF only)
  - a .txt  (for search-service, which indexes text, with [PAGE n] markers)
  - a .json (ground truth: expected type, fields, PII, risk, RAG questions)

Documents are built FROM the ground truth, so expected values are correct
by construction. The corpus is fully reproducible from --seed.

Usage:
    python generate.py --contracts 20 --invoices 30 --seed 42
"""

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from data import new_rng
from templates import build_contract, build_invoice

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.dirname(HERE)
DOCS_DIR = os.path.join(FIXTURES, "documents")
TEXT_DIR = os.path.join(FIXTURES, "text")
GT_DIR = os.path.join(FIXTURES, "ground-truth")

LEFT = 20 * mm
TOP = 277 * mm
LINE = 5.2 * mm
FONT = "Courier"          # monospaced, so the invoice columns line up
FONT_SIZE = 9


MAX_CHARS = 92          # fits A4 at Courier 9pt with 20mm margins


def _wrap(line):
    """Wrap long lines, preserving leading indentation.

    drawString does not wrap — anything past the page edge is silently
    dropped, which would make the ground truth reference text that is
    not actually in the document.
    """
    if len(line) <= MAX_CHARS:
        return [line]
    indent = len(line) - len(line.lstrip())
    prefix = " " * indent
    return textwrap.wrap(
        line,
        width=MAX_CHARS,
        initial_indent=prefix,
        subsequent_indent=prefix + "  ",
        break_long_words=False,
        break_on_hyphens=False,
    ) or [line]


def render_pdf(pages, path):
    c = canvas.Canvas(path, pagesize=A4)
    for page_lines in pages:
        c.setFont(FONT, FONT_SIZE)
        y = TOP
        for raw in page_lines:
            for line in _wrap(raw):
                if y < 20 * mm:
                    raise RuntimeError(
                        f"page overflow in {os.path.basename(path)} — "
                        "content would be silently dropped"
                    )
                c.drawString(LEFT, y, line)
                y -= LINE
        c.showPage()
    c.save()

def render_text(pages, path):
    """Text form with explicit page markers.

    index_sample_documents.py already parses [PAGE n], so this keeps the
    existing search-service ingest path working unchanged.
    """
    out = []
    for i, page_lines in enumerate(pages, start=1):
        out.append(f"[PAGE {i}]")
        out.extend(page_lines)
        out.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def generate(n_contracts, n_invoices, seed, clean):
    if clean:
        for d in (DOCS_DIR, TEXT_DIR, GT_DIR):
            shutil.rmtree(d, ignore_errors=True)

    for d in (DOCS_DIR, TEXT_DIR, GT_DIR):
        os.makedirs(d, exist_ok=True)

    manifest = []
    index = 0

    for i in range(n_contracts):
        doc_id = f"contract_{i:04d}"
        rng = new_rng(seed + index)
        pages, gt = build_contract(rng, doc_id)
        _emit(doc_id, pages, gt, manifest)
        index += 1

    for i in range(n_invoices):
        doc_id = f"invoice_{i:04d}"
        rng = new_rng(seed + index)
        pages, gt = build_invoice(rng, doc_id)
        _emit(doc_id, pages, gt, manifest)
        index += 1

    manifest_path = os.path.join(FIXTURES, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "seed": seed,
            "contracts": n_contracts,
            "invoices": n_invoices,
            "total_documents": len(manifest),
            "total_rag_questions": sum(m["rag_question_count"] for m in manifest),
            "documents": manifest,
        }, f, indent=2)

    return manifest, manifest_path


def _emit(doc_id, pages, gt, manifest):
    render_pdf(pages, os.path.join(DOCS_DIR, f"{doc_id}.pdf"))
    render_text(pages, os.path.join(TEXT_DIR, f"{doc_id}.txt"))
    with open(os.path.join(GT_DIR, f"{doc_id}.json"), "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)
    manifest.append({
        "document_id": doc_id,
        "type": gt["expected_type"],
        "pages": gt["page_count"],
        "risk_band": gt["expected_risk"]["band"],
        "pii_count": len(gt["expected_pii"]),
        "rag_question_count": len(gt["rag_questions"]),
    })


def main():
    p = argparse.ArgumentParser(description="Generate the synthetic test corpus.")
    p.add_argument("--contracts", type=int, default=20)
    p.add_argument("--invoices", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--clean", action="store_true",
                   help="delete existing corpus before generating")
    args = p.parse_args()

    manifest, manifest_path = generate(
        args.contracts, args.invoices, args.seed, args.clean
    )

    bands = {}
    for m in manifest:
        bands[m["risk_band"]] = bands.get(m["risk_band"], 0) + 1

    print(f"\nGenerated {len(manifest)} documents (seed={args.seed})")
    print(f"  Contracts: {args.contracts}   Invoices: {args.invoices}")
    print(f"  Risk bands: {bands}")
    print(f"  RAG questions: {sum(m['rag_question_count'] for m in manifest)}")
    print(f"\n  PDFs:         {DOCS_DIR}")
    print(f"  Text:         {TEXT_DIR}")
    print(f"  Ground truth: {GT_DIR}")
    print(f"  Manifest:     {manifest_path}\n")


if __name__ == "__main__":
    main()