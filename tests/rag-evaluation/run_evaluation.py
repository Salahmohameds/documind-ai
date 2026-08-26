
import argparse
import json
import os
import sys


_SEARCH_SERVICE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "services", "search-service"
)
sys.path.insert(0, os.path.abspath(_SEARCH_SERVICE_DIR))

from src.search import search  # noqa: E402


def load_dataset(path):
    with open(path, "r") as f:
        return json.load(f)


def evaluate(dataset, top_k):
    total = len(dataset)
    doc_hits = 0
    page_hits = 0
    reciprocal_ranks = []
    detailed_rows = []

    for case in dataset:
        results = search(case["question"], top_k=top_k)
        doc_ids = [r.document_id for r in results]
        doc_page_pairs = [(r.document_id, r.page) for r in results]

        doc_hit = case["expected_document"] in doc_ids
        page_hit = (case["expected_document"], case["expected_page"]) in doc_page_pairs

        if doc_hit:
            doc_hits += 1
        if page_hit:
            page_hits += 1

        # reciprocal rank based on document match (1-indexed)
        rr = 0.0
        if doc_hit:
            rank = doc_ids.index(case["expected_document"]) + 1
            rr = 1.0 / rank
        reciprocal_ranks.append(rr)

        detailed_rows.append({
            "id": case["id"],
            "question": case["question"],
            "doc_hit": doc_hit,
            "page_hit": page_hit,
            "reciprocal_rank": round(rr, 3),
            "top_result_doc": doc_ids[0] if doc_ids else None,
        })

    return {
        "top_k": top_k,
        "total_questions": total,
        "doc_hit_rate": round(doc_hits / total, 3),
        "page_hit_rate": round(page_hits / total, 3),
        "mrr": round(sum(reciprocal_ranks) / total, 3),
        "details": detailed_rows,
    }


def guard_against_mock_embeddings(allow_mock):
    """Refuse to produce a retrieval metric from meaningless vectors.

    EMBEDDING_BACKEND=mock in search-service is a SHA-256 hash chain: perfectly
    deterministic, and semantically empty. Cosine similarity between two related
    sentences is noise, so a hit rate measured against it describes nothing.

    This is enforced in code rather than documented in a README because the
    failure mode is somebody pasting a hit rate into the report at 2 a.m. under
    deadline, and a README does not stop that.
    """
    backend = os.getenv("EMBEDDING_BACKEND", "mock")
    if backend != "mock" or allow_mock:
        return backend

    print("=" * 74, file=sys.stderr)
    print("REFUSING TO REPORT: EMBEDDING_BACKEND=mock.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Mock embeddings are a hash chain with no semantic content, so any", file=sys.stderr)
    print("hit rate or MRR computed from them is meaningless. Do not put these", file=sys.stderr)
    print("numbers in docs/performance/ or the final report.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Set EMBEDDING_BACKEND=local_st (or point search-service at", file=sys.stderr)
    print("ai-service /embed), or pass --allow-mock for a plumbing smoke test", file=sys.stderr)
    print("whose output is written nowhere.", file=sys.stderr)
    print("=" * 74, file=sys.stderr)
    raise SystemExit(3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--dataset",
        default=os.path.join(os.path.dirname(__file__), "rag_evaluation_dataset.json"),
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Run with mock embeddings for a plumbing smoke test. NOT reportable.",
    )
    args = parser.parse_args()

    backend = guard_against_mock_embeddings(args.allow_mock)

    dataset = load_dataset(args.dataset)
    report = evaluate(dataset, args.top_k)

    print(f"\n=== RAG Retrieval Evaluation (top_k={report['top_k']}) ===")
    print(f"Questions evaluated: {report['total_questions']}")
    print(f"Document Hit Rate:   {report['doc_hit_rate'] * 100:.1f}%")
    print(f"Page Hit Rate:       {report['page_hit_rate'] * 100:.1f}%")
    print(f"MRR:                 {report['mrr']}")
    print()
    print(f"{'ID':<5}{'Doc Hit':<10}{'Page Hit':<10}{'RR':<8}Question")
    print("-" * 90)
    for row in report["details"]:
        print(
            f"{row['id']:<5}{str(row['doc_hit']):<10}{str(row['page_hit']):<10}"
            f"{row['reciprocal_rank']:<8}{row['question'][:60]}"
        )

    if backend == "mock":
        print("\nNOT A RESULT: mock embeddings. Nothing was written to disk.")
        return

    report["embedding_backend"] = backend
    out_path = os.path.join(os.path.dirname(__file__), "evaluation_results.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()
