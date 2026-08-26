/**
 * The operations dashboard, derived entirely from the real document library.
 *
 * There is no analytics service, so every number here is computed from
 * `GET /documents` rather than read from a warehouse. That constrains what the
 * dashboard is allowed to claim:
 *
 *   - Volume, exceptions and period-over-period deltas are real: every
 *     document carries `uploadedAt`, so both windows can be counted exactly.
 *   - Risk bands are real *when a document has been scored*. Until the
 *     analysis services land, `risk` is null on every row — so the risk panels
 *     report zero and the response is marked `degraded`, rather than
 *     presenting an invented distribution as fact.
 */

import type { NextRequest } from "next/server";
import { handle } from "@/lib/server/backend";
import { fetchAllDocuments } from "@/lib/server/documents";
import type { Dashboard, DateRange, DocumentSummary, Kpi } from "@/lib/types";

const DAYS: Record<DateRange, number> = { "7d": 7, "30d": 30, "90d": 90 };
const DAY_MS = 86_400_000;

/** At or above this score a document is "high risk" — matches the detail view's banding. */
const HIGH_RISK = 67;
const ELEVATED_RISK = 34;

/** The document types the volume chart plots, in legend order. */
const CHART_TYPES = ["Invoice", "Contract", "Amendment", "Statement", "Unknown"] as const;

export async function GET(request: NextRequest) {
  return handle(async () => {
    const url = new URL(request.url);
    const rangeParam = url.searchParams.get("range");
    const range: DateRange = rangeParam === "7d" || rangeParam === "90d" ? rangeParam : "30d";

    const all = await fetchAllDocuments(request.signal);
    return Response.json(buildDashboard(all, range));
  });
}

function buildDashboard(all: DocumentSummary[], range: DateRange): Dashboard {
  const days = DAYS[range];
  const now = Date.now();
  const windowStart = now - days * DAY_MS;
  const previousStart = windowStart - days * DAY_MS;

  const current = all.filter((d) => d.uploadedAt >= windowStart);
  const previous = all.filter((d) => d.uploadedAt >= previousStart && d.uploadedAt < windowStart);

  const failedNow = current.filter((d) => d.status === "failed");
  const failedBefore = previous.filter((d) => d.status === "failed");

  const scored = current.filter((d) => d.risk !== null);
  const highNow = scored.filter((d) => (d.risk ?? 0) >= HIGH_RISK);
  const highBefore = previous.filter((d) => d.risk !== null && d.risk >= HIGH_RISK);

  const awaiting = all.filter((d) => d.status === "queued" || d.status === "processing");

  const kpis: Kpi[] = [
    {
      key: "processed",
      label: "Documents ingested",
      value: current.length.toLocaleString(),
      ...delta(current.length, previous.length, "more-is-good"),
      icon: "bars",
      iconTone: "--accent",
      footnote: `vs. ${previous.length.toLocaleString()} in the previous ${days} days`,
    },
    {
      key: "exceptions",
      label: "Failed documents",
      value: failedNow.length.toLocaleString(),
      ...delta(failedNow.length, failedBefore.length, "less-is-good"),
      icon: "warning",
      iconTone: "--warn",
      footnote: `vs. ${failedBefore.length} in the previous ${days} days`,
    },
    {
      key: "high",
      label: "High risk documents",
      value: highNow.length.toLocaleString(),
      ...delta(highNow.length, highBefore.length, "less-is-good"),
      icon: "shield",
      iconTone: "--bad",
      footnote: scored.length
        ? `risk >= ${HIGH_RISK} · ${scored.length} of ${current.length} scored`
        : "no documents have been risk-scored yet",
    },
    {
      key: "awaiting",
      // No delta: this is a live queue depth, not a period total, so a
      // period-over-period comparison would not mean anything.
      label: "Awaiting analysis",
      value: awaiting.length.toLocaleString(),
      icon: "clock",
      iconTone: awaiting.length ? "--warn" : "--ok",
      footnote: "queued or processing right now",
    },
  ];

  return {
    kpis,
    flagged: all
      .filter(
        (d) => d.verdict === "Needs review" || d.status === "failed" || d.status === "processing",
      )
      .slice(0, 6),
    exceptions: exceptionBreakdown(failedNow),
    gauge: riskGauge(scored),
    series: volumeSeries(current, days, now),
    volume: current.length,
    generatedAt: new Date(now).toLocaleString("en-GB", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
    // Says plainly why the risk panels are empty, instead of leaving the user
    // to conclude that nothing in the library is risky.
    degraded:
      current.length > 0 && scored.length === 0
        ? {
            panel: "Risk scoring",
            message:
              "No document has been risk-scored, so the risk gauge and high-risk count read zero. " +
              "Scoring is produced by the analysis pipeline, which is not deployed yet.",
          }
        : undefined,
  };
}

type DeltaFields = Pick<Kpi, "delta" | "direction" | "deltaTone">;

/** A real period-over-period change, with the tone chosen by what the metric means. */
function delta(now: number, before: number, polarity: "more-is-good" | "less-is-good"): DeltaFields {
  if (before === 0 && now === 0) return { delta: "0", direction: "up", deltaTone: "--idle" };

  const direction = now >= before ? "up" : "down";
  const text = before === 0 ? `+${now}` : `${Math.round((Math.abs(now - before) / before) * 100)}%`;

  const good = polarity === "more-is-good" ? direction === "up" : direction === "down";
  return {
    delta: text,
    direction,
    deltaTone: now === before ? "--idle" : good ? "--ok" : "--warn",
  };
}

/** Failure counts grouped by the error the pipeline reported, as a share of all failures. */
function exceptionBreakdown(failed: DocumentSummary[]): [string, number][] {
  if (failed.length === 0) return [];

  const counts = new Map<string, number>();
  for (const doc of failed) {
    const label = doc.error?.title ?? "Unclassified failure";
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([label, n]) => [label, Math.round((n / failed.length) * 100)] as [string, number]);
}

function riskGauge(scored: DocumentSummary[]): Dashboard["gauge"] {
  const low = scored.filter((d) => (d.risk ?? 0) < ELEVATED_RISK).length;
  const elevated = scored.filter(
    (d) => (d.risk ?? 0) >= ELEVATED_RISK && (d.risk ?? 0) < HIGH_RISK,
  ).length;
  const high = scored.filter((d) => (d.risk ?? 0) >= HIGH_RISK).length;

  const pct = scored.length ? Math.round((low / scored.length) * 100) : 0;

  return {
    pct,
    target:
      scored.length === 0
        ? "No documents scored yet"
        : pct >= 70
          ? "Ahead of the 70% low-risk target"
          : "Below the 70% low-risk target",
    legend: [
      { label: "Low", value: low, tone: "--ok" },
      { label: "Elevated", value: elevated, tone: "--warn" },
      { label: "High", value: high, tone: "--bad" },
    ],
  };
}

/**
 * Daily ingestion counts per document type, oldest day first.
 *
 * Bucketed on calendar-day boundaries derived from `now`, so the rightmost
 * point is always today and the series lines up with the range label.
 */
function volumeSeries(docs: DocumentSummary[], days: number, now: number): Dashboard["series"] {
  const startOfToday = new Date(now).setHours(0, 0, 0, 0);

  return CHART_TYPES.map((name) => {
    const counts = new Array<number>(days).fill(0);
    for (const doc of docs) {
      if (doc.type !== name) continue;
      const startOfDoc = new Date(doc.uploadedAt).setHours(0, 0, 0, 0);
      const dayIndex = days - 1 - Math.round((startOfToday - startOfDoc) / DAY_MS);
      if (dayIndex >= 0 && dayIndex < days) counts[dayIndex] += 1;
    }
    return { name, counts };
  }).filter((s) => s.counts.some((c) => c > 0));
}
