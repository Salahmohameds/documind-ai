# DocuMind AI — Test Strategy

> **Owner:** QA / Performance Engineer (role 8)
> **Status:** Draft v1 — written before services are available, so that test
> assets can be built against a frozen contract and pointed at real endpoints
> with a single environment-variable change.
> **Related:** `docs/PROJECT-PROPOSAL.md` §18 (performance protocol), §20
> (validation matrix), §23 (RAG evaluation), §26 (open decisions) ·
> `docs/validation/test-cases.md` · `docs/validation/validation-matrix.md` ·
> `docs/performance/benchmark-results.md` · `tests/README.md`

---

## 1. Purpose

This document defines **what we test, at which level, with which tools, in
which environment, and when we consider a milestone done**. It is written
under two hard project constraints:

1. **Services are not built yet.** Every test asset must be authored against a
   documented API contract and runnable against a mock, then re-pointed at
   real services without editing test code.
2. **Cloud infrastructure is not left running.** All OKE evidence is captured
   in one short paid burst (proposal §19). Tests therefore have to be
   *rehearsed to green* locally (docker compose + kind) before the burst
   begins — the burst is for capturing evidence, not for debugging tests.

Everything here serves the eight success criteria (proposal §1). The
traceability map is in §13.

---

## 2. Scope

### 2.1 In scope

| Area | What is validated |
|------|-------------------|
| Functional — API | Auth, upload, async job lifecycle, document list/detail, extracted fields, PII entities, risk score/findings, RAG query + citations |
| Functional — UI | Next.js frontend critical path: login → upload → processing → document detail → RAG question → citation rendering |
| Contract | Request/response shapes match the frozen API contract (`docs/architecture/api-contracts/`) |
| Integration | Cross-service flow: gateway → document-service → queue → processing-service → ai-service → search-service → vector store |
| AI quality | Classification accuracy, extraction schema validity + field accuracy, PII recall, risk band, RAG retrieval hit@k / faithfulness / latency |
| Performance | Monolith baseline vs OKE microservices under identical k6 scenarios (smoke, baseline, stress, spike, soak) |
| Resilience | Pod self-healing recovery time, HPA scale up/down, rolling update with no error spike, rollback |
| Security (verification, not pentest) | 401 without JWT, 403 wrong role, rate limiting, NetworkPolicy denial to DB, DB not internet-reachable, upload validation (type/size), no PII in logs |
| Negative / edge | Corrupt, 0-byte, oversized, wrong-type, password-protected, scanned-image, 100-page documents |

### 2.2 Out of scope

* Penetration testing, fuzzing, red-teaming beyond the checks above.
* Model fine-tuning quality, prompt A/B testing, or LLM benchmarking beyond the
  15–20 item golden set (§23).
* Multi-region failover; chaos engineering beyond scripted pod deletion.
* Browser matrix testing — Playwright runs **Chromium only** (scope discipline;
  see risk R7).
* Accessibility and visual-regression testing.
* Load testing OCI Generative AI itself. See §9.4 — the LLM is stubbed or
  capped during load runs. We measure *our* architecture, not Oracle's endpoint.

### 2.3 Explicitly deferred (documented, not done)

Node-level chaos injection, DR restore drills (`docs/disaster-recovery/`), and
cost-per-request measurement (`docs/cost/`) are owned elsewhere and are not QA
deliverables.

---

## 3. Quality objectives and risk-based prioritisation

We do not aim for exhaustive coverage. We aim for **evidence that the eight
success criteria are met**, weighted by risk.

| Priority | Area | Rationale |
|----------|------|-----------|
| P0 | Critical path: upload → poll → all pipeline outputs present → RAG answer with citation | If this breaks, there is no demo. Everything else is secondary. |
| P0 | Performance comparison (monolith vs OKE) | Success criterion S3; the analytical core of the report, and it cannot be re-run after teardown. |
| P1 | Async contract (202 + job states), auth/authz, resilience demos | S1, S4, S5, S6. |
| P1 | RAG evaluation golden set | S7. |
| P2 | Extraction field accuracy, PII recall, risk banding | Quality claims must be measured, but partial results are still publishable. |
| P3 | Edge-case document handling, rate limiting, UI polish | Nice-to-have evidence; first to be cut. |

**Degradation rule:** if time runs short we cut P3, then P2. We never cut P0.
This is written down now, calmly, rather than decided in week 5 under pressure.

---

## 4. Test levels

| Level | Location | Owner | Runs against | Gate |
|-------|----------|-------|--------------|------|
| **Unit** | `services/<name>/tests/` | Each service owner | In-process, no network | CI on every PR — blocking |
| **Shared unit utilities** | `tests/unit/` | QA | Pure functions (ground-truth loaders, scorers) | CI on every PR — blocking |
| **Contract** | `tests/integration/contract/` | QA | Response schema validation against the frozen contract | CI on every PR — blocking once services land |
| **Integration** | `tests/integration/` | QA | `docker compose` stack or dev OKE (`BASE_URL`) | CI nightly + pre-merge to main |
| **E2E (UI)** | `tests/e2e/` | QA | Frontend + full stack (`WEB_BASE_URL`) | CI nightly; manual before demo |
| **Smoke** | `tests/smoke/` | QA | Any deployed environment | Post-deploy, blocking in `cd.yml` |
| **Load / performance** | `tests/load/` | QA | Monolith VM **and** OKE, same scripts | Manual, controlled runs only |
| **Resilience** | `tests/smoke/` + runbook | QA + Platform | dev OKE | Manual, burst day 3 |
| **RAG evaluation** | `tests/rag-evaluation/` | QA + AI owner | Deployed search + ai service | Manual per milestone; recorded per run |

### 4.1 Why the pyramid is deliberately squashed

Unit tests live with the services and are owned by their authors. QA owns
**integration and above**, because the interesting failures in a microservices
migration are *between* services — serialization, timeouts, queue retries, auth
propagation — not inside a single function. A conventional pyramid would
over-invest the one QA person's time where risk is lowest.

Mock-first authoring makes this workable before services exist: the same pytest
suite runs against an in-repo contract mock today and real endpoints later,
with only `BASE_URL` changing.

---

## 5. Tools

| Purpose | Tool | Why |
|---------|------|-----|
| API / integration tests | **pytest** + `httpx` | Team already uses Python; async client matches the async API |
| Contract mocking (pre-integration) | **respx** or a small FastAPI stub app | Mock stays in-process and in the repo — no extra infrastructure |
| Schema validation | **pydantic v2** models generated from the frozen contract | One definition used by both assertions and mocks |
| Load testing | **k6** | Proposal §18; scriptable thresholds, CI-friendly, JSON summaries |
| E2E UI | **Playwright** (language per D-QA-4) | Auto-waiting matches an async pipeline with a polling UI |
| RAG scoring | pytest + a small scoring module | Avoids a heavyweight eval framework for a 15–20 item set |
| CI | **GitHub Actions** (`.github/workflows/ci.yml`) | Already established |
| Evidence capture | k6 JSON summaries, `kubectl` output, Grafana screenshots, screen recordings | Proposal §19 evidence checklist |

Rejected on purpose: Locust (k6 is the committed tool), Postman/Newman (not
gitops-friendly here), Cypress (Playwright's auto-wait handles the polling UI
better), managed load-testing SaaS (cost).

---

## 6. Environments

| Env | What it is | Purpose | Availability |
|-----|-----------|---------|--------------|
| **local-mock** | pytest + in-repo contract mock, no services | Author and green-light every test before services land | Now |
| **local-compose** | `docker-compose.yml` — 5 services + Postgres + Redis | Integration + E2E development | From M1 |
| **kind** | Local Kubernetes rehearsal | Probes, HPA, NetworkPolicy, rollback rehearsal — free | From M2 |
| **monolith-baseline** | Single container on an OCI Compute VM (D5) | Performance baseline only — **planned, no owner assigned (D-QA-3)** | M0 / burst |
| *monolith-baseline (fallback)* | The `docker-compose` monolith on a developer machine | Degraded baseline used **only** if M0 is never captured on a VM — see §9.2.1 | contingency |
| **dev-oke** | OKE cluster, namespace `documind` | Smoke, integration, official k6 runs, all evidence | Burst days 1–5 only |

### 6.1 Configuration — no hardcoded URLs, ever

Every suite reads its target from the environment. A missing required variable
fails loudly at session start with a clear message; it never falls back to
`localhost`.

| Variable | Used by | Example | Required |
|----------|---------|---------|----------|
| `BASE_URL` | pytest, k6, smoke | `http://localhost:8080` / `https://dev.documind.example` | yes |
| `WEB_BASE_URL` | Playwright | `http://localhost:3000` | E2E only |
| `TEST_USER_EMAIL` / `TEST_USER_PASSWORD` | all | seeded non-admin account | yes |
| `TEST_ADMIN_EMAIL` / `TEST_ADMIN_PASSWORD` | authz tests | seeded admin account | authz only |
| `TEST_TIMEOUT_S` | pytest | `120` | no (default 120) |
| `POLL_INTERVAL_S` | pytest, k6 | `2` | no (default 2) |
| `TARGET_LABEL` | k6 | `monolith` \| `oke` | perf runs |
| `K6_SCENARIO` | k6 | `smoke` \| `baseline` \| `stress` \| `spike` \| `soak` | perf runs |
| `SAMPLE_DOCS_DIR` | pytest, k6 | `./sample_documents` | no (default) |

Credentials come from GitHub Actions secrets in CI and a git-ignored `.env`
locally. Nothing is committed — `gitleaks` already runs in CI and will fail the
build if it is.

---

## 7. Test data approach

Full detail lives in the test data plan (deliverable 3); the strategy-level
position is:

1. **Synthetic only. Zero real PII.** All invoices/contracts are generated.
   Seeded "PII" is fabricated — invalid-by-construction national IDs,
   `example.com` emails, reserved phone ranges — so leaking the repo leaks
   nothing.
2. **Ground truth is data, not assertions.** Each sample document has a
   companion ground-truth record (expected classification, extracted fields,
   PII entities, risk band). Tests iterate over the ground-truth file; adding a
   document adds a test case with no code change.
3. **One corpus, three consumers.** The same ~50-document synthetic corpus
   feeds functional tests, the k6 load runs (§18 requires identical data across
   architectures), and the RAG golden set. Divergent corpora would invalidate
   the comparison.
4. **Tolerances are declared, not implied.** Numeric fields compare exactly;
   dates normalise to ISO-8601 before comparison; free-text fields
   (`payment_terms`) use normalised substring matching. Risk is asserted as a
   **band** (LOW/MEDIUM/HIGH), never an exact integer — a test demanding `72`
   from an LLM will flake forever.
5. **Edge cases are fixtures, not accidents.** Corrupt PDF, scanned image,
   0-byte, wrong MIME type, 100-page, password-protected — each generated by a
   committed script so any teammate can recreate them.
6. **Seeding is idempotent.** `tests/fixtures/seed.py` (or `database/seed.sql`)
   creates the test users and can be re-run safely.

---

## 8. Entry and exit criteria

### 8.1 Per level

| Level | Entry | Exit |
|-------|-------|------|
| Unit | Code compiles; PR open | All unit tests pass; no new lint errors |
| Contract | API contract frozen by the Backend Lead | Every documented endpoint has a schema assertion; mock and real responses validate against the same models |
| Integration | `docker compose up` all-healthy; test users seeded | P0 + P1 cases pass; no open Sev-1/Sev-2 |
| E2E | Frontend builds; integration green | Critical path passes 3 consecutive runs (flake check) |
| Smoke | Deployment reports Ready | All `/readiness` green; upload happy path completes; runtime < 60 s |
| Load | Smoke green; environment idle-stable 5 min; no other workload on the cluster | 3 runs per architecture per scenario; thresholds evaluated; raw JSON archived |
| RAG eval | Corpus indexed; golden set authored | All 15–20 items scored; results file committed with commit SHA + model name |

### 8.2 Milestone gates (mapped to proposal §19)

| Milestone | QA exit criterion |
|-----------|-------------------|
| **M0** — monolith baseline | k6 smoke + baseline against the containerized monolith; results archived in `docs/performance/` **and committed to git before decomposition begins**. The *only* chance to capture the baseline, so it is blocking. **Currently unowned and undated — escalated (D-QA-3, R5).** |
| **M1** — 5 services on compose | Critical-path integration test green on compose; contract tests green |
| **M2** — deploy-ready | Full suite green on kind; resilience rehearsals (pod kill, HPA, rollback) recorded once for free; CI green |
| **Burst day 2** | Smoke green against dev-oke within 15 minutes of deploy |
| **Burst day 3** | Every §20 validation-matrix row has evidence; 3 runs × 5 scenarios archived; RAG eval recorded |
| **Final** | `docs/performance/benchmark-results.md` and `docs/validation/validation-matrix.md` complete with measured numbers and no placeholders |

### 8.3 Suspension criteria

Testing stops and the blocker is escalated when the environment cannot reach
all-Ready for > 30 min, a Sev-1 defect blocks the critical path, or GenAI
quota/rate limits make AI responses unrepresentative. During the paid burst
suspension is expensive — hence the rehearse-on-kind-first rule.

---

## 9. Performance: monolith vs OKE comparison methodology

The most scrutinised deliverable (S3), so the protocol is fixed **before** any
number exists. This extends proposal §18.

### 9.1 What we are actually comparing

We are **not** claiming microservices are faster. Five services with a network
hop per boundary will very likely show *higher* latency at low load. The thesis
under test is:

> The monolith is faster at low concurrency and degrades sharply past its
> single-instance ceiling; the OKE deployment pays a fixed latency overhead but
> degrades gracefully because it scales horizontally and isolates failure.

The report therefore treats latency-at-low-load and
throughput-and-error-rate-under-stress as *two findings*, not one verdict.
Where the monolith wins, we say so.

### 9.2 Controlled variables

| Variable | Held constant | How |
|----------|---------------|-----|
| Script | Identical k6 files, unchanged | Only `BASE_URL`, `TARGET_LABEL`, `K6_SCENARIO` differ |
| Corpus | Same ~50 synthetic documents | `SAMPLE_DOCS_DIR`, same commit |
| Request mix | Same weights (§9.3) | Declared in the script, not on the command line |
| VU profile | Same stages per scenario | Declared in the script |
| Load generator | Same machine, same region as the target | Dedicated OCI VM in-region — **not** a GitHub runner (§9.5) |
| AI dependency | Same stub/cap on both sides | §9.4 |
| Data volume | Same pre-seeded document count before each run | Reset script between runs |
| Runs | 3 per scenario per architecture, median reported | Discard run 1 only for cold-start outliers, and *say so* in the report |

Sizing fairness: the monolith VM is sized comparably to **one** OKE worker node
(D5). The cluster having more total capacity is a real difference we document
rather than hide — it is the point of the architecture, and §18 already
requires a fairness-caveats section.

### 9.2.1 Baseline target, and the fallback if M0 is missed

The k6 scripts are written against a **real containerized monolith on an OCI
Compute VM** — the Phase 1 / Phase 2 baseline the proposal already mandates.
Nothing in the scripts is specific to it: the target is `BASE_URL` and the run
is tagged with `TARGET_LABEL=monolith`, so the same file runs against whatever
host we point it at.

**The baseline is currently planned but unowned and undated (D-QA-3), and it is
the top escalation item in this strategy.** It is irrecoverable: once the
monolith is decomposed, there is nothing left to measure, and success criterion
S3 fails with no way to recover it late. The M0 gate (§8.2) stays blocking for
exactly this reason.

If M0 is never captured on a VM, the contingency is the **`docker-compose`
monolith on a developer machine**, and the strategy is explicit that this is a
*degraded* baseline, not an equivalent one:

| | Intended baseline | Fallback baseline |
|---|---|---|
| Host | OCI Compute VM, in-region, sized to ~1 worker node | Developer laptop/desktop, shared with other processes |
| Network path to load generator | In-region VM → VM | Loopback — no real network latency at all |
| Comparability with OKE | Fair; the intended comparison | Weak; laptop CPU, thermal throttling and loopback all confound the numbers |
| How it is reported | Headline comparison table | Reported as *indicative only*, with the confound list stated inline, and the S3 claim narrowed to "we could not capture a like-for-like baseline" |

We do not quietly substitute one for the other. If the fallback is used, the
performance report says so in the first paragraph. A stated methodological
limitation is defensible; an undisclosed one is not.

### 9.3 Request mix

Weighted to resemble real usage rather than hammering one endpoint:

| Weight | Operation | Notes |
|-------:|-----------|-------|
| 10% | `POST /auth/login` | Otherwise tokens are reused across all iterations |
| 20% | `POST /documents` (upload) | Write path; async, expects 202 |
| 35% | `GET /documents/{id}/status` | Polling path — realistically the highest-volume call |
| 15% | `GET /documents` (list) | Read path with pagination |
| 10% | `GET /documents/{id}` (detail) | Heaviest read (fields + PII + risk) |
| 10% | `POST /query` (RAG) | Most expensive; kept low so it does not dominate the run |

Weights are frozen with the contract and identical across architectures.

### 9.4 Handling the AI dependency (open decision D-QA-2)

OCI Generative AI is external, rate-limited and billed. Including it in a stress
run measures Oracle's endpoint and burns budget.

* **(A, recommended)** Services support `AI_MODE=stub`, returning a canned
  response after a fixed simulated delay. Load runs use the stub on **both**
  architectures; real AI latency is measured separately in a small dedicated run.
* (B) Real AI everywhere at low VU counts — realistic, but budget-hostile and noisy.
* (C) Real AI on the OKE side only — invalidates the comparison. Rejected.

Option A needs a service feature flag, so it is a Backend/AI decision. Tracked
as **D-QA-2**.

### 9.5 Where load is generated

Running k6 from a GitHub Actions runner adds uncontrolled internet latency and
makes the two architectures incomparable. Official runs execute from a
**dedicated OCI Compute VM in the same region as both targets**. GitHub Actions
runs only the k6 *smoke* scenario as a functional gate with relaxed thresholds —
never numbers that go in the report.

### 9.6 Scenarios and thresholds

Thresholds are declared inside each script so a run passes or fails on its own
terms. Absolute values are placeholders until M0 exists — **OKE thresholds are
set from the measured monolith baseline**, not invented. That is the honest way
to have thresholds before having data.

| Scenario | Shape | Purpose |
|----------|-------|---------|
| smoke | 1 VU, ~1 min | Does the deployment work at all? CI gate. |
| baseline | Constant modest VUs, 5–10 min | The headline comparison number |
| stress | Ramp until error rate or p95 breaches | Find each architecture's ceiling |
| spike | Sudden jump and drop | HPA reaction and recovery (S5) |
| soak | Low load, 30–60 min | Memory leaks, connection-pool exhaustion, queue backlog drift |

Threshold families: `http_req_duration` p(95)/p(99); `http_req_failed` rate;
per-endpoint sub-thresholds for upload and RAG (different budgets from a status
poll); and a custom `job_completion_time` trend for the async pipeline — a 202
returned in 40 ms means nothing if the job never completes.

### 9.7 Metrics captured per run

RPS, avg, p50/p95/p99, error rate by status class, job completion time, CPU %
and memory % (Grafana), pod count over time (`kubectl get hpa -w`), recovery
time after pod kill. Every run archives the raw k6 JSON summary, commit SHA,
image tags, `TARGET_LABEL`, timestamp and cluster state.

### 9.8 Reporting

`docs/performance/benchmark-results.md` uses the §18 template, and every table
carries its fairness caveats. Any number from a single run rather than a median
of three is labelled as such.

---

## 10. Resilience, security and AI-quality verification

| Check | Method | Evidence |
|-------|--------|----------|
| Pod self-healing | `kubectl delete pod` during a running k6 baseline | Recovery time + errors in the window; video |
| HPA scale up/down | k6 spike scenario | `kubectl get hpa -w` output + Grafana replica graph |
| Rolling update, no downtime | Continuous k6 during `kubectl set image` | Flat error rate in k6 output |
| Rollback | Broken-readiness v2, then `rollout undo` | `rollout history` + smoke green after undo |
| Auth required | Request without JWT | 401 asserted in pytest |
| RBAC | `user` token on an admin route | 403 asserted in pytest |
| Rate limiting | Burst above the gateway limit | 429 asserted; limit read from config, not hardcoded |
| NetworkPolicy | Debug pod → Postgres | Connection denied; command output captured |
| DB not internet-reachable | External probe | Timeout + NSG rule listing |
| No PII in logs | grep seeded PII values across pod logs | Empty result set |
| Classification accuracy | Corpus vs ground truth | ≥ 95% (proposal §20) |
| Extraction validity | JSON-schema validation | 100% schema-valid; field accuracy reported as a percentage |
| PII recall | Seeded entities vs detected | Recall reported; false positives listed |
| RAG quality | Golden set (§23) | hit@k, correctness, faithfulness, latency |

---

## 11. Risk areas

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| R1 | API contract changes after tests are written | High — rework across all suites | Freeze the contract with the Backend Lead (deliverable 2); one pydantic model set as single source of truth, so a change is a one-file edit |
| R2 | Services land late; no time to debug tests during the burst | High | Mock-first authoring; every suite green against mocks before M1; kind rehearsal at M2 |
| R3 | Non-deterministic LLM output causes flaky assertions | High | Assert bands, schema validity and presence — never exact LLM strings; tolerances declared in the ground-truth format |
| R4 | Async timing flakiness (poll timeouts) | Medium | One central polling helper with configurable timeout/backoff; on timeout it reports the last observed job state, not just "failed" |
| **R5** | **Monolith baseline never captured before decomposition.** Planned in the proposal (Phase 1/2) but **no owner, no date** as of v1.1 | **High — S3 unachievable and irrecoverable** | **Top escalation item.** M0 is a blocking gate; baseline results committed to git before decomposition starts; QA raises D-QA-3 at every weekly checkpoint until an owner and date exist. Degraded `docker-compose` fallback defined in §9.2.1 and reported as such |
| R6 | GenAI quota/rate limits distort results | Medium | `AI_MODE=stub` for load (D-QA-2); real-AI latency measured separately |
| R7 | QA capacity is one student; testing scope creep | Medium | Priority ladder in §3 plus the written degradation rule |
| R8 | Load generated from the wrong place makes numbers incomparable | High | §9.5: official runs from an in-region VM only |
| R9 | Evidence lost at teardown | High | `docs/plan/EVIDENCE-CHECKLIST.md` verified before `terraform destroy`; raw artefacts committed to git, never left only in the cluster |
| R10 | Test data accidentally contains real PII | Medium | Synthetic-only rule; gitleaks in CI; PII drawn from reserved/invalid ranges |
| R11 | Frontend and API drift (frontend was built against mocks) | Medium | Playwright E2E against the real stack nightly from M1; the frontend's `lib/api.ts` seam maps 1:1 to the frozen contract |

---

## 12. CI integration

| Workflow | Trigger | QA jobs |
|----------|---------|---------|
| `ci.yml` | PR | unit, contract (schema-only, against mocks), lint — target < 5 min |
| `ci.yml` | PR touching `tests/**` or `services/**` | integration against a compose stack spun up in the runner |
| nightly | schedule | full integration + Playwright E2E against the last deployed environment, if one exists |
| `cd.yml` | merge to main → deploy | smoke suite post-deploy; failure blocks promotion |
| manual (`workflow_dispatch`) | on demand | k6 smoke only (§9.5 — never report numbers) |

Rules: no test may require a hand-configured local file; everything comes from
env vars and repo-committed fixtures. Tests needing a deployed environment skip
cleanly with a clear reason when `BASE_URL` is unset, rather than failing the
build red for the wrong reason.

---

## 13. Traceability

| Success criterion | Primary evidence | Produced by |
|---|---|---|
| S1 full pipeline works | Critical-path integration test + E2E | deliverables 5, 7 |
| S2 reproducible infra | destroy → apply → smoke green | smoke suite |
| S3 real performance numbers | k6 runs, both architectures | deliverable 6 |
| S4 survives failure injection | Pod-kill recovery timing | §10 |
| S5 autoscaling demonstrated | Spike scenario + HPA watch | deliverable 6 |
| S6 layered security verified | authz, netpol, rate-limit checks | §10, deliverable 4 |
| S7 AI quality measured | RAG golden-set results | `tests/rag-evaluation/` |
| S8 decisions documented | ADRs + this strategy | docs |

Row-level traceability from the §20 validation matrix to individual test-case
IDs lives in `docs/validation/test-cases.md` (deliverable 4).

---

## 14. Defect management

Severity is defined by demo impact, since the deliverable is a defensible
demonstration:

| Sev | Definition | Action |
|-----|------------|--------|
| 1 | Critical path broken (upload, processing, RAG answer) | Stop testing; escalate immediately |
| 2 | A success criterion cannot be evidenced | Fix before the burst |
| 3 | Non-critical functional bug; edge case mishandled | Fix if time permits, else document as a known limitation |
| 4 | Cosmetic / documentation | Backlog |

Known limitations are **documented, not hidden** — a limitation stated in the
report costs nothing; one found by a reviewer costs credibility.

---

## 15. Open decisions blocking QA

Each needs a team answer; each has a recommended default so work continues
meanwhile. Extends proposal §26.

| ID | Question | Blocks | QA default until answered |
|----|----------|--------|---------------------------|
| D-QA-1 | Is the API contract (deliverable 2) frozen, and where does it live? | All test authoring | Assume the proposed contract; regenerate models when frozen |
| D-QA-2 | Will services support `AI_MODE=stub` for load runs? | §9.4, deliverable 6 | Scripts work either way; official runs assume the stub |
| **D-QA-3** | **Who owns capturing the M0 monolith baseline, and by when?** Answered 2026-08-25: *planned and documented in the proposal, but unowned and undated.* Escalated to the team the same day. | **S3 — irrecoverable if missed** | k6 scripts written against a real containerized monolith target; `docker-compose` fallback documented in §9.2.1; QA re-raises this weekly until an owner and date are set |
| D-QA-4 | Playwright in Python or TypeScript? | Deliverable 7 | TypeScript, co-located with the Next.js frontend it drives |
| D-QA-5 | Token shape — JWT in `Authorization: Bearer`, TTL, refresh? | Auth helper in every suite | Bearer, no refresh, TTL long enough for a soak run |
| D-QA-6 | Is the job id the same as the document id, or separate? | Polling helper, contract | Separate `job_id` from upload; `document_id` on completion |
| D-QA-7 | Pagination style for `GET /documents` — offset or cursor? | Contract, list tests | `limit`/`offset` + `total` |
| D-QA-8 | Are risk score and findings on document detail, or a separate endpoint? | Contract, detail tests | Embedded in document detail |
| D-QA-9 | What do citations point at — page, chunk id, or both? | RAG assertions, E2E | Both: `document_id`, `page`, `chunk_id`, `snippet` |
| D-QA-10 | Final vector store (D3) and queue (D2) choices | Integration fixtures, soak expectations | pgvector + Redis Streams |

---

## 16. Deliverables owned by QA

1. `docs/validation/test-strategy.md` — this document
2. API contract proposal (TypeScript types + example JSON) for Backend Lead sign-off
3. Test data plan: ground-truth format + edge-case corpus
4. `docs/validation/test-cases.md`
5. `tests/integration/` — pytest suite (conftest, fixtures, helpers, critical path)
6. `tests/load/` — k6 smoke / baseline / stress / spike / soak
7. `tests/e2e/` — Playwright critical path
8. `docs/performance/benchmark-results.md` — measured numbers
9. `tests/rag-evaluation/` — golden set, scorer, results
10. `docs/validation/validation-matrix.md` — §20 matrix with evidence links

---

## 17. Revision history

| Version | Date | Change |
|---------|------|--------|
| v1 draft | 2026-08-25 | Initial strategy, written pre-integration against the proposed contract |
| v1.1 | 2026-08-25 | D-QA-3 answered: monolith baseline is planned but unowned/undated. R5 raised to top escalation item; M0 gate reworded as blocking; §9.2.1 added with the degraded `docker-compose` fallback baseline |
