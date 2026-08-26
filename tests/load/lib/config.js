// Shared configuration for every load scenario.
//
// The same script must run unchanged against both the monolith and the
// OKE deployment, or the comparison is not a comparison. Everything that
// differs between the two lives here, driven by environment variables —
// never hardcoded in a scenario.

export const BASE_URL = (__ENV.BASE_URL || "http://localhost:8090").replace(
  /\/$/,
  "",
);

// Which architecture is under test. Recorded in the summary so a results
// file can never be mistaken for the other one.
export const TARGET = __ENV.TARGET || "unknown";

// Some endpoints do not exist yet (api-gateway, processing-service).
// Scenarios check these flags and skip the corresponding steps, so the
// full script can be written now and run partially today.
export const HAS_GATEWAY = __ENV.HAS_GATEWAY === "true";
export const HAS_UPLOAD = __ENV.HAS_UPLOAD === "true";
export const HAS_SEARCH = __ENV.HAS_SEARCH !== "false"; // available today

export const TOKEN = __ENV.TOKEN || "";

export function headers(extra) {
  const h = { "Content-Type": "application/json" };
  if (TOKEN) {
    h["Authorization"] = `Bearer ${TOKEN}`;
  }
  return Object.assign(h, extra || {});
}

// Thresholds.
//
// These are placeholders until the monolith baseline (M0) is measured.
// Per the test strategy, OKE thresholds get derived from measured
// baseline numbers rather than invented ones — so do not treat a pass
// against these as meaningful until M0 exists.
export const THRESHOLDS = {
  http_req_failed: ["rate<0.01"],
  http_req_duration: ["p(95)<800", "p(99)<2000"],
  checks: ["rate>0.99"],
};

// A question pool drawn from the generated corpus. Varying the query
// prevents any cache from making retrieval look faster than it is.
export const QUESTIONS = [
  "What are the payment terms?",
  "Who are the parties to this agreement?",
  "Does this contract renew automatically?",
  "How much notice is required to terminate for cause?",
  "What is the cap on liability?",
  "What is the total amount due?",
  "Who is the vendor?",
  "What is the invoice number?",
  "When is the invoice due?",
  "What tax was applied?",
  "How long does confidentiality last after termination?",
  "What law governs the agreement?",
];

export function randomQuestion() {
  return QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
}
