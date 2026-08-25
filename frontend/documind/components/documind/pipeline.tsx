"use client";

import type { CSSProperties } from "react";
import { PIPELINE_STEPS } from "@/lib/mock/data";
import { Anim, Spinner, Stagger, motion } from "@/components/motion";
import { SPRING } from "@/lib/motion";

export type StepKind = "done" | "failed" | "active" | "pending";

/**
 * The seven-stage ingestion track. Shown on the upload queue and again on a
 * document that is still processing, so both read as the same pipeline.
 */
export function PipelineTrack({
  step,
  state,
  compact,
}: {
  /** 1-based index of the step currently reached. */
  step: number;
  state: "running" | "done" | "failed" | "queued";
  compact?: boolean;
}) {
  const last = PIPELINE_STEPS.length - 1;

  const kindOf = (i: number): StepKind => {
    const n = i + 1;
    if (state === "done") return "done";
    if (state === "queued") return "pending";
    if (n < step) return "done";
    if (n === step) return state === "failed" ? "failed" : "active";
    return "pending";
  };

  const dotSize = compact ? 14 : 18;

  return (
    <Stagger gap={0.04} style={{ display: "flex", alignItems: "flex-start" }}>
      {PIPELINE_STEPS.map((label, i) => {
        const n = i + 1;
        const kind = kindOf(i);
        const tone = kind === "done" ? "--ok" : kind === "failed" ? "--bad" : kind === "active" ? "--accent" : null;

        const reached = n <= step || state === "done";
        const railBefore = reached && kind !== "pending" ? `var(${tone})` : "var(--border)";
        const railAfter = state === "done" && n < PIPELINE_STEPS.length ? "var(--ok)" : "var(--border)";
        const rail = (background: string): CSSProperties => ({ flex: 1, height: 1, background });

        return (
          <Anim
            key={label}
            preset="row"
            style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}
          >
            <div style={{ display: "flex", alignItems: "center", width: "100%" }}>
              {/* The rail crossfades to its tone as the stage completes, so the
                  track fills left-to-right as work lands. */}
              <motion.span
                animate={{ backgroundColor: i === 0 ? "transparent" : railBefore }}
                transition={{ duration: 0.35 }}
                style={rail(i === 0 ? "transparent" : railBefore)}
              />
              {kind === "active" ? (
                <Spinner
                  size={dotSize}
                  color="var(--accent)"
                  track="var(--accent-border)"
                  style={{ borderWidth: 2 }}
                />
              ) : (
                <motion.span
                  layout
                  transition={SPRING.snappy}
                  initial={false}
                  animate={{ scale: kind === "pending" ? 1 : [0.7, 1] }}
                  style={{
                    width: dotSize,
                    height: dotSize,
                    flex: "none",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: compact ? 8 : 9,
                    color: kind === "pending" ? "transparent" : "#fff",
                    background: kind === "pending" ? "var(--surface)" : `var(${tone})`,
                    border: `1px solid ${kind === "pending" ? "var(--border-strong)" : `var(${tone})`}`,
                  }}
                >
                  {kind === "done" ? "✓" : kind === "failed" ? "✕" : ""}
                </motion.span>
              )}
              <motion.span
                animate={{
                  backgroundColor: i === last ? "transparent" : n < step ? "var(--ok)" : railAfter,
                }}
                transition={{ duration: 0.35 }}
                style={rail(i === last ? "transparent" : n < step ? "var(--ok)" : railAfter)}
              />
            </div>
            <motion.span
              animate={{
                color:
                  kind === "done"
                    ? "var(--text-2)"
                    : kind === "failed"
                      ? "var(--bad)"
                      : kind === "active"
                        ? "var(--accent)"
                        : "var(--text-3)",
              }}
              transition={{ duration: 0.3 }}
              style={{
                fontSize: compact ? 10 : 11,
                fontWeight: kind === "pending" ? 400 : kind === "done" ? 450 : 600,
                textAlign: "center",
                whiteSpace: "nowrap",
              }}
            >
              {label}
            </motion.span>
          </Anim>
        );
      })}
    </Stagger>
  );
}
