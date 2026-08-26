// The user journey, shared by every scenario.
//
// Scenarios differ only in load profile — how many users, ramping how
// fast, for how long. What those users *do* is defined once, here, so
// the monolith and OKE runs exercise identical work.

import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Trend, Rate } from "k6/metrics";

import {
  BASE_URL,
  HAS_GATEWAY,
  HAS_UPLOAD,
  HAS_SEARCH,
  headers,
  randomQuestion,
} from "./config.js";

// Custom metrics, so a slow stage can be attributed to a specific step
// rather than disappearing into an overall p95.
export const searchDuration = new Trend("step_search_duration", true);
export const uploadDuration = new Trend("step_upload_duration", true);
export const processingDuration = new Trend("step_processing_duration", true);
export const processingTimeouts = new Counter("processing_timeouts");
export const skippedSteps = new Counter("skipped_steps");
export const journeyComplete = new Rate("journey_complete");

const POLL_INTERVAL = 1;
const POLL_TIMEOUT = 120;

export function healthCheck() {
  const res = http.get(`${BASE_URL}/liveness`, { tags: { step: "health" } });
  check(res, { "liveness 200": (r) => r.status === 200 });
  return res.status === 200;
}

export function search() {
  if (!HAS_SEARCH) {
    skippedSteps.add(1, { step: "search" });
    return true;
  }

  const question = randomQuestion();
  const url = `${BASE_URL}/search?question=${encodeURIComponent(question)}&top_k=5`;

  const res = http.get(url, { headers: headers(), tags: { step: "search" } });
  searchDuration.add(res.timings.duration);

  return check(res, {
    "search 200": (r) => r.status === 200,
    "search returns results array": (r) => {
      try {
        return Array.isArray(r.json("results"));
      } catch (e) {
        return false;
      }
    },
  });
}

export function upload(pdfFile, filename) {
  if (!HAS_UPLOAD) {
    skippedSteps.add(1, { step: "upload" });
    return null;
  }

  const res = http.post(
    `${BASE_URL}/documents`,
    { file: http.file(pdfFile, filename, "application/pdf") },
    {
      headers: headers({ "Content-Type": undefined }),
      tags: { step: "upload" },
    },
  );
  uploadDuration.add(res.timings.duration);

  const ok = check(res, {
    "upload 202": (r) => r.status === 202,
    "upload returns id": (r) => {
      try {
        return typeof r.json("id") === "string";
      } catch (e) {
        return false;
      }
    },
  });

  return ok ? res.json("id") : null;
}

// Polls until the document reaches a terminal state.
//
// Processing is async by design — the API returns 202 immediately, so
// end-to-end latency is not visible in http_req_duration and has to be
// measured separately.
export function waitForProcessing(documentId) {
  if (!documentId) {
    return false;
  }

  const started = Date.now();
  let elapsed = 0;

  while (elapsed < POLL_TIMEOUT) {
    const res = http.get(`${BASE_URL}/documents/${documentId}/status`, {
      headers: headers(),
      tags: { step: "status" },
    });

    if (res.status === 200) {
      const status = String(res.json("status") || "").toLowerCase();
      if (status === "completed") {
        processingDuration.add(Date.now() - started);
        return true;
      }
      if (status === "FAILED") {
        processingDuration.add(Date.now() - started);
        return false;
      }
    }

    sleep(POLL_INTERVAL);
    elapsed = (Date.now() - started) / 1000;
  }

  processingTimeouts.add(1);
  return false;
}

export function askQuestion(documentId) {
  if (!HAS_GATEWAY || !documentId) {
    skippedSteps.add(1, { step: "ask" });
    return true;
  }

  const res = http.post(
    `${BASE_URL}/documents/${documentId}/ask`,
    JSON.stringify({ question: randomQuestion() }),
    { headers: headers(), tags: { step: "ask" } },
  );

  return check(res, {
    "ask 200": (r) => r.status === 200,
    "ask returns citations": (r) => {
      try {
        return Array.isArray(r.json("citations"));
      } catch (e) {
        return false;
      }
    },
  });
}

// The read-heavy journey — what most load is, in practice.
export function readJourney() {
  const ok = search();
  journeyComplete.add(ok);
  sleep(Math.random() * 2 + 0.5);
}

// The full write journey. Runs only when upload is available.
export function writeJourney(pdfFile, filename) {
  const documentId = upload(pdfFile, filename);
  if (!documentId) {
    journeyComplete.add(false);
    sleep(1);
    return;
  }

  const processed = waitForProcessing(documentId);
  const answered = processed ? askQuestion(documentId) : false;

  journeyComplete.add(processed && answered);
  sleep(Math.random() * 2 + 1);
}
