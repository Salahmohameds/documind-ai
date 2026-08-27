# Monolith vs OKE — performance comparison

**Status: awaiting the monolith baseline. No figures yet.**

This document is the deliverable the migration story rests on. The
project proposal is explicit: _"We will not assume microservices are
faster. We will measure."_ Everything needed to measure is ready except
the monolith.

## What is ready

| Asset                     | Where                           | State                                   |
| ------------------------- | ------------------------------- | --------------------------------------- |
| Load scenarios            | `tests/load/scenarios/`         | Five profiles, tested                   |
| Shared journey            | `tests/load/lib/journey.js`     | Contract-verified against live services |
| Corpus                    | `tests/fixtures/generator/`     | 50 documents, reproducible from seed 42 |
| Cluster metrics collector | `tests/load/collect-metrics.sh` | Samples pods, HPA, CPU, memory          |
| Smoke suite               | `tests/smoke/`                  | Run before any measured load run        |

## What is missing

The containerised monolith described in Phase 2 of the project proposal.
It has no owner and no date.

**This is a one-shot window.** The baseline cannot be captured after
decomposition begins — there will be nothing left to measure. If it is
missed, the Monolith column below stays empty permanently.

## Protocol

Both architectures must be measured under conditions that differ in
exactly one variable: the architecture.

| Controlled variable    | Value                                              |
| ---------------------- | -------------------------------------------------- |
| Load script            | Identical file, no edits between runs              |
| Corpus                 | The same 50 documents, seed 42                     |
| Load generator         | The same machine for both runs                     |
| Request mix            | Frozen with the API contract                       |
| AI backend             | The same setting for both — ideally `AI_MODE=stub` |
| Runs per configuration | 3, report the median                               |

A single run of anything is an anecdote.

**On the AI backend.** Without a stub, both runs measure Oracle's
endpoint latency rather than the architecture, and every stress and soak
run burns provider budget. The flag does not exist yet; the scenarios
are written to work either way.

**On the load generator.** Generating load from a GitHub runner rather
than an in-region VM adds network latency to both sides. That is
acceptable — what invalidates the comparison is generating the two runs
from different places. Whichever is used, use it for both, and record
which in the results.

## Comparison table

To be populated from measured runs only. No estimated or projected
values belong here.

| Metric                             | Monolith | OKE | Delta |
| ---------------------------------- | -------- | --- | ----- |
| Requests/sec                       | —        | —   | —     |
| P50 latency                        | —        | —   | —     |
| P95 latency                        | —        | —   | —     |
| P99 latency                        | —        | —   | —     |
| Error rate                         | —        | —   | —     |
| CPU (peak)                         | —        | —   | —     |
| Memory (peak)                      | —        | —   | —     |
| Pod / instance count               | —        | —   | —     |
| Recovery time after instance loss  | —        | —   | —     |
| Time to scale up under spike       | n/a      | —   | —     |
| Time to scale down after load drop | n/a      | —   | —     |

Rows marked `n/a` for the monolith are the point of the exercise: a
single instance has no autoscaling behaviour to measure. The comparison
is not only about which is faster.

## Scenarios

| Scenario      | Profile                    | Answers                                            |
| ------------- | -------------------------- | -------------------------------------------------- |
| `smoke.js`    | 1 VU, 10 iterations        | Is the target up and correct before we measure it? |
| `baseline.js` | Ramp to N, hold, ramp down | How does it perform under expected load?           |
| `stress.js`   | Step up to peak            | Where is the ceiling, and what fails first?        |
| `spike.js`    | Calm → surge → calm        | Does autoscaling react, and how fast?              |
| `soak.js`     | Modest load, 60 minutes    | Does anything leak over time?                      |

`stress.js` has no pass/fail thresholds deliberately. A stress run is
expected to degrade; gating on that would hide the answer it exists to
produce.

## Thresholds

The values in `tests/load/lib/config.js` are placeholders. Per the test
strategy, OKE thresholds are derived from the measured monolith baseline
rather than invented — so a passing threshold today is not evidence of
anything.

Once M0 exists, replace them with values anchored to it.

## Cluster metrics

k6 measures the client side only. CPU, memory, pod count and HPA
replicas appear nowhere in its output and must be sampled from the
cluster during the run:

```bash
./tests/load/collect-metrics.sh baseline-oke documind 5
```

Read-only — it needs get/list on pods and hpa, nothing more. Output is
CSV, suitable for plotting the autoscaling event.

**Running `spike.js` without this collector proves nothing about
autoscaling.** The scaling event is the result, and it is invisible from
the client side.

## Running a measured comparison

Once the monolith exists:

```bash
# 1. Verify the target before measuring it
BASE_URL=<monolith> TARGET=monolith k6 run tests/load/scenarios/smoke.js

# 2. Baseline, three times
BASE_URL=<monolith> TARGET=monolith \
  k6 run --env VUS=10 --env DURATION=5m tests/load/scenarios/baseline.js

# 3. Repeat against OKE with the collector running alongside
./tests/load/collect-metrics.sh baseline-oke documind 5 &
BASE_URL=<oke> TARGET=oke \
  k6 run --env VUS=10 --env DURATION=5m tests/load/scenarios/baseline.js
```

`TARGET` is recorded in the run tags, so a results file can never be
mistaken for the other architecture.

## Interpreting the result

The conclusion must follow from the data, whichever way it points.

Microservices may well be slower per request — an extra network hop
between gateway and service costs latency that a monolith does not pay.
If that is what the numbers show, that is what the report says. The
argument for the migration is not raw speed; it is independent scaling,
isolated failure, and the ability to add capacity where the bottleneck
actually is.

A report that finds microservices faster on every axis should be treated
as suspicious before it is treated as a success.
