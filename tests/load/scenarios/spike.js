// Spike — a sudden surge, then a sudden drop.
//
// This is the HPA demonstration. The interesting numbers are not
// throughput but timing: how long from the surge until new pods are
// ready, how many requests fail in that gap, and how long after the drop
// until replicas scale back down.
//
// Run collect-metrics.sh alongside this, or the scaling behaviour goes
// unrecorded and the run proves nothing.

import { TARGET, BASE_URL } from "../lib/config.js";
import { healthCheck, readJourney } from "../lib/journey.js";

const CALM = parseInt(__ENV.CALM || "5", 10);
const SURGE = parseInt(__ENV.SURGE || "80", 10);

export const options = {
  stages: [
    { duration: "1m", target: CALM }, // establish a calm floor
    { duration: "10s", target: SURGE }, // the spike — deliberately abrupt
    { duration: "3m", target: SURGE }, // hold: HPA should react in here
    { duration: "10s", target: CALM }, // drop
    { duration: "3m", target: CALM }, // hold: watch replicas come down
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    // A spike is allowed to hurt, but not to break outright. If more
    // than 5% fails, autoscaling did not save us.
    http_req_failed: ["rate<0.05"],
  },
  tags: { target: TARGET, scenario: "spike" },
};

export function setup() {
  console.log(
    `spike: target=${TARGET} calm=${CALM} surge=${SURGE} url=${BASE_URL}`,
  );
  if (!healthCheck()) {
    throw new Error(`target not reachable at ${BASE_URL}`);
  }
}

export default function () {
  readJourney();
}
