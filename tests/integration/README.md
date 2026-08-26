# Integration tests

Contract tests that run against a live service over HTTP. They assert the
shape of the API — status codes, response fields, types, boundaries — not
the quality of results. Retrieval quality cannot be measured while
`EMBEDDING_BACKEND=mock`, because the mock embedder is a hash chain with
no semantic signal.

## Running

Start a search-service instance:

```bash
cd services/search-service
DISABLE_AUTH=true VECTOR_STORE_BACKEND=memory \
    uvicorn src.main:app --port 8090
```

Then:

```bash
pytest tests/integration/search_service -v
```

The suite skips itself if no service is reachable, so it is safe to run
anywhere. Point it at a different instance — a compose stack, or the OKE
deployment — with an environment variable, no code change:

```bash
SEARCH_SERVICE_URL=https://search.dev.example pytest tests/integration
```

## Test isolation

The in-memory vector store persists across runs and is written relative
to the service's working directory, so tests cannot assume an empty
store. Each test indexes under a uuid-namespaced document id instead of
trying to clear shared state.

## Findings

Two behaviours are documented by the suite rather than asserted as
correct:

**`top_k` is unbounded** — `test_search_rejects_unbounded_top_k` is
marked `xfail`. `top_k=999999` is accepted and the service ranks the
entire store. Harmless against a small corpus; a denial-of-service
vector at scale. The test starts passing when a bound is added.

**`page` is null for content indexed via `POST /index`** — the endpoint
takes raw text with no page structure, so no page can be assigned.
Documents indexed by `index_sample_documents.py` do carry page numbers,
because it parses `[PAGE n]` markers first. Citations are a core feature,
so whatever feeds the real pipeline must preserve page information.
Raised with the search/data owner.
