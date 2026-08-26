// Baseline — sustained normal load.
//
// This is the run that produces the headline comparison numbers. It must
// be executed identically against the monolith (M0) and OKE, from the
// same load generator, with the same corpus, or the two results are not
// comparable and the migration story has no evidence behind it.
//
// Three runs, report the median. A single run of anything is an anecdote.

import { THRESHOLDS, TARGET, BASE_URL } from "../lib/config.js";
import { healthCheck, readJourney } from "../lib/journey.js";

const VUS = parseInt(__ENV.VUS || "10", 10);
const DURATION = __ENV.DURATION || "5m";

export const options = {
  stages: [
    { duration: "30s", target: VUS }, // ramp in, do not shock the target
    { duration: DURATION, target: VUS }, // the measured window
    { duration: "30s", target: 0 }, // ramp out
  ],
  thresholds: THRESHOLDS,
  tags: { target: TARGET, scenario: "baseline" },
};

export function setup() {
  console.log(
    `baseline: target=${TARGET} vus=${VUS} duration=${DURATION} url=${BASE_URL}`,
  );
  if (!healthCheck()) {
    throw new Error(`target not reachable at ${BASE_URL}`);
  }
  return { startedAt: new Date().toISOString() };
}

export default function () {
  readJourney();
}

export function teardown(data) {
  console.log(`baseline complete: target=${TARGET} started=${data.startedAt}`);
}
