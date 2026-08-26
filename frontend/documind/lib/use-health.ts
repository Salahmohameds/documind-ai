"use client";

import { useEffect, useState } from "react";
import { getDocumentCounts, getHealth, type DocumentCounts, type ServiceHealth } from "@/lib/api";

/** How often the badge re-checks. Slow enough to be free, fast enough to notice. */
const POLL_MS = 15_000;

export type Health = {
  status: "ready" | "degraded" | "unknown";
  /** Short text for the badge. */
  label: string;
  /** The full reason, for a tooltip. */
  detail: string;
  services: ServiceHealth[];
};

const UNKNOWN: Health = {
  status: "unknown",
  label: "Checking services…",
  detail: "Reading service readiness.",
  services: [],
};

/**
 * Live readiness of the backing services.
 *
 * The upload screen used to derive "pipeline healthy" from whether any local
 * job had failed, which said nothing about whether the services were up. This
 * asks them.
 */
export function useHealth(): Health {
  const [health, setHealth] = useState<Health>(UNKNOWN);

  useEffect(() => {
    const controller = new AbortController();
    let live = true;

    const check = async () => {
      try {
        const report = await getHealth(controller.signal);
        if (!live) return;

        const unhappy = report.services.filter((s) => s.state !== "ready");
        setHealth({
          status: report.status,
          label: unhappy.length === 0 ? "All services ready" : `${unhappy.length} service${unhappy.length === 1 ? "" : "s"} degraded`,
          detail:
            unhappy.length === 0
              // Named rather than counted: which services back the app is
              // exactly what this tooltip exists to answer, and the list grows
              // as services land.
              ? `${report.services.map((s) => s.service).join(", ")} are ready.`
              : unhappy.map((s) => `${s.service}: ${s.detail}`).join(" "),
          services: report.services,
        });
      } catch {
        if (!live) return;
        setHealth({
          status: "unknown",
          label: "Service status unknown",
          detail: "The health check itself could not be reached.",
          services: [],
        });
      }
    };

    void check();
    const t = setInterval(check, POLL_MS);

    return () => {
      live = false;
      controller.abort();
      clearInterval(t);
    };
  }, []);

  return health;
}

const NO_COUNTS: DocumentCounts = {
  total: 0,
  queued: 0,
  processing: 0,
  completed: 0,
  failed: 0,
  inFlight: 0,
};

/**
 * Live library counts for the nav badges.
 *
 * Polled rather than pushed, and deliberately slower than the per-screen
 * pollers: a badge being a few seconds stale costs nothing, and this runs on
 * every page of the app.
 */
export function useDocumentCounts(): DocumentCounts {
  const [counts, setCounts] = useState<DocumentCounts>(NO_COUNTS);

  useEffect(() => {
    const controller = new AbortController();
    let live = true;

    const read = async () => {
      try {
        const next = await getDocumentCounts(controller.signal);
        if (live) setCounts(next);
      } catch {
        // Badges keep their last known value rather than flashing to zero.
      }
    };

    void read();
    const t = setInterval(read, POLL_MS);

    return () => {
      live = false;
      controller.abort();
      clearInterval(t);
    };
  }, []);

  return counts;
}
