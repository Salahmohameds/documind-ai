// Stress — ramp until something breaks.
//
// Baseline answers "how does it behave under expected load". Stress
// answers "where is the ceiling, and what fails first when we hit it".
// Thresholds are deliberately absent: a stress run is expected to
// degrade, and failing the run on that would hide the answer.

import { TARGET, BASE_URL } from "../lib/config.js";
import { healthCheck, readJourney } from "../lib/journey.js";

const PEAK = parseInt(__ENV.PEAK || "100", 10);

export const options = {
  stages: [
    { duration: "1m", target: Math.round(PEAK * 0.25) },
    { duration: "2m", target: Math.round(PEAK * 0.5) },
    { duration: "2m", target: Math.round(PEAK * 0.75) },
    { duration: "2m", target: PEAK },
    { duration: "1m", target: 0 },
  ],
  // No pass/fail thresholds — this run is diagnostic. Record where
  // latency turns and where errors begin, do not gate on it.
  tags: { target: TARGET, scenario: "stress" },
};

export function setup() {
  console.log(`stress: target=${TARGET} peak=${PEAK} url=${BASE_URL}`);
  if (!healthCheck()) {
    throw new Error(`target not reachable at ${BASE_URL}`);
  }
}

export default function () {
  readJourney();
}
