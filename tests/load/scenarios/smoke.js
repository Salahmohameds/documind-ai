// Smoke test — the cheapest possible sanity check.
//
// One user, a handful of iterations. This is not a load test: it answers
// "is the target up and behaving correctly at all?" so that a failed
// stress run means the system broke under load, not that the URL was
// wrong. Always run this first.

import { THRESHOLDS, TARGET, BASE_URL } from "../lib/config.js";
import { healthCheck, readJourney } from "../lib/journey.js";

export const options = {
  vus: 1,
  iterations: 10,
  thresholds: {
    ...THRESHOLDS,
    // A smoke run must be clean — no tolerance for failures here.
    http_req_failed: ["rate==0"],
    checks: ["rate==1"],
  },
  tags: { target: TARGET, scenario: "smoke" },
};

export function setup() {
  console.log(`smoke: target=${TARGET} base_url=${BASE_URL}`);
  if (!healthCheck()) {
    throw new Error(`target not reachable at ${BASE_URL}`);
  }
}

export default function () {
  readJourney();
}
