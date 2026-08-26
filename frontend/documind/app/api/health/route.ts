/**
 * Aggregated readiness of the services the UI depends on.
 *
 * This is what the "pipeline healthy / degraded" indicator reads. It probes
 * `/readiness` (not `/liveness`) because the question the badge answers is
 * "can my upload actually be processed?", and readiness is the probe that
 * checks Postgres and Redis.
 *
 * A degraded dependency is a 200 here with `status: "degraded"`, not a 5xx:
 * the health report itself succeeded, and the UI needs the detail to render.
 */

import { DOCUMENT_SERVICE_URL, SEARCH_SERVICE_URL } from "@/lib/server/backend";

const PROBE_TIMEOUT_MS = 4000;

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

export async function GET() {
  const services = await Promise.all([
    probe("document-service", DOCUMENT_SERVICE_URL),
    probe("search-service", SEARCH_SERVICE_URL),
  ]);

  const report: HealthReport = {
    status: services.every((s) => s.state === "ready") ? "ready" : "degraded",
    services,
    checkedAt: new Date().toISOString(),
  };
  return Response.json(report);
}

async function probe(service: string, base: string): Promise<ServiceHealth> {
  try {
    const response = await fetch(`${base}/readiness`, {
      cache: "no-store",
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
    });

    const body = (await response.json().catch(() => ({}))) as {
      status?: string;
      checks?: Record<string, string>;
      error?: string;
    };

    if (response.ok) {
      return { service, state: "ready", detail: "Serving traffic.", checks: body.checks };
    }

    const down = Object.entries(body.checks ?? {})
      .filter(([, v]) => v !== "ok")
      .map(([k]) => k);

    return {
      service,
      state: "degraded",
      detail: down.length
        ? `Running, but ${down.join(" and ")} ${down.length === 1 ? "is" : "are"} unavailable.`
        : (body.error ?? `Reported ${response.status} on readiness.`),
      checks: body.checks,
    };
  } catch {
    return {
      service,
      state: "unreachable",
      detail: `No response from ${base}. Check that the service is running.`,
    };
  }
}
