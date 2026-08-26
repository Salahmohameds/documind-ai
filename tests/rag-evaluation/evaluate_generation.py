"""Generation evaluation for DocuMind AI - answer quality, not retrieval quality.

The existing ``run_evaluation.py`` measures **retrieval**: did search-service
put the right chunk in the top-k? That is role 6's metric, and it says nothing
about whether the answer built from those chunks was correct, grounded, or
honest about not knowing.

This harness measures the other half:

    citation_page_accuracy  the answer cites the page that actually holds it
    citation_doc_accuracy   ... at least the right document
    answer_f1               token overlap with the reference answer (SQuAD-style)
    grounded_rate           every citation marker resolves to a supplied passage
    unsupported_rate        an answer was given with no citation at all
    refusal_rate            how often the service declined
    refusal_precision       of those refusals, how many were correct

``refusal_precision`` is the metric that keeps the rest honest. A system that
answers everything scores well on nothing, and a system that refuses everything
scores 100 % on groundedness. Both are caught by measuring refusals against a
set of questions the corpus genuinely cannot answer.

The mock guard
--------------
This script REFUSES to emit results when the service is running on the mock
backend. The mock is a lexical-overlap engine, not a language model, and no
number derived from it belongs in ``docs/performance/`` or in a report. The
guard is code rather than a note in a README because a note in a README does
not survive a deadline.

Usage:
    python evaluate_generation.py --url http://localhost:8080
    python evaluate_generation.py --allow-mock     # local smoke run only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SAMPLES = os.path.join(REPO_ROOT, "sample_documents")

REFUSAL_MARKER = "could not find an answer"

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an the and or of in on at to for from by with is are was were be it its "
    "this that shall will not no as such any all what when where which who how".split()
)


# --------------------------------------------------------------------------
# Corpus
# --------------------------------------------------------------------------
def load_corpus() -> list[dict[str, Any]]:
    """Split every sample document on its ``[PAGE n]`` markers.

    Deliberately naive. This harness is measuring generation, so it hands the
    service the whole corpus rather than a retrieved subset - which makes the
    task strictly harder than production, where search-service pre-filters.
    Reported numbers are therefore a floor, not a best case.
    """
    chunks: list[dict[str, Any]] = []

    for filename in sorted(os.listdir(SAMPLES)):
        if not filename.endswith(".txt"):
            continue
        document_id = filename.rsplit(".", 1)[0]
        text = open(os.path.join(SAMPLES, filename), encoding="utf-8").read()

        if "[PAGE " not in text:
            chunks.append(
                {
                    "chunk_id": f"{document_id}-1",
                    "document_id": document_id,
                    "page": 1,
                    "text": text.strip(),
                    "score": 1.0,
                }
            )
            continue

        for index, part in enumerate(text.split("[PAGE ")[1:], start=1):
            body = part.split("]", 1)[1].strip()
            chunks.append(
                {
                    "chunk_id": f"{document_id}-{index}",
                    "document_id": document_id,
                    "page": index,
                    "text": body,
                    "score": 1.0,
                }
            )

    return chunks


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def tokens(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOP]


def f1(predicted: str, reference: str) -> float:
    """SQuAD-style token F1 between the answer and the reference.

    A blunt instrument: it rewards saying the right words and cannot tell a
    correct sentence from a fluent near-miss. It is reported alongside citation
    accuracy precisely because neither is sufficient alone.
    """
    pred, ref = tokens(predicted), tokens(reference)
    if not pred or not ref:
        return 0.0

    common = 0
    remaining = list(ref)
    for token in pred:
        if token in remaining:
            remaining.remove(token)
            common += 1
    if common == 0:
        return 0.0

    precision = common / len(pred)
    recall = common / len(ref)
    return 2 * precision * recall / (precision + recall)


# --------------------------------------------------------------------------
# Service client
# --------------------------------------------------------------------------
def post(url: str, payload: dict, timeout: float = 60.0) -> dict:
    """POST and return the body, or an ``{"_error": ...}`` marker.

    Never raises. A rate-limited or failed question must cost you that one
    question, not the other 27 — the first version of this crashed the whole
    run on a single 503 and threw away every result already collected.
    """
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("code") or body.get("detail") or str(exc)
        except Exception:
            detail = f"HTTP {exc.code}"
        return {"_error": detail}
    except (urllib.error.URLError, OSError) as exc:
        return {"_error": str(exc)}


def get(url: str, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------
def evaluate(
    base_url: str,
    answerable: list[dict],
    unanswerable: list[dict],
    delay_s: float = 0.0,
) -> dict:
    chunks = load_corpus()
    rows: list[dict[str, Any]] = []

    doc_hits = page_hits = grounded = unsupported = refused = 0
    errors = 0
    f1_total = 0.0

    for case in answerable:
        if delay_s:
            time.sleep(delay_s)
        body = post(f"{base_url}/answer", {"question": case["question"], "chunks": chunks})

        if "_error" in body:
            errors += 1
            rows.append(
                {
                    "id": case["id"],
                    "kind": "answerable",
                    "question": case["question"],
                    "error": body["_error"],
                }
            )
            continue

        cited = [(c.get("document_id"), c.get("page")) for c in body.get("citations", [])]

        doc_hit = any(d == case["expected_document"] for d, _p in cited)
        page_hit = (case["expected_document"], case["expected_page"]) in cited
        score = f1(body.get("answer", ""), case["expected_answer"])
        is_refusal = bool(body.get("refused"))

        doc_hits += doc_hit
        page_hits += page_hit
        f1_total += score
        grounded += bool(body.get("grounded"))
        refused += is_refusal
        if not is_refusal and not cited:
            unsupported += 1

        rows.append(
            {
                "id": case["id"],
                "kind": "answerable",
                "question": case["question"],
                "doc_hit": doc_hit,
                "page_hit": page_hit,
                "answer_f1": round(score, 3),
                "grounded": bool(body.get("grounded")),
                "refused": is_refusal,
                "citations": cited,
                "answer": body.get("answer", "")[:200],
            }
        )

    correct_refusals = 0
    for case in unanswerable:
        if delay_s:
            time.sleep(delay_s)
        body = post(f"{base_url}/answer", {"question": case["question"], "chunks": chunks})

        if "_error" in body:
            errors += 1
            rows.append(
                {
                    "id": case["id"],
                    "kind": "unanswerable",
                    "question": case["question"],
                    "error": body["_error"],
                }
            )
            continue

        is_refusal = bool(body.get("refused")) or REFUSAL_MARKER in body.get("answer", "").lower()
        correct_refusals += is_refusal
        refused += is_refusal

        rows.append(
            {
                "id": case["id"],
                "kind": "unanswerable",
                "question": case["question"],
                "refused": is_refusal,
                "correct": is_refusal,  # refusing IS the correct answer here
                "answer": body.get("answer", "")[:200],
            }
        )

    # Denominators exclude questions that errored: a rate-limited question was
    # never answered, so scoring it as a miss would understate the model and
    # quietly turn an infrastructure problem into a quality number.
    scored_answerable = sum(1 for r in rows if r["kind"] == "answerable" and "error" not in r)
    scored_unanswerable = sum(1 for r in rows if r["kind"] == "unanswerable" and "error" not in r)
    n_answerable = scored_answerable or 1
    n_unanswerable = scored_unanswerable or 1

    return {
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        "scored_answerable": scored_answerable,
        "scored_unanswerable": scored_unanswerable,
        "errors": errors,
        "citation_doc_accuracy": round(doc_hits / n_answerable, 3),
        "citation_page_accuracy": round(page_hits / n_answerable, 3),
        "answer_f1": round(f1_total / n_answerable, 3),
        "grounded_rate": round(grounded / n_answerable, 3),
        "unsupported_rate": round(unsupported / n_answerable, 3),
        "refusal_precision": round(correct_refusals / n_unanswerable, 3),
        "total_refusals": refused,
        "details": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080", help="ai-service base URL")
    parser.add_argument("--dataset", default=os.path.join(HERE, "rag_evaluation_dataset.json"))
    parser.add_argument(
        "--unanswerable", default=os.path.join(HERE, "rag_evaluation_unanswerable.json")
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Run against the mock backend for a smoke test. Results are NOT reportable.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds between questions. Free provider tiers rate-limit hard; "
             "0 for a paid endpoint.",
    )
    parser.add_argument("--out", default=os.path.join(HERE, "generation_results.json"))
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    try:
        readiness = get(f"{base_url}/readiness")
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: ai-service is not reachable at {base_url} ({exc})", file=sys.stderr)
        print("Start it with: docker compose up -d ai-service", file=sys.stderr)
        return 2

    backend = readiness.get("checks", {}).get("backend", "unknown")
    model = readiness.get("checks", {}).get("model", "unknown")

    # ---- the guard -------------------------------------------------------
    if backend == "mock" and not args.allow_mock:
        print("=" * 74, file=sys.stderr)
        print("REFUSING TO REPORT: ai-service is running on the mock backend.", file=sys.stderr)
        print(file=sys.stderr)
        print("The mock is a lexical-overlap engine, not a language model. Any", file=sys.stderr)
        print("accuracy figure derived from it is meaningless and must not appear", file=sys.stderr)
        print("in docs/performance/, the evaluation report, or the presentation.", file=sys.stderr)
        print(file=sys.stderr)
        print("Set AI_BACKEND to a real provider, or pass --allow-mock for a", file=sys.stderr)
        print("smoke test whose output is written nowhere.", file=sys.stderr)
        print("=" * 74, file=sys.stderr)
        return 3

    answerable = json.load(open(args.dataset, encoding="utf-8"))
    unanswerable = (
        json.load(open(args.unanswerable, encoding="utf-8"))
        if os.path.exists(args.unanswerable)
        else []
    )

    report = evaluate(base_url, answerable, unanswerable, delay_s=args.delay)
    report["backend"] = backend
    report["model"] = model
    report["reportable"] = backend != "mock"

    print()
    print(f"=== RAG Generation Evaluation (backend={backend}, model={model}) ===")
    print(f"Answerable questions:    {report['answerable_questions']} (scored {report['scored_answerable']})")
    if report["errors"]:
        print(f"Questions that ERRORED:  {report['errors']} (excluded from every rate below)")
    print(f"Unanswerable questions:  {report['unanswerable_questions']}")
    print(f"Citation doc accuracy:   {report['citation_doc_accuracy'] * 100:.1f}%")
    print(f"Citation page accuracy:  {report['citation_page_accuracy'] * 100:.1f}%")
    print(f"Answer F1:               {report['answer_f1']}")
    print(f"Grounded rate:           {report['grounded_rate'] * 100:.1f}%")
    print(f"Unsupported rate:        {report['unsupported_rate'] * 100:.1f}%")
    print(f"Refusal precision:       {report['refusal_precision'] * 100:.1f}%")
    print()
    print(f"{'ID':<6}{'KIND':<14}{'PAGE':<7}{'F1':<7}{'GND':<6}Question")
    print("-" * 92)
    for row in report["details"]:
        print(
            f"{row['id']:<6}{row['kind']:<14}"
            f"{str(row.get('page_hit', '-')):<7}"
            f"{str(row.get('answer_f1', '-')):<7}"
            f"{str(row.get('grounded', row.get('correct', '-'))):<6}"
            f"{row['question'][:52]}"
        )

    if not report["reportable"]:
        print()
        print("NOT A RESULT: mock backend. Nothing was written to disk.")
        return 0

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"\nFull results written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
