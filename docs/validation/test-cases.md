# Test cases

Functional test cases derived from the project spec. This is the list of
what needs testing, independent of what has been automated — the
`Status` column tracks that separately.

Owner: QA / Performance Engineer. Raise a PR against this file if a
service behaves differently from what a case here assumes.

## Status key

| Status | Meaning                                           |
| ------ | ------------------------------------------------- |
| ✅     | Automated and passing                             |
| ⚠️     | Automated, currently failing — a recorded finding |
| 🔒     | Blocked on something that does not exist yet      |
| 📋     | Specified, not yet automated                      |

## Coverage

193 automated tests across five services plus the end-to-end pipeline.

| Suite                                | Tests | Needs                                         |
| ------------------------------------ | ----- | --------------------------------------------- |
| `tests/integration/search_service`   | 18    | search-service                                |
| `tests/integration/document_service` | 45    | document-service, postgres, redis             |
| `tests/integration/api_gateway`      | 44    | api-gateway, document-service, search-service |
| `tests/integration/ai_service`       | 38    | ai-service                                    |
| `tests/integration/e2e`              | 26    | the full stack                                |
| `tests/smoke`                        | 22    | any deployed environment                      |

Suites skip rather than fail when their target is unreachable, so any
subset runs anywhere. Disruptive tests (stop containers, publish
directly to Redis) need `-m disruptive`. Corpus accuracy needs
`-m accuracy`.

## Blocked on

- **A real embedding backend.** `EMBEDDING_BACKEND=mock` is a hash chain
  with no semantic signal. Retrieval quality cannot be measured under
  it, and any number produced would describe the hash function.
- **A cluster.** Pods, autoscaling, rollback and the OKE load runs.
- **The monolith.** No baseline, no owner — see §11.

## 1. Document upload

| ID    | Case                                         | Expected                                             | Status |
| ----- | -------------------------------------------- | ---------------------------------------------------- | ------ |
| UP-01 | Upload a valid PDF                           | 202, body contains `id`                              | ✅     |
| UP-02 | Filename does not end `.pdf`                 | 415, `ERR_UNSUPPORTED_DOCUMENT`                      | ✅     |
| UP-03 | `.pdf` extension without `%PDF-` magic bytes | Rejected                                             | ✅     |
| UP-04 | Zero-byte file                               | Rejected                                             | ✅     |
| UP-05 | Over the 25 MiB cap                          | Rejected                                             | ✅     |
| UP-06 | Filename containing `../`                    | Sanitised or rejected; never written outside storage | ✅     |
| UP-07 | No file part                                 | 422                                                  | ✅     |
| UP-08 | Two uploads of the same bytes                | Two distinct ids                                     | ✅     |
| UP-09 | Corrupt body, valid header                   | Accepted at upload, fails during processing          | ✅     |
| UP-10 | 100-page PDF                                 | Accepted, processes to completion                    | ✅     |
| UP-11 | Textless PDF (stands in for a scan)          | Fails terminally with `ERR_NO_TEXT_LAYER`            | ✅     |
| UP-12 | Filename containing a null byte              | Sanitised or rejected                                | ✅     |
| UP-13 | Non-ASCII filename                           | Accepted, name preserved                             | ✅     |
| UP-14 | Filename over 255 characters                 | Truncated or rejected                                | ✅     |
| UP-15 | Rejections carry `retryable: false`          | A malformed file will be malformed on retry          | ✅     |

The cap is 25 **MiB**, not 25 million bytes. An earlier fixture built at
26,000,000 bytes was accepted because it sits under 26,214,400 — which
incidentally confirmed the service measures correctly.

OCR is explicitly out of scope per the processing-service README.
Image-only PDFs fail with `ERR_NO_TEXT_LAYER` rather than silently
indexing nothing, which is the right behaviour until OCR exists.

## 2. Document status and listing

| ID    | Case                                  | Expected                                | Status |
| ----- | ------------------------------------- | --------------------------------------- | ------ |
| ST-01 | Status of an existing document        | 200, status in the known set            | ✅     |
| ST-02 | Status of an unknown id               | 404                                     | ✅     |
| ST-03 | Get a document by id                  | 200 with metadata                       | ✅     |
| ST-04 | Get an unknown document               | 404                                     | ✅     |
| ST-05 | List documents                        | 200 with a `rows` array                 | ✅     |
| ST-06 | List row shape                        | id, name, ext, type, status, uploadedAt | ✅     |
| ST-07 | `page_size` limits rows               | At most `page_size` returned            | ✅     |
| ST-08 | Invalid pagination bounds             | Rejected or clamped, never unbounded    | ✅     |
| ST-09 | Oversized `page_size`                 | Does not dump the table                 | ✅     |
| ST-10 | A completed document reports its risk | Risk present, not null                  | ⚠️     |
| ST-11 | A terminal status is final            | Never moves backwards                   | ⚠️     |

**Three vocabularies describe one lifecycle.** `document-service`
reports lowercase (`queued`, `completed`); `processing_jobs` stores
uppercase (`QUEUED`, `COMPLETED`); `documents.status` uses
`UPLOADED|PROCESSING|INDEXED|FAILED` and never says COMPLETED at all.
The processing-service README documents this as deliberate — widening
the CHECK constraint would force a lockstep change in document-service.
Tests match terminal states case-insensitively against every spelling.

## 3. Classification

| ID    | Case                                            | Expected                              | Status |
| ----- | ----------------------------------------------- | ------------------------------------- | ------ |
| CL-01 | Classify an invoice                             | `invoice`                             | ✅     |
| CL-02 | Classify a contract                             | `contract`                            | ✅     |
| CL-03 | Scores returned for every label                 | Each in 0–1                           | ✅     |
| CL-04 | Confidence in range                             | 0–1                                   | ✅     |
| CL-05 | Classification explains itself                  | Non-empty rationale                   | ✅     |
| CL-06 | Unrelated prose                                 | Not classified at full confidence     | ✅     |
| CL-07 | Deterministic                                   | Same input, same label and confidence | ✅     |
| CL-08 | End-to-end: uploaded contract is typed CONTRACT | Via the pipeline, not a direct call   | ✅     |
| CL-09 | End-to-end: uploaded invoice is typed INVOICE   | Classification discriminates          | ✅     |
| CL-10 | Accuracy across the 50-document corpus          | Report against `expected_type`        | 📋     |

The mock backend is rules-based, not random — it returns `rules-only` as
its model and includes the matched signals in its rationale. That makes
behaviour worth asserting even without a real provider.

Note the case: the service returns `invoice`, the ground truth says
`INVOICE`, and `documents.document_type` stores `INVOICE`. Comparisons
are case-insensitive.

## 4. Information extraction

| ID    | Case                                     | Expected                                                                   | Status |
| ----- | ---------------------------------------- | -------------------------------------------------------------------------- | ------ |
| EX-01 | Extract an invoice number                | Exact match                                                                | ✅     |
| EX-02 | Extract a due date                       | ISO 8601                                                                   | ✅     |
| EX-03 | Absent fields                            | Null, confidence 0, no evidence — never invented                           | ✅     |
| EX-04 | Populated fields carry evidence          | Snippet and offset present                                                 | ✅     |
| EX-05 | Evidence offsets are inside the document | Within the input length                                                    | ✅     |
| EX-06 | Confidence in range                      | 0–1 per field                                                              | ✅     |
| EX-07 | Extraction runs in the pipeline          | Rows land in `extracted_fields`                                            | ✅     |
| EX-08 | Per-field accuracy across the corpus     | Report per field, not one aggregate — a 90% average can hide a field at 0% | 📋     |

EX-03 is the one that matters most. A model that invents a plausible
value for a field that is not in the document is worse than one that
returns nothing, because nothing downstream can tell the difference.

## 5. PII detection

| ID     | Case                                     | Expected                         | Status |
| ------ | ---------------------------------------- | -------------------------------- | ------ |
| PII-01 | Detect email                             | Found                            | ✅     |
| PII-02 | Detect phone                             | Found                            | ✅     |
| PII-03 | Detect national ID as its own type       | `NATIONAL_ID`                    | ⚠️     |
| PII-04 | Raw values never returned                | `value` is null in every match   | ✅     |
| PII-05 | Offsets inside the text                  | `0 <= start < end <= len`        | ✅     |
| PII-06 | Placeholders appear in the redacted text | Every match substituted          | ✅     |
| PII-07 | Redaction removes an email entirely      | Original absent                  | ✅     |
| PII-08 | Redaction removes a phone number whole   | No surviving digit groups        | ✅     |
| PII-09 | No false positives on clean prose        | Empty counts                     | ✅     |
| PII-10 | Recall across 250 seeded entities        | Report per type                  | 📋     |
| PII-11 | Page attribution                         | Each entity on its declared page | 📋     |

**PII-03 is a recorded finding.** A 14-digit Egyptian national ID is
classified `CREDIT_CARD` — the card pattern matches any 13–16 digit run,
and `NATIONAL_ID` is not a recognised type at all. It is required by the
project spec alongside email, phone, bank account and address.

PII-04 and PII-08 are the security-relevant ones. Redaction runs before
egress to the AI provider, so a partial match would send real data
outside the system.

## 6. Risk analysis

| ID    | Case                                     | Expected                                  | Status |
| ----- | ---------------------------------------- | ----------------------------------------- | ------ |
| RK-01 | Score a contract                         | 0–100                                     | ✅     |
| RK-02 | Band agrees with the score               | No contradiction                          | ✅     |
| RK-03 | Automatic renewal is flagged             | Finding present                           | ✅     |
| RK-04 | Presence findings quote the text         | Evidence with a snippet                   | ✅     |
| RK-05 | Every finding is identifiable            | `rule_id`, `severity`, `title`            | ✅     |
| RK-06 | Evidence offsets are inside the document | Within the input length                   | ✅     |
| RK-07 | The score responds to content            | Plain prose scores below a risky contract | ✅     |
| RK-08 | Risk runs in the pipeline                | Rows land in `risk_assessments`           | ✅     |
| RK-09 | Band agreement across the corpus         | Report against `expected_risk.band`       | 📋     |

**Findings come in two kinds.** A rule about text that is present must
quote it. A rule about something absent — `R07 No governing law clause`,
`R09 No confidentiality obligation` — legitimately has nothing to point
at. Demanding evidence from both would have flagged correct behaviour as
a defect. The tests distinguish them.

Corpus bands at seed 42: 37 LOW, 8 MEDIUM, 5 HIGH.

## 7. Search and RAG

| ID    | Case                                     | Expected                        | Status |
| ----- | ---------------------------------------- | ------------------------------- | ------ |
| SR-01 | Index returns a chunk count              | 200 with `chunks_indexed`       | ✅     |
| SR-02 | Index rejects an empty body              | 422 naming both missing fields  | ✅     |
| SR-03 | Longer content produces more chunks      | Chunking actually splits        | ✅     |
| SR-04 | Search envelope and field types          | Documented shape                | ✅     |
| SR-05 | Search requires a question               | 422                             | ✅     |
| SR-06 | `top_k` is respected                     | At most `top_k` results         | ✅     |
| SR-07 | Results ordered by descending similarity | Sorted                          | ✅     |
| SR-08 | Round trip on the in-memory backend      | What went in comes back         | ✅     |
| SR-09 | Round trip on the Postgres backend       | Returns results                 | ✅     |
| SR-10 | `top_k` has an upper bound               | Absurd values rejected          | ⚠️     |
| SR-11 | Page survives indexing                   | Citations need a page           | ⚠️     |
| SR-12 | A completed document is retrievable      | End-to-end through the pipeline | ✅     |
| SR-13 | Retrieval hit rate over 270 questions    | Report doc and page hit rate    | 🔒     |
| SR-14 | Answers carry citations                  | Document and page per answer    | 🔒     |
| SR-15 | Unanswerable questions are refused       | No fabricated answer            | 🔒     |

**SR-09 was the most consequential finding so far.** The Postgres
backend returned empty result sets for every query while indexing
reported success. `idx_document_chunks_embedding` was an `ivfflat` index
with `lists=100`: it partitions vectors into 100 clusters and probes one
by default, so a small corpus landed in one or two clusters and any
query elsewhere returned nothing — a 200 with an empty array, never an
error. Confirmed with an identical query embedding: default probes
returned zero rows, `probes=100` returned the row. The in-memory backend
does an exact scan, which is why local testing never surfaced it, and
Postgres is what ships. Fixed by removing the index.

**SR-13 is not measurable yet.** Under `EMBEDDING_BACKEND=mock` any hit
rate describes the hash function, not retrieval.

## 8. Health and resilience

| ID    | Case                                           | Expected                                | Status |
| ----- | ---------------------------------------------- | --------------------------------------- | ------ |
| HL-01 | `/liveness` without auth                       | 200                                     | ✅     |
| HL-02 | `/readiness` without auth                      | 200                                     | ✅     |
| HL-03 | Readiness names each dependency                | postgres and redis reported separately  | ✅     |
| HL-04 | Readiness with Redis down                      | 503, redis marked unavailable           | ✅     |
| HL-05 | Readiness with Postgres down                   | 503, postgres marked unavailable        | ✅     |
| HL-06 | Liveness stays 200 while a dependency is down  | Liveness is not readiness               | ✅     |
| HL-07 | Readiness recovers when the dependency returns | Back to 200 without a restart           | ✅     |
| HL-08 | Upload with the queue down                     | 503, `ERR_QUEUE_UNAVAILABLE`, retryable | ✅     |
| HL-09 | Worker liveness tracks the consumer            | Not just the HTTP server                | ✅     |
| HL-10 | Worker exposes queue depth                     | `documind_processing_stream_pending`    | ✅     |
| HL-11 | Probes answer quickly                          | Under two seconds                       | ✅     |
| HL-12 | Unknown paths leak nothing                     | Clean 404, no stack trace               | ✅     |
| HL-13 | Pod deleted under load                         | Replaced, recovery time recorded        | 🔒     |
| HL-14 | Bad deployment                                 | Readiness fails, traffic not routed     | 🔒     |
| HL-15 | Rollback                                       | Previous version restored               | 🔒     |

HL-06 is the reason both probes exist. If liveness also failed when a
dependency was down, the kubelet would restart a healthy container in a
loop for as long as the outage lasted, instead of routing around it.

HL-08 is the one that would have caused silent data loss: a 202 with no
queue behind it stores the file and nothing ever processes it — a lost
job the client believes succeeded. The service correctly returns 503.

HL-09 is a design detail worth noting: a worker whose consumer task has
died answers HTTP perfectly while the queue grows unattended, and
nothing else in the platform would detect that.

## 9. Auth

| ID    | Case                                           | Expected                                     | Status |
| ----- | ---------------------------------------------- | -------------------------------------------- | ------ | ------------------------------- | --- | --- |
| AU-01 | Register a new user                            | 200, email echoed normalised                 | ✅     |
| AU-02 | Duplicate email                                | 409, `field` is `email`                      | ✅     |
| AU-03 | Malformed email                                | 422                                          | ✅     |
| AU-04 | Password under 8 characters                    | 422                                          | ✅     |
| AU-05 | Org name under 2 characters                    | 422                                          | ✅     |
| AU-06 | Email case is normalised                       | One account, not two                         | ✅     |
| AU-07 | Validation errors name the field               | `ok`, `field`, `title`, `detail`             | ✅     |
| AU-08 | Login with valid credentials                   | 200 with a token                             | ✅     |
| AU-09 | Login returns session details                  | email, name, initials                        | ✅     |
| AU-10 | Wrong password                                 | 401                                          | ✅     |
| AU-11 | Unknown email                                  | 401                                          | ✅     |
| AU-12 | Failed login does not reveal account existence | Identical response either way                | ✅     |
| AU-13 | Password never returned                        | Absent from the body                         | ✅     |
| AU-14 | Well-formed JWT                                | Three segments                               | ✅     |
| AU-15 | Token subject is the user                      | `sub` matches                                | ✅     |
| AU-16 | Token carries a role                           | Present                                      | ✅     |
| AU-17 | Token expires                                  | `exp` in the future                          | ✅     |
| AU-18 | Token lifetime bounded                         | ≤ 24h                                        | ✅     |
| AU-19 | No credential material in claims               | No password or hash                          | ✅     |
| AU-20 | Concurrent sessions                            | A second login does not invalidate the first | ✅     |
| AU-21 | `X-Request-ID` echoed                          | Caller's id survives                         | ✅     |
| AU-22 | `X-Request-ID` generated when absent           | Always present                               | ✅     |
| AU-23 | Health probes need no token                    | 200                                          | ✅     |
| AU-24 | Protected route without a token                |                                              | AU-24  | Protected route without a token | 401 | ✅  |
| AU-25 | Protected route with a garbage token           | 401                                          | ✅     |
| AU-26 | Protected route with a forged signature        | 401                                          | ✅     |
| AU-27 | Protected route with an expired token          | 401                                          | ✅     |
| AU-28 | Protected route with a valid token             | Reaches the downstream service               | ✅     |
| AU-29 | Upload requires a token                        | 401                                          | ✅     |
| AU-30 | Token without the Bearer scheme                | 401                                          | ✅     |
| AU-31 | Wrong auth scheme (Basic)                      | 401                                          | ✅     |
| AU-32 | Proxied response keeps its envelope            | `rows` survives the hop                      | ✅     |
| AU-33 | Downstream 404 is preserved                    | Not rewritten to 500                         | ✅     |
| AU-34 | `X-Request-ID` survives the proxy hop          | Same id end to end                           | ✅     |

AU-12 matters more than it looks. If a wrong password and an unknown
account produce different responses, login becomes an account
enumerator. Both return an identical 401 with identical text.

**AU-26 is the one that matters most.** Anyone can mint claims; only
the issuer can sign them. A token with a bogus signature is rejected —
had it been accepted, a caller could grant themselves any identity or
role, and authentication would be decorative.

AU-18 matters because there is no revocation. An unbounded token stays
usable indefinitely if it leaks.

## 10b. Corpus accuracy

Measured by uploading all 50 generated documents through the full
pipeline and comparing results to the ground truth they were built
from.

| ID    | Metric                                      | Result       |
| ----- | ------------------------------------------- | ------------ |
| AC-01 | Documents reaching a terminal state         | 50/50        |
| AC-02 | Completion rate                             | 50/50 = 100% |
| AC-03 | Classification accuracy                     | 50/50 = 100% |
| AC-04 | Classification produces more than one label | Yes          |
| AC-05 | Completed documents indexed and retrievable | 50/50 = 100% |

**These numbers measure the rule set, not a model.** The mock backend
is rules-based and deterministic rather than random, so they are real
and repeatable — but they are not a claim about OCI Generative AI.
Re-run against a real provider before quoting anything.

Retrieval coverage is measured across six different queries. A single
query capped at `top_k` returns the best-matching chunks, not every
chunk, so a correctly indexed document can miss the cut — a
single-query version reported 94% for a corpus that was fully indexed.

Per-field extraction accuracy and PII recall are specified but not
automated: they are worth measuring against a real provider, not
against the rule set.

## 11. End-to-end and failure modes

| ID     | Case                                           | Expected                                      | Status |
| ------ | ---------------------------------------------- | --------------------------------------------- | ------ |
| E2E-01 | Upload to completion through every service     | Terminal success                              | ✅     |
| E2E-02 | Processing is genuinely async                  | 202 returns before the work is done           | ✅     |
| E2E-03 | A contract is classified as a contract         | Via the pipeline                              | ✅     |
| E2E-04 | An invoice is classified as an invoice         | Classification discriminates                  | ✅     |
| E2E-05 | A completed document is searchable             | Retrievable by query                          | ✅     |
| E2E-06 | Completion is not pathologically slow          | Four pages under 30s                          | ✅     |
| E2E-07 | A truncated PDF reaches a terminal state       | Never stalls in PROCESSING                    | ✅     |
| E2E-08 | A textless PDF does not silently index nothing | Fails or is flagged                           | ✅     |
| E2E-09 | The consumer group exists                      | Otherwise nothing is ever consumed            | ✅     |
| E2E-10 | Completed jobs are acked                       | No lingering pending entries                  | ✅     |
| E2E-11 | A malformed event does not stall the stream    | Valid jobs behind it still complete           | ✅     |
| E2E-12 | Unknown event version                          | Rejected, not guessed at                      | ✅     |
| E2E-13 | Worker readiness fails with Redis down         | 503                                           | ✅     |
| E2E-14 | Worker recovers when Redis returns             | No manual restart                             | ✅     |
| E2E-15 | Work survives a Redis restart                  | Reaches a terminal state                      | ✅     |
| E2E-16 | Redelivery of the same message id              | Not reprocessed                               | ✅     |
| E2E-17 | A completed document does not revert           | Terminal is terminal                          | ⚠️     |
| E2E-18 | Ten concurrent uploads                         | All complete, no lost jobs                    | 📋     |
| E2E-19 | Frontend journey                               | Login → upload → detail → question → citation | 🔒     |

A four-page contract completes in roughly 2.3 seconds with
`degraded=false`, meaning no stage was skipped: text extracted, five
chunks indexed, classification, extraction and risk all recorded.

E2E-07 targets the worst failure mode available — a document that stalls
in PROCESSING forever. The user waits, no alert fires, and nothing marks
the job as needing attention.

**E2E-17 is a recorded finding.** Publishing a fresh message for an
already-completed document reprocesses it, and a failure on that second
pass overwrites COMPLETED with FAILED. The frontend reads this status,
so a document the user watched finish can later display as failed. This
is separate from the message-id idempotency described in the README,
which works correctly — the gap is that there is no protection at the
document level.

## 12. Performance

| ID    | Case                     | Expected                                     | Status |
| ----- | ------------------------ | -------------------------------------------- | ------ |
| PF-01 | Smoke against the target | Passes before any load run                   | ✅     |
| PF-02 | Monolith baseline (M0)   | RPS, P50/P95/P99, error rate, CPU, memory    | 🔒     |
| PF-03 | OKE baseline             | Same script, same corpus, same generator     | 🔒     |
| PF-04 | Stress to failure        | Ceiling identified, first failure mode named | 🔒     |
| PF-05 | Spike                    | HPA scales up, scale-up time recorded        | 🔒     |
| PF-06 | Load drop                | Replicas scale back down                     | 🔒     |
| PF-07 | Soak, 60 minutes         | p95 at the end comparable to the start       | 🔒     |
| PF-08 | Comparison report        | Populated from measured runs only            | 🔒     |

**PF-02 remains the deliverable at risk.** The baseline cannot be
captured after decomposition begins — it is a one-shot window. The k6
scenarios, the 50-document corpus and the cluster metrics collector are
all ready. The monolith is not, and still has no owner.

Thresholds in `tests/load/lib/config.js` are placeholders. Per the test
strategy, OKE thresholds are derived from the measured baseline rather
than invented, so a passing threshold today is not evidence of anything.

---

## Known findings

Confirmed and raised. Recorded here so they are not rediscovered.

| #   | Finding                                                                                           | Where                             | State                                                                               |
| --- | ------------------------------------------------------------------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------------- |
| 1   | `ivfflat` with `lists=100` returned empty result sets on small corpora                            | `database/schema.sql`             | **Fixed** — index removed, SR-09 passes                                             |
| 2   | A 14-digit national ID is classified `CREDIT_CARD`; `NATIONAL_ID` is not a recognised type        | `ai-service`                      | Open, PII-03 xfail                                                                  |
| 3   | Risk is computed and stored but the status endpoint returns `risk: null` and `verdict: "Pending"` | `document-service`                | Open, ST-10 xfail                                                                   |
| 4   | A completed document can revert to FAILED on a spurious reprocess                                 | `processing-service`              | Open, E2E-17 xfail                                                                  |
| 5   | `top_k` has no upper bound — a large value ranks the entire store                                 | `search-service`                  | Open, SR-10 xfail                                                                   |
| 6   | `page` is null for content indexed via `POST /index`                                              | `search-service`                  | Open, SR-11                                                                         |
| 7   | Upload response field is `id`, not `document_id`                                                  | `document-service`                | Resolved in the k6 journey; noted for contract alignment                            |
| 8   | Status values are lowercase; the worker compares uppercase                                        | `tests/load/lib/journey.js`       | **Fixed** — every poll would have timed out                                         |
| 9   | `sentence-transformers` pulls PyTorch and CUDA into the image                                     | `search-service/requirements.txt` | Open — unused under `mock`, and the likely cause of CI disk exhaustion              |
| 10  | The gateway user store is in-memory                                                               | `api-gateway`                     | Open — M1 scope; will not survive a restart or work across replicas                 |
| 11  | Default `STORAGE_DIR` is relative                                                                 | `document-service`                | Open — local runs write uploads into the source tree                                |
| 12  | `app_instrumentation` imports its own submodules absolutely                                       | `services/monitoring`             | Open — any service importing it needs a manual `PYTHONPATH`                         |
| 13  | OTel package versions conflict across services in a shared venv                                   | multiple                          | Open — invisible in Docker, breaks a shared local environment                       |
| 14  | `processing_jobs` is missing from databases created before the table was added                    | `database/schema.sql`             | Environmental — init scripts run once per volume; `docker compose down -v` fixes it |

Findings 7 and 8 were both found by writing contract tests, and both
would have corrupted the first write-journey load run: every upload
recorded as failed against a service that accepted it, and every
document polling to a full 120-second timeout.
