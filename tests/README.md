# Tests — DocuMind AI

> Owner: **QA / Performance Engineer (role 8)**, with contributions from every
> service owner (unit tests live inside each service folder).

| Folder | Purpose | Runs where |
|--------|---------|-----------|
| `unit/` | cross-cutting unit test utilities/fixtures shared by services | local + CI |
| `integration/` | API → queue → worker → AI → vector DB flow tests | local compose stack |
| `smoke/` | post-deploy checks: all `/readiness` green, upload happy path | against dev OKE |
| `load/` | k6 scripts: baseline, ramp, spike — same corpus for monolith AND OKE | controlled runs |
| `rag-evaluation/` | golden dataset (15–20 Q/A/source items) + scoring scripts + results | local + dev |

## Load testing protocol (from proposal §18 — no invented numbers)

1. Same k6 script + same synthetic corpus (~50 docs) for both architectures.
2. Baseline: monolith on single VM · Target: 5 services on OKE.
3. 3 runs each → report median. Record CPU/mem/pod count during runs.
4. Capture: RPS, avg latency, P50/P95/P99, error rate, recovery time after pod kill.

## Golden dataset format (`rag-evaluation/golden.jsonl`)

```json
{"question": "...", "expected_answer": "...", "expected_document": "...", "expected_section": "..."}
```

Metrics: retrieval hit@k · answer correctness · faithfulness · latency.
