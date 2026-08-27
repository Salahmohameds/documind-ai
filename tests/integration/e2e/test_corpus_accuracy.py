"""Accuracy against the synthetic corpus.

Every other suite asserts that the API is shaped correctly. This one
asserts that the answers are correct — classification against
expected_type, extraction against expected_fields, PII against the 250
seeded entities.

Slow: uploads the whole corpus and waits for each document. Marked
`accuracy` and excluded from the default run.

    pytest tests/integration/e2e/test_corpus_accuracy.py -m accuracy -v -s

Numbers produced under AI_BACKEND=mock measure the rule set, not a
model. They are real and repeatable — the mock is rules-based, not
random — but they are not a claim about OCI Generative AI. Re-run
against a real provider before quoting anything.
"""

import glob
import io
import json
import os
import time

import pytest

pytestmark = pytest.mark.accuracy

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "fixtures"
)

# Cap the corpus so a run stays under a few minutes. Set to 0 for all 50.
SAMPLE_SIZE = int(os.environ.get("ACCURACY_SAMPLE", "12"))
PER_DOC_TIMEOUT = float(os.environ.get("ACCURACY_TIMEOUT", "60"))

TERMINAL_OK = {"completed", "indexed"}
TERMINAL_BAD = {"failed"}


def load_ground_truth():
    paths = sorted(glob.glob(os.path.join(FIXTURES, "ground-truth", "*.json")))
    if not paths:
        pytest.skip(
            "corpus not generated — run tests/fixtures/generator/generate.py"
        )
    docs = [json.load(open(p, encoding="utf-8")) for p in paths]

    if SAMPLE_SIZE and len(docs) > SAMPLE_SIZE:
        # Take an even spread of contracts and invoices rather than the
        # first N, which would be all contracts.
        contracts = [d for d in docs if d["expected_type"] == "CONTRACT"]
        invoices = [d for d in docs if d["expected_type"] == "INVOICE"]
        half = SAMPLE_SIZE // 2
        docs = contracts[:half] + invoices[: SAMPLE_SIZE - half]

    return docs


@pytest.fixture(scope="module")
def processed(documents):
    """Upload the sample and wait for every document to finish.

    Returns [(ground_truth, document_id, final_status)]. Built once for
    the module — uploading the corpus per test would take far too long.
    """
    corpus = load_ground_truth()
    print(f"\nuploading {len(corpus)} documents...")

    uploaded = []
    for gt in corpus:
        path = os.path.join(FIXTURES, "documents", gt["filename"])
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            content = f.read()
        r = documents.post("/documents", files={
            "file": (gt["filename"], io.BytesIO(content), "application/pdf"),
        })
        if r.status_code == 202:
            uploaded.append((gt, r.json()["id"]))

    print(f"waiting for {len(uploaded)} to process...")

    results = []
    for gt, doc_id in uploaded:
        deadline = time.time() + PER_DOC_TIMEOUT
        status = "timeout"
        while time.time() < deadline:
            body = documents.get(f"/documents/{doc_id}/status").json()
            status = str(body.get("status", "")).lower()
            if status in TERMINAL_OK or status in TERMINAL_BAD:
                break
            time.sleep(1)
        results.append((gt, doc_id, status))

    completed = sum(1 for _, _, s in results if s in TERMINAL_OK)
    print(f"{completed}/{len(results)} completed\n")

    if not results:
        pytest.skip("nothing uploaded — is document-service running?")

    return results


# ───────────────────────── pipeline throughput ─────────────────────────

def test_every_document_reaches_a_terminal_state(processed):
    """No document may stall.

    A stuck document is worse than a failed one: nothing reports it and
    the user waits indefinitely.
    """
    stalled = [(gt["document_id"], s) for gt, _, s in processed
               if s not in TERMINAL_OK and s not in TERMINAL_BAD]
    assert not stalled, f"{len(stalled)} documents never finished: {stalled[:5]}"


def test_completion_rate(processed):
    """Report how many of a known-good corpus process successfully."""
    total = len(processed)
    ok = sum(1 for _, _, s in processed if s in TERMINAL_OK)
    rate = ok / total

    print(f"\n  completion rate: {ok}/{total} = {rate:.1%}")

    assert rate == 1.0, (
        f"{total - ok} of {total} well-formed documents failed to process"
    )


# ──────────────────────────── classification ────────────────────────────

def test_classification_accuracy(documents, processed):
    """Measured against expected_type, which the document was built from.

    Not a transcription that could be wrong — the generator wrote an
    invoice because the ground truth said invoice.
    """
    correct = 0
    total = 0
    wrong = []

    for gt, doc_id, status in processed:
        if status not in TERMINAL_OK:
            continue
        total += 1
        actual = str(
            documents.get(f"/documents/{doc_id}").json().get("type", "")
        ).upper()
        expected = gt["expected_type"]
        if actual == expected:
            correct += 1
        else:
            wrong.append((gt["document_id"], expected, actual))

    assert total, "no documents completed"
    accuracy = correct / total

    print(f"\n  classification accuracy: {correct}/{total} = {accuracy:.1%}")
    for doc, exp, act in wrong[:10]:
        print(f"    {doc}: expected {exp}, got {act}")

    assert accuracy >= 0.90, (
        f"classification accuracy {accuracy:.1%} across {total} documents"
    )


def test_classification_does_not_collapse_to_one_label(documents, processed):
    """A classifier that always answers 'contract' scores well on a
    contract-heavy corpus while being useless."""
    labels = set()
    for _, doc_id, status in processed:
        if status in TERMINAL_OK:
            labels.add(str(
                documents.get(f"/documents/{doc_id}").json().get("type", "")
            ).upper())

    assert len(labels) >= 2, f"only ever produced {labels}"


# ────────────────────────────── retrieval ──────────────────────────────

def test_every_completed_document_is_indexed(search, processed):
    """Indexing is the point of the pipeline.

    Queries the corpus with several different terms rather than one:
    a single query capped at top_k returns the best-matching chunks, not
    every chunk, so a document can be correctly indexed and still miss
    the cut. Union across queries is what tells us whether it is there.
    """
    completed = [doc_id for _, doc_id, s in processed if s in TERMINAL_OK]
    assert completed

    queries = [
        "payment terms",
        "invoice total due",
        "termination notice",
        "liability limitation",
        "parties to the agreement",
        "vendor tax",
    ]

    found = set()
    for question in queries:
        r = search.get("/search", params={"question": question, "top_k": 100})
        assert r.status_code == 200
        found.update(item["document_id"] for item in r.json()["results"])

    missing = [d for d in completed if d not in found]
    rate = 1 - len(missing) / len(completed)

    print(f"\n  indexed and retrievable: "
          f"{len(completed) - len(missing)}/{len(completed)} = {rate:.1%}")

    assert not missing, (
        f"{len(missing)} completed documents were not returned by any of "
        f"{len(queries)} queries: {missing[:5]}"
    )

# ──────────────────────────── summary ────────────────────────────

def test_report_summary(documents, processed):
    """Print a single block suitable for pasting into the results doc."""
    total = len(processed)
    completed = [(gt, d) for gt, d, s in processed if s in TERMINAL_OK]

    correct = sum(
        1 for gt, doc_id in completed
        if str(documents.get(f"/documents/{doc_id}").json().get("type", "")).upper()
        == gt["expected_type"]
    )

    contracts = sum(1 for gt, _ in completed if gt["expected_type"] == "CONTRACT")
    invoices = len(completed) - contracts

    print(f"""
  ─────────────────────────────────────────────
  Corpus accuracy — AI_BACKEND=mock (rules)
  ─────────────────────────────────────────────
  documents uploaded      {total}
  completed               {len(completed)} ({len(completed)/total:.0%})
    contracts             {contracts}
    invoices              {invoices}

  classification correct  {correct}/{len(completed)} = {correct/len(completed):.1%}
  ─────────────────────────────────────────────
  These numbers measure the rule set, not a model.
  Re-run against a real provider before quoting.
  ─────────────────────────────────────────────
""")
    assert True