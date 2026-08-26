"""Verify that every ground-truth value actually appears in its document.

A corpus whose expected answers are not present in the text produces
false failures — the model is marked wrong for not finding something
that was never there. This check must pass before the corpus is used.
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.dirname(HERE)


def main():
    problems = []
    docs = 0
    fields = 0
    pii = 0
    questions = 0

    for path in sorted(glob.glob(os.path.join(FIXTURES, "ground-truth", "*.json"))):
        gt = json.load(open(path, encoding="utf-8"))
        docs += 1
        text_path = os.path.join(FIXTURES, "text", f"{gt['document_id']}.txt")
        text = open(text_path, encoding="utf-8").read()

        pages = text.split("[PAGE ")

        for key, value in gt["expected_fields"].items():
            values = value if isinstance(value, list) else [value]
            for v in values:
                if not isinstance(v, str):
                    continue
                fields += 1
                if v not in text:
                    problems.append(f"{gt['document_id']}: field '{key}' = {v!r} not in text")

        for entity in gt["expected_pii"]:
            pii += 1
            if entity["value"] not in text:
                problems.append(
                    f"{gt['document_id']}: PII {entity['type']} = "
                    f"{entity['value']!r} not in text"
                )
                continue
            marker = f"{entity['page']}]"
            page_block = next((p for p in pages if p.startswith(marker)), None)
            if page_block is None or entity["value"] not in page_block:
                problems.append(
                    f"{gt['document_id']}: PII {entity['type']} not on "
                    f"declared page {entity['page']}"
                )

        for q in gt["rag_questions"]:
            questions += 1
            if q["expected_page"] > gt["page_count"]:
                problems.append(
                    f"{gt['document_id']}: question cites page "
                    f"{q['expected_page']} but document has {gt['page_count']}"
                )

    print(f"\nVerified {docs} documents")
    print(f"  field values checked: {fields}")
    print(f"  PII entities checked: {pii} (value present + on declared page)")
    print(f"  RAG questions checked: {questions}")

    if problems:
        print(f"\n{len(problems)} PROBLEMS:\n")
        for p in problems[:40]:
            print(f"  - {p}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        sys.exit(1)

    print("\nAll ground-truth values present and correctly paged.\n")


if __name__ == "__main__":
    main()