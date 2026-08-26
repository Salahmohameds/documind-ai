# Smoke tests

Post-deploy checks. One question: did this deployment come up correctly?

Not a functional suite. These run against whatever was just deployed —
including production — so they are read-only, and they finish in
seconds. A smoke suite that takes minutes gets skipped by the people
who need it most.

## Running

```bash
API_GATEWAY_URL=https://gateway.dev.example \
DOCUMENT_SERVICE_URL=https://documents.dev.example \
SEARCH_SERVICE_URL=https://search.dev.example \
AI_SERVICE_URL=https://ai.dev.example \
    pytest tests/smoke -v
```

Every service is optional. One with no URL configured is skipped rather
than failed, so the same suite works during a partial rollout.

Locally, use `127.0.0.1` rather than `localhost`. On Windows, resolving
`localhost` adds roughly two seconds per request while IPv6 is tried
first and times out — enough to fail the response-time check against
perfectly healthy services.

## What is checked

Across every configured service: liveness, readiness, that neither
probe requires auth, that a probe answers in under two seconds, and
that an unknown path returns a clean 404 without leaking a stack trace.

Per service, one real code path each: the gateway rejects bad
credentials and sets a request id, document listing is reachable and
readiness names its dependencies, and search answers a query.

The final check asserts that at least one service URL was configured.
Without it, a run with the environment unset passes trivially — the
pipeline reports success having verified nothing, which is worse than
failing.

## Why these checks

`test_health_probes_need_no_auth` — Kubernetes cannot present a token.
If a probe starts requiring auth, the kubelet sees 401, marks the pod
unhealthy, and restarts it forever.

`test_service_responds_quickly` — slow probes cause probe timeouts,
which restart pods that are merely overloaded, turning a load problem
into an outage.

`test_no_stack_traces_on_unknown_paths` — framework debug pages expose
file paths, versions, and sometimes environment variables.

## In CI

Wire into `cd.yml` after the OKE deploy step, with the service URLs
pointing at the deployed environment. A failure should fail the
pipeline and trigger a rollback.
