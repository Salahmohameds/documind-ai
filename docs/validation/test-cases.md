# Test cases

Functional test cases derived from the project spec. This is the list of
what needs testing, independent of what has been automated so far — the
`Status` column tracks that separately.

Owner: QA / Performance Engineer. Raise a PR against this file if a
service behaves differently from what a case here assumes.

## Status key

| Status | Meaning                                      |
| ------ | -------------------------------------------- |
| ✅     | Automated and passing                        |
| ⚠️     | Automated, currently failing — see notes     |
| 🔒     | Blocked on a service that does not exist yet |
| 📋     | Specified, not yet automated                 |

## Blocked on

Three services are empty directories, so anything crossing them is 🔒:

- `api-gateway` — authenticates and issues JWTs, but does not yet proxy
  to the downstream services, so nothing behind it is protected
- `processing-service` — nothing consumes the `document_jobs` stream,
  so an uploaded document never leaves `UPLOADED`
- PDF text extraction — lives in `processing-service`; `ai-service`
  takes text, `document-service` takes PDF, nothing bridges them

---

## 1. Document upload

| ID    | Case                                              | Expected                                                              | Status |
| ----- | ------------------------------------------------- | --------------------------------------------------------------------- | ------ |
| UP-01 | Upload a valid PDF                                | 202, body contains `document_id`                                      | 📋     |
| UP-02 | Upload a file whose name does not end `.pdf`      | 400                                                                   | 📋     |
| UP-03 | Upload a file without `%PDF-` magic bytes         | 400                                                                   | 📋     |
| UP-04 | Upload a 0-byte file                              | 400                                                                   | 📋     |
| UP-05 | Upload a file over the 25 MB cap                  | 413 or 400                                                            | 📋     |
| UP-06 | Filename containing `../` path traversal          | Rejected, no write outside storage dir                                | 📋     |
| UP-07 | Upload with no file part                          | 422                                                                   | 📋     |
| UP-08 | Two uploads of the same file                      | Two distinct `document_id` values                                     | 📋     |
| UP-09 | Upload a corrupt PDF (valid header, damaged body) | Accepted at upload, fails in processing with a clear status           | 🔒     |
| UP-10 | Upload a 100-page PDF                             | Accepted, processing completes                                        | 🔒     |
| UP-11 | Upload a scanned image-only PDF                   | Documented behaviour — extract or fail explicitly, not silently empty | 🔒     |

Fixtures for UP-04, UP-09, UP-10, UP-11 come from
`tests/fixtures/generator` edge cases.

## 2. Document status and listing

| ID    | Case                                                          | Expected                                                       | Status |
| ----- | ------------------------------------------------------------- | -------------------------------------------------------------- | ------ |
| ST-01 | Status of a document that exists                              | 200, status is one of QUEUED / PROCESSING / COMPLETED / FAILED | 📋     |
| ST-02 | Status of an unknown id                                       | 404                                                            | 📋     |
| ST-03 | Status transitions in order                                   | Never moves backwards, terminal states are final               | 🔒     |
| ST-04 | List documents                                                | 200, paginated envelope                                        | 📋     |
| ST-05 | Pagination bounds — `page=0`, negative, oversized `page_size` | 422 or clamped, documented either way                          | 📋     |
| ST-06 | Filter by type and status                                     | Only matching documents returned                               | 📋     |
| ST-07 | Get a document by id                                          | 200 with metadata                                              | 📋     |
| ST-08 | Get an unknown document                                       | 404                                                            | 📋     |

## 3. Classification

| ID    | Case                                             | Expected                                                              | Status |
| ----- | ------------------------------------------------ | --------------------------------------------------------------------- | ------ |
| CL-01 | Classify a generated invoice                     | `INVOICE`                                                             | 🔒     |
| CL-02 | Classify a generated contract                    | `CONTRACT`                                                            | 🔒     |
| CL-03 | Classification accuracy across the 50-doc corpus | Report accuracy against `expected_type`; no threshold until measured  | 🔒     |
| CL-04 | Classify a document that is neither              | Low confidence or an explicit unknown — never a confident wrong label | 🔒     |
| CL-05 | Confidence is returned and within 0–1            | Present, in range                                                     | 🔒     |

Ground truth: `expected_type` in `tests/fixtures/ground-truth/*.json`.

## 4. Information extraction

| ID    | Case                                       | Expected                                                                   | Status |
| ----- | ------------------------------------------ | -------------------------------------------------------------------------- | ------ |
| EX-01 | Extract invoice fields                     | vendor, invoice_number, total, currency, due_date present                  | 🔒     |
| EX-02 | Extract contract fields                    | parties, start_date, end_date, payment_terms present                       | 🔒     |
| EX-03 | Per-field accuracy across the corpus       | Report per field, not one aggregate — a 90% average can hide a field at 0% | 🔒     |
| EX-04 | Numeric fields are numbers, not strings    | Correct types in the response                                              | 🔒     |
| EX-05 | Dates are ISO 8601                         | `YYYY-MM-DD`                                                               | 🔒     |
| EX-06 | A field genuinely absent from the document | Null or omitted — never invented                                           | 🔒     |

Ground truth: `expected_fields`.

## 5. PII detection

| ID     | Case                                      | Expected                                                     | Status |
| ------ | ----------------------------------------- | ------------------------------------------------------------ | ------ |
| PII-01 | Detect email                              | Found, correct page                                          | 🔒     |
| PII-02 | Detect phone                              | Found, correct page                                          | 🔒     |
| PII-03 | Detect national ID                        | Found, correct page                                          | 🔒     |
| PII-04 | Detect bank account                       | Found, correct page                                          | 🔒     |
| PII-05 | Detect address                            | Found, correct page                                          | 🔒     |
| PII-06 | Recall across 250 seeded entities         | Report recall per type                                       | 🔒     |
| PII-07 | False positives on clean text             | Report precision — over-detection makes the feature unusable | 🔒     |
| PII-08 | Values are masked by default in responses | Unmasked only on explicit request                            | 🔒     |

Ground truth: `expected_pii`, including the page each entity is on.

## 6. Risk analysis

| ID    | Case                                           | Expected                                       | Status |
| ----- | ---------------------------------------------- | ---------------------------------------------- | ------ |
| RK-01 | Score a contract with auto-renewal             | `auto_renewal` flagged                         | 🔒     |
| RK-02 | Score a contract with short termination notice | `short_termination_notice` flagged             | 🔒     |
| RK-03 | Score is 0–100                                 | In range                                       | 🔒     |
| RK-04 | Band matches score                             | LOW / MEDIUM / HIGH consistent with the number | 🔒     |
| RK-05 | Band agreement across the corpus               | Report agreement with `expected_risk.band`     | 🔒     |
| RK-06 | Every finding cites a source page              | Page present and within the document           | 🔒     |
| RK-07 | Invoices score LOW                             | No spurious contract risk on invoices          | 🔒     |

Corpus bands: 37 LOW, 8 MEDIUM, 5 HIGH at seed 42.

## 7. Search and RAG

| ID    | Case                                     | Expected                                                      | Status                     |
| ----- | ---------------------------------------- | ------------------------------------------------------------- | -------------------------- |
| SR-01 | Index returns a chunk count              | 200 with `chunks_indexed`                                     | ✅                         |
| SR-02 | Index rejects an empty body              | 422 naming both missing fields                                | ✅                         |
| SR-03 | Longer content produces more chunks      | Chunking actually splits                                      | ✅                         |
| SR-04 | Search envelope and field types          | `question` echoed, `results` an array of the documented shape | ✅                         |
| SR-05 | Search requires a question               | 422                                                           | ✅                         |
| SR-06 | `top_k` is respected                     | At most `top_k` results                                       | ✅                         |
| SR-07 | Results ordered by descending similarity | Sorted                                                        | ✅                         |
| SR-08 | Indexed content is retrievable           | Round trip returns what went in                               | ✅                         |
| SR-09 | Same round trip on the Postgres backend  | Returns results                                               | ✅                         |
| SR-10 | `top_k` upper bound                      | Should reject an absurd value                                 | ⚠️ xfail — no bound exists |
| SR-11 | Page is preserved through indexing       | Citations need a page                                         | ⚠️ null via `POST /index`  |
| SR-12 | Retrieval hit rate over 270 questions    | Report doc and page hit rate                                  | 🔒 needs a real embedder   |
| SR-13 | Answers carry citations                  | Every answer cites a document and page                        | 🔒                         |
| SR-14 | Unanswerable questions are refused       | No fabricated answer                                          | 🔒                         |

**SR-12 depends on the embedding backend.** `EMBEDDING_BACKEND=mock` is
a hash chain with no semantic signal, so any hit rate measured under it
describes nothing. Numbers are not reportable until `oci` or `local_st`
is wired.

## 8. Health and resilience

| ID    | Case                                          | Expected                                           | Status |
| ----- | --------------------------------------------- | -------------------------------------------------- | ------ |
| HL-01 | `/liveness` without auth                      | 200                                                | ✅     |
| HL-02 | `/readiness` without auth                     | 200                                                | ✅     |
| HL-03 | Readiness with Postgres down                  | 503, names the failed dependency                   | 📋     |
| HL-04 | Readiness with Redis down                     | 503, names the failed dependency                   | 📋     |
| HL-05 | Liveness stays 200 while a dependency is down | Liveness is not readiness                          | 📋     |
| HL-06 | Pod deleted under load                        | Replaced, traffic restored, recovery time recorded | 🔒     |
| HL-07 | Bad deployment                                | Readiness fails, traffic not routed to it          | 🔒     |
| HL-08 | Rollback                                      | Previous version restored                          | 🔒     |

HL-03 and HL-05 are the reason both probes exist. If liveness also fails
when a dependency is down, Kubernetes restarts a healthy container
instead of routing around it.

## 9. Auth

| ID    | Case                                           | Expected                                        | Status                     |
| ----- | ---------------------------------------------- | ----------------------------------------------- | -------------------------- |
| AU-01 | Register a new user                            | 200, email echoed normalised                    | ✅                         |
| AU-02 | Register with a duplicate email                | 409, `field` is `email`                         | ✅                         |
| AU-03 | Register with a malformed email                | 422, `field` is `email`                         | ✅                         |
| AU-04 | Register with a password under 8 characters    | 422, `field` is `password`                      | ✅                         |
| AU-05 | Register with an org name under 2 characters   | 422, `field` is `org`                           | ✅                         |
| AU-06 | Email case is normalised                       | `Alice@X.COM` and `alice@x.com` are one account | ✅                         |
| AU-07 | Validation errors name the offending field     | `ok`, `field`, `title`, `detail` present        | ✅                         |
| AU-08 | Login with valid credentials                   | 200 with a token                                | ✅                         |
| AU-09 | Login returns session details                  | email, name, derived initials                   | ✅                         |
| AU-10 | Login with a wrong password                    | 401                                             | ✅                         |
| AU-11 | Login with an unknown email                    | 401                                             | ✅                         |
| AU-12 | Failed login does not reveal account existence | Identical status and message either way         | ✅                         |
| AU-13 | Login response never contains the password     | Absent from the body                            | ✅                         |
| AU-14 | Token is a well-formed JWT                     | Three segments                                  | ✅                         |
| AU-15 | Token subject is the user                      | `sub` matches the email                         | ✅                         |
| AU-16 | Token carries a role                           | `role` present                                  | ✅                         |
| AU-17 | Token expires                                  | `exp` present and in the future                 | ✅                         |
| AU-18 | Token lifetime is bounded                      | ≤ 24h                                           | ✅                         |
| AU-19 | Token carries no credential material           | No password or hash in claims                   | ✅                         |
| AU-20 | Concurrent sessions                            | A second login does not invalidate the first    | ✅                         |
| AU-21 | `X-Request-ID` is echoed                       | Caller's id survives the hop                    | ✅                         |
| AU-22 | `X-Request-ID` is generated when absent        | Always present on the response                  | ✅                         |
| AU-23 | Health probes need no token                    | 200                                             | ✅                         |
| AU-24 | A protected route without a token              | 401                                             | 🔒 no protected routes yet |
| AU-25 | A protected route with a malformed token       | 401                                             | 🔒                         |
| AU-26 | A protected route with an expired token        | 401                                             | 🔒                         |
| AU-27 | A protected route with a valid token           | 200                                             | 🔒                         |

AU-12 matters more than it looks: if a wrong password and an unknown
account return different responses, login becomes an account
enumerator. Both currently return an identical 401.

AU-24 through AU-27 are blocked on the gateway proxying to the
downstream services. It authenticates today but does not yet route, so
there is nothing behind it to protect. `search-service` has JWT
middleware that has still never run against a real token — every test
sets `DISABLE_AUTH=true`.

## 10. End-to-end

| ID     | Case                                          | Expected                                                 | Status |
| ------ | --------------------------------------------- | -------------------------------------------------------- | ------ |
| E2E-01 | Upload → process → index → ask → cited answer | Completes; citation resolves to a real page              | 🔒     |
| E2E-02 | Failure mid-pipeline                          | Document reaches FAILED with a usable message, not stuck | 🔒     |
| E2E-03 | Ten concurrent uploads                        | All complete, no lost jobs                               | 🔒     |
| E2E-04 | Frontend journey                              | Login → upload → detail → question → citation renders    | 🔒     |

E2E-01 is the demo. Nothing consumes the job queue today, so an upload
sits at UPLOADED indefinitely — this is the single blocker for the whole
section.

## 11. Performance

| ID    | Case                     | Expected                                           | Status                   |
| ----- | ------------------------ | -------------------------------------------------- | ------------------------ |
| PF-01 | Smoke against the target | All checks pass before any load run                | ✅                       |
| PF-02 | Monolith baseline (M0)   | RPS, P50/P95/P99, error rate, CPU, memory recorded | 🔒 no monolith, no owner |
| PF-03 | OKE baseline             | Same script, same corpus, same generator           | 🔒                       |
| PF-04 | Stress to failure        | Ceiling identified, first failure mode named       | 🔒                       |
| PF-05 | Spike                    | HPA scales up, scale-up time recorded              | 🔒                       |
| PF-06 | Load drop                | Replicas scale back down                           | 🔒                       |
| PF-07 | Soak, 60 minutes         | p95 at the end comparable to the start             | 🔒                       |
| PF-08 | Comparison report        | Table populated from measured runs only            | 🔒                       |

**PF-02 is the deliverable at risk.** The baseline cannot be captured
after decomposition begins. Scripts, corpus and metrics collector are
ready; the monolith is not, and has no owner.

---

## Known findings

Behaviours confirmed and raised, documented here so they are not
rediscovered:

| Finding                                                                | Where                             | State                                                                                      |
| ---------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------ |
| `ivfflat` with `lists=100` returned empty result sets on small corpora | `database/schema.sql`             | Fixed — index removed, SR-09 passes                                                        |
| `top_k` has no upper bound                                             | `search-service`                  | Open, SR-10 xfail                                                                          |
| `page` is null for content indexed via `POST /index`                   | `search-service`                  | Open, SR-11                                                                                |
| `sentence-transformers` pulls PyTorch and CUDA into the image          | `search-service/requirements.txt` | Open — unused under `EMBEDDING_BACKEND=mock`, and the likely cause of CI disk exhaustion   |
| The gateway's user store is in-memory                                  | `api-gateway/app/auth/store.py`   | Open — M1 scope. Registrations do not survive a restart and are not shared across replicas |
| Default `STORAGE_DIR` is relative                                      | `document-service`                | Open — running locally writes uploaded PDFs into the source tree                           |
