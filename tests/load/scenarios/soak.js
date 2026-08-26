// Soak — modest load held for a long time.
//
// Catches what short runs cannot: memory leaks, connection pool
// exhaustion, unbounded queues, disk filling with logs. The signal is
// not the average but the trend — if p95 at minute 55 is materially
// worse than at minute 5 under identical load, something is leaking.

import { THRESHOLDS, TARGET, BASE_URL } from '../lib/config.js';
import { healthCheck, readJourney } from '../lib/journey.js';

const VUS = parseInt(__ENV.VUS || '10', 10);
const DURATION = __ENV.DURATION || '60m';

export const options = {
  stages: [
    { duration: '2m', target: VUS },
    { duration: DURATION, target: VUS },
    { duration: '2m', target: 0 },
  ],
  thresholds: THRESHOLDS,
  tags: { target: TARGET, scenario: 'soak' },
};

export function setup() {
  console.log(`soak: target=${TARGET} vus=${VUS} duration=${DURATION} url=${BASE_URL}`);
  if (!healthCheck()) {
    throw new Error(`target not reachable at ${BASE_URL}`);
  }
}

export default function () {
  readJourney();
}