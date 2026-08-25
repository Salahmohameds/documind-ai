import type { CSSProperties } from "react";

/**
 * Tone variables mirror the `--ok` / `--warn` / `--bad` / `--idle` / `--accent`
 * triplets in globals.css: each has a base, a `-soft` fill and a `-border`.
 */
export type Tone = "--ok" | "--warn" | "--bad" | "--idle" | "--accent";

export type DocStatus = "completed" | "processing" | "failed" | "queued";

export const STATUS: Record<DocStatus, { tone: Tone; label: string }> = {
  completed: { tone: "--ok", label: "Completed" },
  processing: { tone: "--warn", label: "Processing" },
  failed: { tone: "--bad", label: "Failed" },
  queued: { tone: "--idle", label: "Queued" },
};

/** 0–33 low, 34–66 elevated, 67–100 high — the band thresholds used throughout. */
export function riskTone(score: number): Tone {
  if (score <= 33) return "--ok";
  if (score <= 66) return "--warn";
  return "--bad";
}

export function confidenceTone(conf: number): Tone {
  if (conf >= 95) return "--ok";
  if (conf >= 85) return "--warn";
  return "--bad";
}

export const v = (tone: Tone, suffix: "" | "-soft" | "-border" = "") =>
  `var(${tone}${suffix})`;

/** Soft-filled, tone-bordered badge — the shape used for status and risk pills. */
export function tonedPill(tone: Tone): CSSProperties {
  return {
    color: v(tone),
    background: v(tone, "-soft"),
    border: `1px solid ${v(tone, "-border")}`,
  };
}

export function toneDot(tone: Tone): CSSProperties {
  return { background: v(tone) };
}

export function bar(pct: number, color: string): CSSProperties {
  return { width: `${pct}%`, height: "100%", background: color };
}
