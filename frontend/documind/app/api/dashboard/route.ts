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
    flagged: needingAttention(current),
    exceptions: exceptionBreakdown(current),
    gauge: riskGauge(scored),
    series: volumeSeries(current, days, now),
    axis: axisLabels(days, now),
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
/** How many rows the flagged panel shows before "View all" takes over. */
const FLAGGED_LIMIT = 6;

/**
 * The documents an operator should look at, worst first.
 *
 * Scoped to the selected period, because the panel says "in this period" and
 * used to quietly read the whole library instead.
 *
 * Everything at or above the elevated threshold counts, not only the high-risk
 * ones: a dashboard reporting six elevated documents beside an empty "nothing
 * flagged" panel is describing two different libraries. A document that failed
 * needs attention for a different reason and belongs here too.
 */
function needingAttention(docs: DocumentSummary[]): DocumentSummary[] {
  const flagged = docs.filter(
    (d) =>
      d.status === "failed" ||
      d.status === "processing" ||
      (d.risk !== null && d.risk >= ELEVATED_RISK),
  );

  // A failure outranks any score: it has no result at all, where even a
  // high-risk document has been read and understood.
  const rank = (d: DocumentSummary) => (d.status === "failed" ? Infinity : (d.risk ?? 0));
  flagged.sort((a, b) => rank(b) - rank(a));

  return flagged.slice(0, FLAGGED_LIMIT);
}

/**
 * What is wrong with the flagged documents, most common first.
 *
 * Counts failures by their reported cause and risky documents by their band.
 * It used to count failures alone, so a library with eight elevated documents
 * and no failures reported "no exceptions were raised" — which read as an
 * all-clear rather than as "nothing crashed".
 */
function exceptionBreakdown(docs: DocumentSummary[]): [string, number][] {
  const counts = new Map<string, number>();
  let total = 0;

  for (const doc of docs) {
    let label: string | null = null;

    if (doc.status === "failed") {
      label = doc.error?.title ?? "Unclassified failure";
    } else if (doc.risk !== null && doc.risk >= HIGH_RISK) {
      label = "High risk";
    } else if (doc.risk !== null && doc.risk >= ELEVATED_RISK) {
      label = "Elevated risk";
    }

    if (label === null) continue;
    counts.set(label, (counts.get(label) ?? 0) + 1);
    total += 1;
  }

  if (total === 0) return [];

  // A share of the flagged documents, not of the library: "60% elevated" means
  // most of what needs attention is elevated, which is the question this panel
  // is answering.
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([label, n]) => [label, Math.round((n / total) * 100)] as [string, number]);
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
/** How many ticks the x-axis shows, whatever the range. */
const AXIS_TICKS = 7;

/**
 * Tick labels for the volume chart, evenly spaced across the window.
 *
 * Derived from the same `days` and `now` the buckets are, because a label that
 * is computed independently of the data it sits under will eventually disagree
 * with it — which is exactly what happened: the axis was a hardcoded list of
 * dates that read the same whether the range was 7 days or 90.
 *
 * The last tick is always today, since that is the bucket the newest documents
 * land in and the one a reader looks at first.
 */
function axisLabels(days: number, now: number): string[] {
  const startOfToday = new Date(now).setHours(0, 0, 0, 0);
  const ticks = Math.min(AXIS_TICKS, days);

  return Array.from({ length: ticks }, (_, i) => {
    // Spread across the window so the first tick is the oldest day plotted and
    // the last is today, rather than sampling every nth day and stopping short.
    const daysAgo = Math.round(((ticks - 1 - i) * (days - 1)) / Math.max(1, ticks - 1));
    return new Date(startOfToday - daysAgo * DAY_MS).toLocaleDateString("en-GB", {
      month: "short",
      day: "2-digit",
    });
  });
}

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
