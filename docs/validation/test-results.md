Verified independently in the database: `processing_jobs` shows
`COMPLETED`, `document_chunks` holds the chunks, `risk_assessments` and
`extracted_fields` are populated.

## Corpus accuracy

All 50 generated documents uploaded through the full pipeline and
compared to the ground truth they were built from.

| Metric                   | Result       |
| ------------------------ | ------------ |
| Reached a terminal state | 50/50        |
| Completed successfully   | 50/50 — 100% |
| Classified correctly     | 50/50 — 100% |
| Indexed and retrievable  | 50/50 — 100% |

**These numbers measure the rule set, not a model.** The mock backend is
rules-based and deterministic rather than random, which makes the
figures real and repeatable — but they are not a claim about OCI
Generative AI. Re-run against a real provider before quoting.

The corpus is reproducible from seed 42, so any change in a measured
figure is caused by a code change, never by the data.

## Open findings

| #   | Finding                                                                                    | Where                | Impact                                                                          |
| --- | ------------------------------------------------------------------------------------------ | -------------------- | ------------------------------------------------------------------------------- |
| 1   | A 14-digit national ID is classified `CREDIT_CARD`; `NATIONAL_ID` is not a recognised type | `ai-service`         | A required PII type per the spec is not detected, and is mislabelled as another |
| 2   | Risk is computed and stored but the status endpoint returns `risk: null`                   | `document-service`   | The frontend reads this endpoint, so a completed document displays as pending   |
| 3   | A completed document can revert to FAILED on a spurious reprocess                          | `processing-service` | A user who watched a document finish can later see it failed                    |
| 4   | `top_k` has no upper bound                                                                 | `search-service`     | A large value ranks the entire store — a denial-of-service vector at scale      |
| 5   | `page` is null for content indexed via `POST /index`                                       | `search-service`     | Citations are a core feature and need a page                                    |
| 6   | `sentence-transformers` pulls PyTorch and CUDA into the image                              | `search-service`     | Unused under `mock`; the likely cause of CI disk exhaustion                     |

Each has a test marked `xfail` that starts passing when the fix lands.

## Fixed findings

| #   | Finding                                                                      | Impact if it had shipped                                                                  |
| --- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 1   | `ivfflat` index with `lists=100` returned empty result sets on small corpora | RAG would have returned nothing on OKE, with a 200 and an empty array — no error anywhere |
| 2   | Upload response field is `id`, not `document_id`                             | Every load-test upload recorded as failed against a service that accepted it              |
| 3   | Status values are lowercase; the load journey compared uppercase             | Every document polling to a full 120-second timeout and logging a false timeout           |

Finding 1 is the most consequential caught so far. The in-memory backend
does an exact scan, so local testing never surfaced it — and Postgres is
what ships. Confirmed with an identical query embedding: default probes
returned zero rows, `probes=100` returned the row.

Findings 2 and 3 were both surfaced by writing contract tests against
the live services, and both would have corrupted the first write-journey
load run.

## Environmental notes

Recorded so they are not rediagnosed as service defects:

- `processing_jobs` is missing from any database created before the
  table was added. Init scripts run once per volume;
  `docker compose down -v` rebuilds.
- `app_instrumentation` imports its own submodules absolutely, so any
  service importing it needs a manual `PYTHONPATH` locally.
- OpenTelemetry package versions conflict across services in a shared
  venv. Invisible in Docker, breaks a shared local environment.
- On Windows, resolving `localhost` adds roughly two seconds per request
  while IPv6 is tried first. Use `127.0.0.1` locally.

## Not measured

| Area                                                                    | Blocked on                                                |
| ----------------------------------------------------------------------- | --------------------------------------------------------- |
| Retrieval hit rate, answer citations, refusal of unanswerable questions | A real embedding backend                                  |
| Per-field extraction accuracy, PII recall and precision                 | Worth measuring against a real provider, not the rule set |
| Pod deletion, autoscaling, rollback                                     | A cluster                                                 |
| Monolith baseline and the OKE comparison                                | The monolith — see below                                  |

## The blocked deliverable

The monolith-vs-OKE performance comparison cannot proceed. The k6
scenarios, the 50-document corpus and the cluster metrics collector are
all ready and tested. The monolith is not built and has no owner.

This baseline is a one-shot window: it cannot be captured after
decomposition begins. If it is missed, the comparison table in
`docs/performance/monolith-vs-oke.md` stays empty, and the migration
story rests on assertion rather than measurement — which the project
proposal explicitly rules out.

## Reproducing

```bash
docker compose up -d postgres redis
# start document-service :8081, ai-service :8083,
# search-service :8090, processing-service :8084, api-gateway :8000

pytest                                    # default suites
pytest -m disruptive                      # container failure tests
pytest -m accuracy -s                     # corpus accuracy, prints figures
pytest tests/smoke -v                     # against any environment
```

Generate the corpus first, or accuracy tests skip:

```bash
cd tests/fixtures/generator
python generate.py --contracts 20 --invoices 30 --seed 42
python verify.py
python edge_cases.py
```
