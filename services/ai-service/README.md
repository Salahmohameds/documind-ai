# ai-service

Classification, field extraction, contract risk scoring, embeddings and RAG
generation with citations — behind one provider-agnostic adapter.

**Owner:** role 4 (AI Engineer)
**API contract:** [`docs/architecture/ai-service-contract.md`](../../docs/architecture/ai-service-contract.md)
**Decisions:** [ADR-006](../../docs/adr/ADR-006-oci-generative-ai.md) (provider) · [ADR-008](../../docs/adr/ADR-008-embeddings-boundary.md) (embeddings boundary)

---

## Quick start

No credential, no network, no OCI account:

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8080
```

```bash
curl -s localhost:8080/readiness
```

```bash
pytest
```

With docker compose, from the repo root:

```bash
docker compose up -d ai-service
```

---

## Why `mock` is the default backend

The whole platform has to be buildable while decision D1 — which AI provider —
is still open. Nobody has yet run `oci iam region-subscription list`, and
`me-jeddah-1` does not host OCI Generative AI at all (ADR-006 §Contingency).
Four other roles were blocked behind that.

So `AI_BACKEND=mock` is the default, and the mock is **a real implementation,
not a stub**:

* **Embeddings carry genuine lexical signal.** Signed feature hashing over word
  unigrams and bigrams, L2-normalised. Related texts score measurably higher
  than unrelated ones, so retrieval can actually be smoke-tested. Compare with
  `search-service`'s own `MockEmbedder`, which is a SHA-256 hash chain whose
  cosine similarity is pure noise.
* **Answers are extractive and really grounded.** `/answer` finds the sentence
  with the strongest overlap with the question and cites the passage it came
  from, using the same `[n]` markers a real model is prompted to emit — so one
  citation parser serves both paths.
* **Classification, extraction and risk scoring are the same code on every
  backend.** They are deterministic engines, not model calls, so their output
  offline is the output in production.

**What it is not:** a language model. `tests/rag-evaluation/evaluate_generation.py`
**refuses to write a results file** when the backend is `mock`, and
`run_evaluation.py` does the same for `EMBEDDING_BACKEND=mock`. Enforced in code,
not in a README, because a README does not survive a deadline.

Measured on the mock backend for reference only — *these are not results*:
citation page accuracy 70 %, refusal precision 12.5 %. The refusal number is
the honest one: the mock answers seven of eight questions the corpus cannot
answer. That is the gap a real model closes.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/embed` | Batch text → vectors (role 6 consumes this) |
| POST | `/classify` | invoice · contract · receipt · report · unknown |
| POST | `/extract` | Structured fields with source-anchored evidence |
| POST | `/analysis/risk` | Deterministic risk score + model-written explanation |
| POST | `/answer` | RAG generation with page-level citations |
| POST | `/pii` | PII detection / redaction |
| GET | `/liveness` | Process alive. Never touches the provider. |
| GET | `/readiness` | Provider reachable and circuit closed, else 503 |
| GET | `/metrics` | Prometheus |
| GET | `/openapi.json` | The authoritative schema |

Full request/response shapes: see the API contract, or the live OpenAPI schema.

---

## Design decisions worth knowing

**The risk score is not a model output.** A weighted, versioned rule set
produces the number; the model only writes the narrative. Every point traces to
a named rule and a quoted span, and the same document always scores the same.
This is the deliberate answer to *"how did you validate 72 out of 100?"* — a
question an LLM-produced score cannot survive.

**Every extracted value must be locatable in the source.** Model-supplied
values are searched for in the original text and **discarded** if not found —
one string search per field, and it is the cheapest effective guard against a
model inventing an invoice total.

**Redaction happens in one place.** `app/pipeline.py` runs redact → budget →
resilience → call → account on every provider call. "PII is redacted before
egress" is only true if it is impossible to forget, and a route author cannot
forget a step they never write.

**Readiness means something.** It reflects a cached provider probe and the
circuit breaker state. Liveness deliberately does not — a liveness probe that
failed during a provider outage would make Kubernetes restart every healthy pod
and turn a degraded dependency into a self-inflicted outage.

**The circuit breaker is per-pod, on purpose.** A shared breaker would need a
coordination backend and would make one pod's network problem everybody's
outage. Each replica discovering the provider is down independently is correct,
and it keeps the service stateless in the sense that matters: no pod holds data
another pod needs.

**Prompts are files, not string literals.** `PROMPTS_DIR` points at a mounted
ConfigMap, so changing a prompt is a `kubectl apply` and a restart — not an
image rebuild, a Trivy scan, an OCIR push and a rollout.

---

## Configuration

Everything is environment-driven; defaults are local-development only. The full
table is in the [API contract](../../docs/architecture/ai-service-contract.md#4-configuration).
The ones you will actually touch:

```bash
AI_BACKEND=mock              # mock | oci | openai_compat
MODEL_NAME=mock-chat-v1
EMBEDDING_MODEL=mock-embed-v1
EMBEDDING_DIM=384            # must match the pgvector column
TOKEN_BUDGET_PER_REQUEST=8000
REQUEST_TIMEOUT_S=30
```

### Switching to OCI Generative AI (once D1 closes)

```bash
AI_BACKEND=oci
OCI_REGION=me-riyadh-1              # a GenAI region — NOT necessarily the compartment's
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxx
OCI_AUTH_MODE=workload              # OKE workload identity. Never an API key.
MODEL_NAME=cohere.command-a
EMBEDDING_MODEL=cohere.embed-v4.0
EMBEDDING_DIM=1024
```

Requires the OCI SDK, which is deliberately **not** in `requirements.txt` so the
default image stays small and dependency-free:

```bash
docker build --build-arg INSTALL_OCI=true -t documind/ai-service:oci .
```

Compartments in OCI are **global**; the SDK client is separately pointed at a
**regional endpoint**. So a compartment in `me-jeddah-1` can call Generative AI
in `me-riyadh-1` — same tenancy, same IAM, no data leaving OCI. That is why
`OCI_REGION` and `OCI_COMPARTMENT_ID` are independent settings.

---

## Layout

```
app/
├── main.py            FastAPI wiring: middleware, error translation, routers
├── config.py          pydantic-settings; nothing hard-coded
├── pipeline.py        redact → budget → resilience → call → account
├── resilience.py      timeout, jittered backoff, circuit breaker
├── budget.py          per-request token cap, context trimming
├── redaction.py       PII detection and redaction
├── metrics.py         Prometheus series
├── schemas.py         the wire contract (authoritative)
├── adapters/          mock · oci_genai · openai_compat, one interface
├── analysis/          deterministic engines: classify, extract, risk rules
├── prompts/           *.txt, mounted as a ConfigMap in K8s
└── routes/            thin HTTP handlers
```

`app/` rather than `src/`: matches `document-service`, which is the most
recently written service in the repo. `services/README.md` still says `src/`
and is now out of date for two of the four services.

---

## Testing

```bash
pytest -q          # 101 tests, ~0.3s, no network
```

`tests/conftest.py` pins `AI_BACKEND=mock` **before** the app is imported, so a
stray `AI_BACKEND=oci` in a shell cannot turn `pytest` into a billable event.
No test calls a real model.

CI picks the Dockerfile up automatically — `ci.yml` discovers
`services/*/Dockerfile` and builds and Trivy-scans each one. Note that CI
currently runs **no Python test job at all**, for any service; adding one is a
change to role 2's workflow file and should be a separate PR.

### Evaluation

```bash
python ../../tests/rag-evaluation/evaluate_generation.py --url http://localhost:8080
```

Measures **generation**, which nothing previously did: citation page accuracy,
answer F1, grounded rate, unsupported rate, and refusal precision against a set
of questions the corpus genuinely cannot answer. Retrieval remains
`run_evaluation.py`'s job (role 6).

Refusal precision is the metric that keeps the others honest: a system that
answers everything scores well on nothing, and a system that refuses everything
scores 100 % on groundedness.

---

## Known gaps

* `oci_genai.py` and `openai_compat.py` have **never been executed against a
  live endpoint** — D1 is open. Call sites needing confirmation against the
  pinned SDK are marked `VERIFY-D1`.
* Scanned PDFs are **out of scope**. Text-extractable documents only; there is
  no OCR path. `sample_documents/` is `.txt` only, so nothing exercises one.
* The risk rule set is 15 rules tuned against one sample contract. It is
  deterministic and testable, not comprehensive, and it is not legal advice.
