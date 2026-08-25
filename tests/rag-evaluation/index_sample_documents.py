

import os
import sys

_SEARCH_SERVICE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "services", "search-service"
)
sys.path.insert(0, os.path.abspath(_SEARCH_SERVICE_DIR))

from src.search import index_document  # noqa: E402

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sample_documents")


def load_contract_pages(path):
    with open(path, "r") as f:
        raw = f.read()
    pages = []
    for part in raw.split("[PAGE"):
        part = part.strip()
        if not part:
            continue
        text = part.split("]", 1)[-1].strip()
        if text:
            pages.append(text)
    return pages


def main():
    with open(os.path.join(SAMPLE_DIR, "invoice_sample.txt")) as f:
        invoice_text = f.read()
    n = index_document("invoice_sample", invoice_text)
    print(f"Indexed invoice_sample: {n} chunks")

    pages = load_contract_pages(os.path.join(SAMPLE_DIR, "contract_sample.txt"))
    n = index_document("contract_sample", pages)
    print(f"Indexed contract_sample: {n} chunks across {len(pages)} pages")


if __name__ == "__main__":
    main()
