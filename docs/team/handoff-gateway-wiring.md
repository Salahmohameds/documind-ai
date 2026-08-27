# Handoff — Gateway wiring, tenant isolation, network boundary

**Date:** 2026-08-27
**Context:** The frontend now routes all traffic through `api-gateway`. Doing that
surfaced several issues in services owned by other people. Most are written up
here for a decision rather than fixed; one is fixed on a branch awaiting review.

`scripts/run-local.ps1` starts the whole stack on Windows with the environment
each service actually needs — it is the executable version of the
configuration notes in items 3c and below.

Nothing in this document has been merged to `main`.

---

## Branches open

| Branch | Owner to review | State |
|---|---|---|
| `feat/gateway-document-bulk-ops` | Salem | Committed, tests green, **not merged** |
| `feat/document-tenant-isolation` | Salem | Planned — see item 2 |
| `feat/search-tenant-scoping` | Adel | Planned — see item 3 |
| netpol / network boundary | Salem + Adel | Planned — see item 4 |

---

## 1. `api-gateway` — bulk document routes added (Salem)

**Branch:** `feat/gateway-document-bulk-ops` · **Status:** done, needs review

`document-service` has exposed bulk delete and reprocess since M1, but the
Gateway never proxied them. Both returned `405`, and the frontend carried stub
implementations that reported every id as failed.

Added to `services/api-gateway/app/routes/documents.py`:

- `DELETE /documents` → `document-service` `/documents`
- `POST /documents/reprocess` → `document-service` `/documents/reprocess`

Two things worth knowing when reviewing:

- **`/documents/reprocess` is declared *above* `GET /documents/{document_id}`.**
  Before this change the literal path was captured by the parameterised route,
  which is why it returned `405` rather than `404`. There is a regression test
  for it.
- **Both are body-carrying, and `DELETE` with a body is unusual.**
  `proxy_request` already forwards a body on any method; there is a test
  asserting the `{"ids": […]}` payload reaches the downstream service, because
  a future refactor could silently drop it.

`services/api-gateway/tests/test_document_proxy.py` gained 13 tests. Full suite:
**100 passed**.

### Also noticed in `api-gateway`, not fixed

- **`x-request-id` stripping is a no-op.** Commit `17c6f34` added it to
  `_HOP_BY_HOP`, but `proxy.py:113-115` re-adds the client's value verbatim
  immediately afterwards. The `x-user-email` / `x-user-role` half of that fix
  works correctly; this third is inert. Low severity — a forged request id
  corrupts trace correlation, not authorisation.
- **The Gateway strips `Authorization` and mints nothing downstream.** See
  item 4.

---

## 2. `document-service` — no tenant isolation (Salem)

**Branch:** `feat/document-tenant-isolation` · **Status:** planned, ~28 lines

**Every authenticated user currently sees every document.** There are 135 rows
in the shared library and no query filters them by owner. This was invisible
while sign-in was mocked; it is now reachable, because the frontend signs in
against the Gateway for real.

`grep` across `services/document-service/app/` finds zero references to
`X-User-Email`, `owner`, or `tenant`. The `documents` table
(`database/schema.sql:4`) has six columns and no owner. There is no `users`
table anywhere — the Gateway's store is in-memory
(`services/api-gateway/app/auth/store.py`), so an owner column is free text
with no foreign key to point at.

### The fix

Every read funnels through two repository methods. `DocumentRepository.get()`
is called by `_get_or_raise` (→ `get`, `get_status`), `bulk_delete`, `delete`,
`mark_failed`, and `reset_to_queued` (→ `bulk_reprocess`). **Scope `get()` and
`list()` and all six inherit it** — no route or service-layer changes at all.

| File | Change | Lines |
|---|---|---|
| `database/migrations/003_documents_owner_email.sql` *(new)* | `ADD COLUMN owner_email TEXT`, backfill, index on `(owner_email, uploaded_at DESC)` | ~8 |
| `app/models.py` | one `mapped_column` | ~2 |
| `app/repositories/documents.py` | ctor takes `owner_email`; `create` sets it; **`get()` changes from `db.get(Document, id)` — a primary-key lookup that ignores owner — to a `select().where(id, owner)`**; `list()` filters both the count and the page query | ~12 |
| `app/dependencies.py` | read `X-User-Email`, pass to `DocumentRepository(db, owner_email=…)` | ~6 |
| `app/services/documents.py` | **none** | 0 |
| `app/routes/documents.py` | **none** | 0 |

The `get()` line is the one that matters; the rest is plumbing.

**Backfill decision (made):** the 135 existing rows go to `admin@documind.com`,
the account `api-gateway` seeds on startup. They stay reachable for testing
rather than becoming orphans.

**Migration safety (verified):** `processing-service` maps `documents`
read-mostly through SQLAlchemy, which selects only mapped columns, so an
additive nullable column will not break it. `search-service` never queries
`documents` directly.

> ⚠️ **This fix is only sound if `document-service` is unreachable except
> through the Gateway.** See item 4. Without that boundary,
> `curl -H "X-User-Email: victim@example.com"` straight at port 8081 defeats it
> entirely.

---

## 3. `search-service` — chunks are not tenant-scoped (Adel)

**Branch:** `feat/search-tenant-scoping` · **Status:** planned, not started

**Item 2 does not cover retrieval.** `document_chunks` has no owner column and
no join to one, so `GET /search` and the Gateway's `POST /qa` keep returning
passages from other users' documents.

This is worse than the document-list leak, because `/qa` feeds those passages
to the model: a user would see a scoped, correct-looking document library
sitting next to a generated answer that quotes documents they cannot open.

Two possible approaches, needs Adel's call:

1. **`owner_email` on `document_chunks`**, written at index time. Fast queries,
   denormalised, needs a backfill joined through `documents`.
2. **Join through `documents`** in the vector query. No new column and no
   backfill, but adds a join to every similarity search — the hot path.

### Known blocker in that repo

`search-service` cannot start from its own directory:

```
ModuleNotFoundError: No module named 'app_instrumentation'
```

`src/main.py:12` imports it, but it lives in `services/monitoring/` and is not
on the path. Docker Compose sets this up; a local `uvicorn` from
`services/search-service` does not. **Not fixed as part of this work** —
flagging it because it blocks running the service's tests locally.

---

## 3a. `document-service` — computed analysis is never returned (Salem)

**Status:** not started, the largest single gap

The pipeline works. A document uploaded through the Gateway completes in ~1.3s
and writes real results to four tables:

```
extracted_fields    1 row
risk_assessments    1 row   (risk_score 8, financial Low, legal Low)
document_summaries  1 row
document_chunks     1 row   (indexed, and searchable)
```

**`document-service` reads none of them.** It maps only the `documents` table,
so `GET /documents/{id}` answers with `risk: null`, `pages: 0`, `fields: []`,
`pii: []`, `classification: null` for a document that has all of it on disk.

The response schemas already exist and already match the frontend types
(`ExtractedFieldSchema`, `RiskCategorySchema`, `ClassificationSchema` in
`app/schemas.py`) — they are simply never populated. `_summary()` hardcodes
`risk=None` and `pages=0`.

The visible cost: the document detail page, the risk column in the library, the
extracted-fields panel and the PII panel are all permanently empty even after a
completely successful run. It reads as "the AI does nothing", when in fact the
AI has already done the work and the answer is sitting in Postgres.

This is a read-side change in `document-service` — a repository method per
table and a wider `get()`. No migration, no change to any other service.

---

## 3b. `document-service` — no per-stage progress (Salem)

**Status:** not started, small

`GET /documents/{id}/status` returns `progress: null` on every document, always.
The schema has the field (`ProgressSchema`) and the upload screen renders it,
but nothing populates it.

`processing-service` already knows the answer: `processing_jobs.stage` holds
`extract_text | classify | extract | pii | risk | index | complete` throughout
the run. It is simply never surfaced through `document-service`.

The consequence is that the seven-step pipeline track on `/upload` cannot move.
It can only show queued / processing / done, so a document that is genuinely
being worked on and one whose worker has died look identical. The frontend now
detects the second case by measuring how long the status has been unchanged,
which works but is inference — reading `stage` would be the real answer.

**Also:** a document whose job has permanently failed does not always follow.
Observed during testing: `documents.status = 'PROCESSING'` with the matching
`processing_jobs` row at `FAILED`, attempt 3. The document stays "processing"
forever from the UI's point of view.

---

## 3c. `processing-service` — Docker DNS defaults break local runs (Salem)

**Status:** configuration, no code change needed

`app/config.py` defaults to Compose service names:

```python
ai_service_url:     str = "http://ai-service:8080"
search_service_url: str = "http://search-service:8080"
```

Run outside Compose and neither resolves. Observed effect: classification,
extraction, PII and risk all succeed (because `AI_SERVICE_URL` was exported in
that shell), then the run dies at the last stage:

```
stage=index  ERR_UPSTREAM_UNAVAILABLE
"search-service index transport error: All connection attempts failed"
```

It retries three times and the document ends `failed` — after a long stretch at
`queued` that looks like a hang.

Fix is to export `SEARCH_SERVICE_URL` alongside `AI_SERVICE_URL` when running
locally. Worth considering a `.env.example` in `services/processing-service/`
so the pair is discoverable, since getting one and not the other produces a
failure that looks like a stalled queue rather than a misconfiguration.

---

## 4. Network boundary — nothing restricts direct service access (Salem + Adel)

**Status:** planned, last, highest blast radius

The Gateway now authenticates every proxied route, and commit `17c6f34`
correctly stopped clients from forging `X-User-Email` / `X-User-Role`
*at the Gateway*. **Nothing stops a client from skipping the Gateway.**

- `kubernetes/network-policies/01-default-deny.yaml` is a blanket ingress deny
  with **no allow-from-gateway rule** for `document-service`, `search-service`
  or `ai-service`. Applied as written, the Gateway cannot reach them either.
- Locally, ports 8080/8081/8082 are wide open. Every direct probe in this
  session's testing went straight at them.

**This is a prerequisite for item 2, not a follow-up.** Owner-scoping that
trusts a header is only as strong as the guarantee that only the Gateway can
set it.

### Second, related gap

`proxy.py` strips `Authorization` and injects no downstream credential. So:

- `search-service` only accepts the Gateway's calls today because it runs with
  `DISABLE_AUTH=true`.
- Turn its auth on and **Gateway → search-service returns 401**, breaking
  search and `/qa` in one go.

Whoever enables the netpol needs to decide the downstream auth story at the
same time — service-to-service tokens, mTLS, or search-service trusting the
network boundary instead of a bearer. Doing one without the other breaks
retrieval.

### Verification required before this is called done

1. Every service can still reach the ones it needs (Gateway → all three;
   `document-service` → Postgres/Redis; `processing-service` → Postgres/Redis).
2. Direct access to `:8081` from outside the Gateway is actually refused.

If both cannot be shown, revert.

---

## What the frontend now assumes

So that nobody changes these without knowing what breaks:

- **`admin@documind.com` / `password123`** is the sign-in hint on `/login`
  (`frontend/documind/lib/mock/data.ts`). It mirrors the account seeded in
  `services/api-gateway/app/auth/store.py`. Change one, change the other.
- **The Gateway mounts every proxied route at the same path as the downstream
  service.** `frontend/documind/lib/server/backend.ts` relies on this: mode
  selection is a base-URL swap and nothing else. A Gateway route mounted under
  a prefix would break that assumption.
- **`POST /qa` is used only for unscoped questions.** It accepts a question and
  nothing else, so scoped chat and per-document Q&A use `/search` → `/answer`
  instead. If `/qa` ever grows `document_id` and `top_k`, both paths can
  collapse into it.
- **`/qa` does not filter empty passages** and `ai-service` rejects the whole
  request with a 422 when one appears. `/api/answer` filters; `/qa` retrieves
  inside the Gateway, so the frontend cannot. Worth a two-line guard in
  `routes/ai.py` next time it is touched.
- **Bulk delete and reprocess report per-document failures inside a `200`.**
  Any future caller must read `failed[]` rather than treating a 2xx as success.
