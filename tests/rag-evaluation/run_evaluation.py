
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--dataset",
        default=os.path.join(os.path.dirname(__file__), "rag_evaluation_dataset.json"),
    )
    args = parser.parse_args()

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

    out_path = os.path.join(os.path.dirname(__file__), "evaluation_results.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()
