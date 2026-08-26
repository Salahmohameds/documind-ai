# ai-service — API contract

**Owner:** role 4 (AI Engineer) · **Status:** proposed, implemented in `services/ai-service/`
**Consumers:** role 5 (processing-service), role 6 (search-service), role 3 (api-gateway), role 8 (QA)

This document is the prose form of `services/ai-service/app/schemas.py`. **The
code is authoritative** — if the two disagree, the code is right and this page
is the bug. The live OpenAPI schema is served at `GET /openapi.json`.

Written now, before the consumers write their integration code, because
`ROLES.md` names the API contract as role 3's first task and says it "unlocks
roles 4, 5, 6 and 8". It had not been written, and four people were waiting on
it. This covers the ai-service half so that work can start.

---

## 1. Ownership boundaries

Two boundaries were genuinely ambiguous in `ROLES.md` and would have produced a
merge conflict. Both are resolved here.

### vs role 6 (Data / Search) — both were listed as owning embeddings

| Concern | Owner |
|---|---|
| Model client, credentials, token budget | **ai-service** |
| `POST /embed` endpoint | **ai-service** |
| Chunking, storage, indexing, retrieval, top-k | **search-service** |
| Retrieval metrics (hit rate, MRR) | **search-service** |
| Generation metrics (answer, citations, refusals) | **ai-service** |

One model client in the codebase, one place credentials live, one place the
token budget is enforced. `OCIGenerativeAIEmbedder` in
`services/search-service/src/embeddings.py` — which currently raises
`NotImplementedError` addressed to the AI Engineer — becomes a thin HTTP call to
`POST /embed`.

**The hop is optional.** `search-service` keeps `local_st` as an in-process
backend. Embeddings are the highest-volume call in the platform (every chunk of
every document, plus every query), so whether to pay a network round-trip for
them is a deployment decision, not something to hard-code. See ADR-008.

### vs role 5 (Processing) — failure semantics

The worker calls ai-service. Every error response carries a **`retryable`**
boolean, and that is the contract:

| `retryable` | Worker action |
|---|---|
| `true` | Re-queue with the worker's own backoff. ai-service has already retried internally. |
| `false` | Do not retry. Dead-letter the job. The same request will fail identically. |

ai-service already applies bounded retries with jittered backoff and a circuit
breaker before returning anything, so a `retryable: true` means *"this failed
even after we tried"* — the worker should back off generously rather than
immediately.

**Recommended worker timeout: `REQUEST_TIMEOUT_S + 5s`** (default 35 s). Set it
shorter and the worker gives up while ai-service is still usefully retrying.

---

## 2. Conventions

* **Base path:** none. Endpoints are at the service root, port `8080`.
* **Auth:** behind the gateway JWT, except `/liveness`, `/readiness`, `/metrics`.
* **Correlation:** send `X-Request-ID`. It is propagated, never regenerated, and
  echoed on every response including errors. Optional `request_id` in the body
  is echoed into `meta.request_id`.
* **Content type:** `application/json` throughout.

### `meta` — on every successful response

```json
{
  "provider": "mock",
  "model": "mock-chat-v1",
  "duration_ms": 12,
  "usage": { "tokens_in": 420, "tokens_out": 35, "estimated": true },
  "request_id": "…",
  "degraded": false,
  "redacted": false
}
```

* `usage.estimated: true` — the counts are a local `chars/4` estimate, not
  provider-reported. **Never present an estimated count as a measurement.**
* `degraded: true` — the response was produced by a local fallback because the
  provider was unusable. The result is still valid but weaker; the worker should
  mark the job completed-with-caveats rather than silently trusting it.
* `redacted: true` — PII was replaced before the text left the cluster.

### Error envelope — identical on every endpoint

```json
{
  "code": "ERR_PROVIDER_TIMEOUT",
  "title": "Model provider timed out",
  "detail": "…",
  "retryable": true,
  "request_id": "…"
}
```

| Code | HTTP | Retryable | Meaning |
|---|---|---|---|
| `ERR_PROVIDER_TIMEOUT` | 504 | yes | Provider exceeded `REQUEST_TIMEOUT_S`. |
| `ERR_PROVIDER_UNAVAILABLE` | 503 | yes | Provider unreachable or erroring. |
| `ERR_CIRCUIT_OPEN` | 503 | yes | Breaker open; not even attempted. Back off hard. |
| `ERR_TOKEN_BUDGET_EXCEEDED` | 413 | **no** | Payload over `TOKEN_BUDGET_PER_REQUEST`. Split it. |
| `ERR_BATCH_TOO_LARGE` | 413 | **no** | Over `MAX_EMBED_BATCH`. Send smaller batches. |
| `ERR_PROVIDER_MISCONFIGURED` | 500 | **no** | Config error. Needs a human. |
| `ERR_PROMPT_NOT_FOUND` | 500 | **no** | Prompts ConfigMap not mounted. |
| `ERR_UNSUPPORTED_OPERATION` | 501 | **no** | Provider does not support it. |
| — | 422 | **no** | Pydantic validation failure (FastAPI default shape). |

---

## 3. Endpoints

### `POST /embed` → role 6

```jsonc
// request
{ "texts": ["chunk one", "chunk two"], "input_type": "document" }
// response
{ "embeddings": [[0.01, …], [0.02, …]], "dim": 384, "count": 2, "meta": { … } }
```

* **Batch-first.** `texts` is required and non-empty. Max `MAX_EMBED_BATCH`
  (default 96); over that is `ERR_BATCH_TOO_LARGE` — rejected, never truncated,
  because silently dropping half a batch corrupts the index invisibly.
* `input_type`: `"document"` when indexing, `"query"` when searching. Cohere
  embedding models project the two into different spaces; passing the wrong one
  degrades retrieval with no error. The mock ignores it deliberately, so both
  land in the same space offline.
* `dim` **must** match the `vector(N)` column in `database/schema.sql`. A
  mismatch is rejected at startup rather than written into the table.
* Embeddings are **not** PII-redacted — see §5.

### `POST /classify`

```jsonc
// request
{ "text": "…", "document_id": "optional" }
// response
{
  "document_id": "…",
  "label": "contract",              // invoice | contract | receipt | report | unknown
  "confidence": 0.73,
  "scores": { "invoice": 0.10, "contract": 0.73, "receipt": 0.17, "report": 0.0 },
  "rationale": "Matched 8 'contract' signals …",
  "meta": { … }
}
```

`scores` sum to 1.0 and expose the runner-up: a 0.51/0.49 split is very
different from 0.95/0.05, and the caller should be able to see which it got.
`"unknown"` is returned rather than a low-confidence guess, because a wrong
label sends the wrong field set to `/extract`.

### `POST /extract`

```jsonc
// request
{ "text": "…", "document_type": "invoice", "fields": ["invoice_number"] }  // both optional
// response
{
  "document_type": "invoice",
  "fields": {
    "invoice_number": {
      "value": "INV-1024",
      "confidence": 0.9,
      "evidence": { "snippet": "Invoice Number: INV-1024", "offset": 24, "page": null }
    },
    "invoice_date": { "value": null, "confidence": 0.0, "evidence": null }
  },
  "meta": { … }
}
```

* `document_type` omitted → classified first.
* Fields that are not found are returned with `value: null`, not omitted. The
  response shape is stable regardless of what the document contains.
* **Every value carries evidence locatable in the source.** Model-supplied
  values are searched for in the original text and discarded if not found. A
  value you cannot point at in the document is not returned.

Field sets: `invoice`, `contract`, `receipt` — see `app/analysis/extraction.py`.

### `POST /analysis/risk`

```jsonc
// request
{ "text": "…", "document_type": "contract", "explain": true }
// response
{
  "score": 38,
  "band": "medium",                 // low <30 · medium 30-64 · high >=65
  "findings": [
    { "rule_id": "R01", "title": "Automatic renewal", "severity": "medium",
      "weight": 10, "evidence": { "snippet": "…automatically renew…", "offset": 1180 } }
  ],
  "explanation": "…",
  "scoring": {
    "method": "deterministic-rules",
    "rules_version": "risk-1.0",
    "points_scored": 23,
    "points_possible": 142,
    "rules_evaluated": 15,
    "rules_fired": 3
  },
  "meta": { … }
}
```

**The score is not produced by a language model.** It is a weighted sum over a
fixed, versioned rule set; the model only writes `explanation` and cannot move
the number. `points_scored` always equals the sum of the fired findings'
weights — that reconciliation is unit-tested. The same document always scores
the same.

`score = min(100, round(100 × points_scored / 60))`. The calibration constant 60
is documented in `app/analysis/risk_rules.py`; changing it requires a
`rules_version` bump so historical scores stay interpretable.

Set `explain: false` for load tests — full score, zero tokens.

### `POST /answer` → role 6 / role 3

```jsonc
// request
{
  "question": "What are the payment terms?",
  "chunks": [
    { "chunk_id": "doc-2", "document_id": "contract_sample", "page": 2,
      "text": "…", "score": 0.83 }
  ]
}
// response
{
  "answer": "Payment is due within 60 days of receipt of a valid invoice. [1]",
  "citations": [
    { "chunk_id": "doc-2", "document_id": "contract_sample", "page": 2, "snippet": "…" }
  ],
  "grounded": true,
  "refused": false,
  "confidence": 1.0,
  "meta": { … }
}
```

* **ai-service does not retrieve.** The caller supplies the chunks. This keeps
  retrieval quality and answer quality separately measurable, so neither can
  hide behind the other.
* Context is capped at `MAX_CONTEXT_CHUNKS` (default 12), best-scoring first.
  When trimming happens the answer says so.
* `refused: true` — the context did not support an answer. **This is a correct
  outcome, not an error.** Do not retry it.
* `grounded: true` — an answer was given and every `[n]` marker resolved to a
  supplied passage. Markers pointing outside the supplied range are dropped.
* `confidence` is **the share of citation markers that resolve**, nothing more.
  It is not a semantic confidence and must not be presented as one.

### `POST /pii` → role 7 / role 8

```jsonc
// request
{ "text": "…", "return_redacted_text": true, "include_values": false }
// response
{
  "matches": [{ "type": "EMAIL", "placeholder": "[EMAIL_1]", "start": 40, "end": 62, "value": null }],
  "counts": { "EMAIL": 1 },
  "redacted_text": "… [EMAIL_1] …"
}
```

Raw values are withheld unless `include_values: true`, so a casual debug call
cannot become the leak this control exists to prevent.

### `GET /liveness` · `GET /readiness` · `GET /metrics`

`/liveness` is 200 whenever the process is up and **never** checks the provider —
a liveness probe that failed on a provider outage would have Kubernetes restart
every healthy pod and turn a degraded dependency into an outage.

`/readiness` returns **503** when the provider is unreachable or the circuit is
open, so the pod leaves the Service endpoints instead of accepting traffic it
will fail.

---

## 4. Configuration

100 % environment-driven. Nothing hard-coded.

| Variable | Default | Notes |
|---|---|---|
| `AI_BACKEND` | `mock` | `mock` \| `oci` \| `openai_compat` |
| `MODEL_NAME` | `mock-chat-v1` | |
| `EMBEDDING_MODEL` | `mock-embed-v1` | |
| `EMBEDDING_DIM` | `384` | Must match the pgvector column |
| `TEMPERATURE` | `0.0` | |
| `MAX_TOKENS` | `1024` | |
| `OCI_REGION` | — | A Generative AI region; **not** necessarily the compartment's region |
| `OCI_COMPARTMENT_ID` | — | Compartments are global |
| `OCI_AUTH_MODE` | `workload` | `workload` \| `instance` \| `config` (local dev only) |
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` | — | Fallback only; key from a Secret |
| `REQUEST_TIMEOUT_S` | `30` | |
| `MAX_RETRIES` | `3` | |
| `CIRCUIT_BREAKER_THRESHOLD` | `5` | Consecutive failures |
| `CIRCUIT_BREAKER_RESET_S` | `30` | |
| `TOKEN_BUDGET_PER_REQUEST` | `8000` | |
| `MAX_EMBED_BATCH` | `96` | |
| `MAX_CONTEXT_CHUNKS` | `12` | |
| `REDACT_BEFORE_EGRESS` | `true` | |
| `PROMPTS_DIR` | `app/prompts` | ConfigMap mount point in K8s |

---

## 5. PII redaction — what the guarantee actually is

Redaction runs in one place (`app/pipeline.py`) before every external provider
call, so a route author cannot forget it.

**Redacted:** email, phone, IBAN, Luhn-valid card numbers, national IDs, SSN, IP
addresses.

**Not redacted:** invoice numbers, amounts, dates, party names in operative
text. These are not personal data, and redacting them would destroy the
extraction the product exists to perform.

**Not applied to `/embed`:** vectors never leave the platform as readable text,
and redacting first would change the vector for a document the tenant already
owns — degrading their own retrieval to protect them from themselves. Redaction
guards *generation* prompts, which is where content leaves in readable form.

**Not applied when `AI_BACKEND=mock`:** nothing egresses, so there is nothing to
protect against.

The honest scope: *when an external provider is configured, document text
leaves the cluster with personal identifiers replaced by placeholders.* It is
not a claim that no data leaves — see ADR-006 on why the OCI path is preferred.

---

## 6. Notes for each consumer

**Role 5 (processing-service)** — call `/classify`, `/extract`, `/analysis/risk`
per document; `/answer` is request-time, not pipeline. Branch on `retryable`.
Timeout 35 s. Treat `degraded: true` as completed-with-caveats.

**Role 6 (search-service)** — replace `OCIGenerativeAIEmbedder.embed` with a
batched POST to `/embed`. Keep `local_st` available. Send `input_type: "query"`
when searching. For RAG, call `/query` yourself then pass the chunks to
`/answer`.

**Role 8 (QA)** — set `AI_BACKEND=mock` for k6. Real calls mean real token spend
and latency figures that measure Oracle's network rather than this
architecture. Use `explain: false` on `/analysis/risk`. `POST /pii` lets you
test PII detection as a functional requirement directly.

**Role 9 (observability)** — scrape `/metrics`. The series worth a dashboard
panel: `documind_ai_tokens_total`, `documind_ai_circuit_breaker_state` (0/1/2),
`documind_ai_request_duration_seconds`, `documind_ai_degraded_responses_total`,
`documind_ai_pii_redactions_total`.

**Role 2 (deployment)** — port 8080, probes at `/liveness` and `/readiness`,
prompts as a ConfigMap at `PROMPTS_DIR`, no secrets in the image. Suggested
requests `100m`/`256Mi`, limits `1000m`/`512Mi`. Stateless: scale freely, the
circuit breaker is per-pod on purpose.
