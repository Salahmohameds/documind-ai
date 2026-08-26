# Load tests

k6 scenarios for the monolith-vs-OKE performance comparison.

## The rule that matters

The same script, the same corpus, and the same load generator must be
used for both architectures. If any of those differ, the two result sets
are not comparable and the migration story has no evidence behind it.
Everything that varies between targets is an environment variable — no
scenario hardcodes a URL, and no scenario is edited between runs.

## Scenarios

| Script        | Load profile               | Answers                                      |
| ------------- | -------------------------- | -------------------------------------------- |
| `smoke.js`    | 1 VU, 10 iterations        | Is the target up and behaving correctly?     |
| `baseline.js` | Ramp to N, hold, ramp down | How does it perform under expected load?     |
| `stress.js`   | Step up to peak            | Where is the ceiling, and what breaks first? |
| `spike.js`    | Calm → surge → calm        | Does autoscaling react, and how fast?        |
| `soak.js`     | Modest load, 60 minutes    | Does anything leak over time?                |

Always run `smoke.js` first. A failed stress run should mean the system
broke under load, not that the URL was wrong.

`stress.js` has no pass/fail thresholds on purpose. A stress run is
expected to degrade; gating on that would hide the answer it exists to
produce.

## Running

```bash
export BASE_URL=http://localhost:8090
export TARGET=local-search-service

k6 run tests/load/scenarios/smoke.js
k6 run --env VUS=10 --env DURATION=5m tests/load/scenarios/baseline.js
k6 run --env PEAK=100 tests/load/scenarios/stress.js
k6 run --env CALM=5 --env SURGE=80 tests/load/scenarios/spike.js
k6 run --env VUS=10 --env DURATION=60m tests/load/scenarios/soak.js
```

`TARGET` is recorded in the run tags so a results file can never be
mistaken for the other architecture.

## Feature flags

Three services do not exist yet, so the journey checks before it calls:

| Variable      | Default | Enable when                           |
| ------------- | ------- | ------------------------------------- |
| `HAS_SEARCH`  | `true`  | available today                       |
| `HAS_UPLOAD`  | `false` | `document-service` is reachable       |
| `HAS_GATEWAY` | `false` | `api-gateway` exists and mints tokens |

Skipped steps are counted in the `skipped_steps` metric, so a run always
records what it did _not_ exercise. The full journey is written and
waiting — enabling it is a flag change, not a rewrite.

## Cluster metrics

k6 measures the client side only. CPU, memory, pod count and HPA
replicas are required by the comparison table and appear nowhere in k6
output. Sample them separately, in a second terminal, started just
before k6 and stopped just after:

```bash
./collect-metrics.sh baseline-oke documind 5
```

Output is CSV under `results/` (gitignored). Read-only — it needs
get/list on pods and hpa, nothing more. If `metrics-server` is not
installed, CPU and memory columns come back blank rather than failing
the run.

Running `spike.js` without this collector proves nothing about
autoscaling: the scaling event is the result, and it is invisible from
the client side.

## Thresholds

The values in `lib/config.js` are placeholders. Per the test strategy,
OKE thresholds are derived from the measured monolith baseline (M0), not
invented. Until M0 exists, a passing threshold is not evidence of
anything.

## Async processing

Upload returns `202` immediately, so end-to-end processing time does not
appear in `http_req_duration`. It is measured separately as
`step_processing_duration` by polling to a terminal state. Reporting
only `http_req_duration` for a write journey would claim a p95 of
milliseconds for work that takes tens of seconds.
