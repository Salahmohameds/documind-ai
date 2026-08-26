/**
 * Aggregated readiness of the services the UI depends on.
 *
 * This is what the "pipeline healthy / degraded" indicator reads. It probes
 * `/readiness` (not `/liveness`) because the question the badge answers is
 * "can my upload actually be processed?", and readiness is the probe that
 * checks Postgres, Redis and the model provider.
 *
 * A degraded dependency is a 200 here with `status: "degraded"`, not a 5xx:
 * the health report itself succeeded, and the UI needs the detail to render.
 */

import { AI_SERVICE_URL, DOCUMENT_SERVICE_URL, SEARCH_SERVICE_URL } from "@/lib/server/backend";

/**
 * Generous on purpose. A readiness probe is slowest exactly when something is
 * wrong — document-service takes ~4s to answer when Redis is down, because the
 * Redis connect has to time out first. Cutting it off at that point would
 * report the service as unreachable and throw away the one thing the report
 * exists to say: which dependency is broken.
 */
const PROBE_TIMEOUT_MS = 8000;

export type ServiceHealth = {
  service: string;
  /** "ready" — serving. "degraded" — up but a dependency is down. "unreachable" — no answer. */
  state: "ready" | "degraded" | "unreachable";
  detail: string;
  /** Per-dependency results, when the service reports them. */
  checks?: Record<string, string>;
};

export type HealthReport = {
  status: "ready" | "degraded";
  services: ServiceHealth[];
  checkedAt: string;
};

/**
 * Which keys in a service's `checks` map are dependency states, and what each
 * one looks like when healthy.
 *
 * This has to be explicit because ai-service reports descriptive metadata in
 * the same map — `backend`, `model`, `embedding_dim` — and a naive "anything
 * that isn't `ok` is broken" rule would read its model name as an outage.
 * Keys absent from this list are metadata and are never read as a failure.
 */
type Probe = { service: string; base: string; dependencies: Record<string, readonly string[]> };

const PROBES: readonly Probe[] = [
  {
    service: "document-service",
    base: DOCUMENT_SERVICE_URL,
    dependencies: { postgres: ["ok"], redis: ["ok"] },
  },
  {
    // Reports no per-dependency checks; its status code is the whole answer.
    service: "search-service",
    base: SEARCH_SERVICE_URL,
    dependencies: {},
  },
  {
    service: "ai-service",
    base: AI_SERVICE_URL,
    // A half-open breaker is a service that is trying again, not one that is
    // down — it serves the next request, so it does not belong in the badge.
    dependencies: { provider: ["ok"], circuit_breaker: ["closed", "half_open"] },
  },
];

export async function GET() {
  const services = await Promise.all(PROBES.map(probe));

  const report: HealthReport = {
    status: services.every((s) => s.state === "ready") ? "ready" : "degraded",
    services,
    checkedAt: new Date().toISOString(),
  };
  return Response.json(report);
}

async function probe({ service, base, dependencies }: Probe): Promise<ServiceHealth> {
  try {
    const response = await fetch(`${base}/readiness`, {
      cache: "no-store",
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
    });

    const body = (await response.json().catch(() => ({}))) as {
      status?: string;
      checks?: Record<string, unknown>;
      error?: string;
    };

    // ai-service mixes numbers into `checks`; the UI contract is strings.
    const checks = body.checks
      ? Object.fromEntries(Object.entries(body.checks).map(([k, v]) => [k, String(v)]))
      : undefined;

    if (response.ok) {
      return { service, state: "ready", detail: "Serving traffic.", checks };
    }

    const down = Object.entries(dependencies)
      .filter(([key, healthy]) => checks?.[key] !== undefined && !healthy.includes(checks[key]))
      .map(([key]) => key);

    return {
      service,
      state: "degraded",
      detail: down.length
        ? `Running, but ${down.join(" and ")} ${down.length === 1 ? "is" : "are"} unavailable.`
        : (body.error ?? `Reported ${response.status} on readiness.`),
      checks,
    };
  } catch {
    return {
      service,
      state: "unreachable",
      detail: `No response from ${base}. Check that the service is running.`,
    };
  }
}
