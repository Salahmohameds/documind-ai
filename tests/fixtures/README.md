# Test corpus

Synthetic invoices and contracts used by load tests, RAG evaluation, and
integration tests.

## Why synthetic

Documents are generated **from** the ground truth, not annotated after the
fact. When the ground truth says a contract's payment terms are 45 days,
that is not a transcription that might be wrong — it is the value the
document was built from. Real documents cannot give that guarantee.

## Generating

```bash
cd tests/fixtures/generator
python generate.py --contracts 20 --invoices 30 --seed 42 --clean
python verify.py
```

Requires `reportlab`. Output is **not committed** — it is reproducible
from the seed recorded in `manifest.json`. Regenerating with the same
seed produces identical documents, so any change in a measured metric
is caused by a code change, never by a corpus change.

Always run `verify.py` after generating. It fails if any expected field
or PII value is missing from the document text, or lands on a different
page than the ground truth declares.

## Output

| Path                  | Format                       | Consumed by                       |
| --------------------- | ---------------------------- | --------------------------------- |
| `documents/*.pdf`     | PDF                          | `document-service` (PDF only)     |
| `text/*.txt`          | text with `[PAGE n]` markers | `search-service` (text only)      |
| `ground-truth/*.json` | expected values              | all test suites                   |
| `manifest.json`       | seed + corpus summary        | committed, reproducibility record |

Both formats are rendered from the same source, so the PDF and text
forms of a document always contain identical content. This matters
because the two ingest paths reject each other's format.

## Ground truth per document

- `expected_type` — INVOICE or CONTRACT
- `expected_fields` — parties, dates, payment terms, totals, currency
- `expected_pii` — five entity types, each with the page it appears on
- `expected_risk` — band plus the flags that produced it
- `rag_questions` — question, expected answer, expected page

Risk bands are derived from drivers chosen before the text is written
(auto-renewal, termination notice, liability cap, contract value, late
interest), so the expected band is explainable rather than asserted.

All PII uses `.example` domains and randomly generated identifiers. No
value corresponds to a real person, account, or organisation.

## Current corpus

50 documents · 20 contracts (4 pages each) · 30 invoices (1 page each)
270 RAG questions · 250 PII entities · seed 42
