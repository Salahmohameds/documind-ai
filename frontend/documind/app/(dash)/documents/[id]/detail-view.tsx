"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { getDocument, reprocessDocuments, tickProcessing, type Simulate } from "@/lib/api";
import { useAction, useAsync } from "@/lib/use-async";
import { PIPELINE_STEPS } from "@/lib/mock/data";
import { confidenceTone, riskTone, v } from "@/lib/design";
import type { DocumentDetail, PiiFinding, Tone } from "@/lib/types";
import { PipelineTrack } from "@/components/documind/pipeline";
import {
  ConfirmDialog,
  ErrorPanel,
  InlineError,
  Spinner,
  StateSwitcher,
  Toaster,
  useToasts,
} from "@/components/documind/feedback";
import {
  ChatIcon,
  DownloadIcon,
  FileIcon,
  KebabIcon,
  LockIcon,
  RefreshIcon,
} from "@/components/ui/icons";
import { Button } from "@/components/ui/button";

const SIMULATIONS = [
  { value: "ok" as const, label: "Default" },
  { value: "slow" as const, label: "Slow" },
  { value: "error" as const, label: "Error" },
];

const SEVERITY_TONE: Record<string, Tone> = { High: "--bad", Medium: "--warn", Low: "--ok" };

const eyebrow: CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  letterSpacing: ".1em",
  textTransform: "uppercase",
  color: "var(--text-3)",
};

const panel: CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 18,
  boxShadow: "0 1px 2px rgba(16,24,40,.05)",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
};

export function DocumentDetailView({ id }: { id: string }) {
  const [simulate, setSimulate] = useState<Simulate>("ok");
  const [confirmReprocess, setConfirmReprocess] = useState(false);
  const { toasts, push, update, dismiss } = useToasts();

  const doc = useAsync((signal) => getDocument(id, { simulate, signal }), [id, simulate]);
  const reprocess = useAction(reprocessDocuments);

  const detail = doc.data;
  const processing = detail?.status === "processing";

  // Keep a processing document moving while the page is open.
  const reloadDoc = doc.reload;
  useEffect(() => {
    if (!processing || simulate !== "ok") return;
    const t = setInterval(() => {
      tickProcessing();
      reloadDoc();
    }, 1800);
    return () => clearInterval(t);
  }, [processing, simulate, reloadDoc]);

  async function runReprocess() {
    setConfirmReprocess(false);
    const toastId = push({ tone: "--accent", glyph: "", pending: true, title: "Reprocessing…", body: "The document re-entered the pipeline at classification." }, 0);
    const result = await reprocess.run([id]);
    doc.reload();
    if (result && result.failed.length > 0) {
      update(toastId, { pending: false, tone: "--bad", glyph: "✕", title: "Could not reprocess", body: result.failed[0].reason });
    } else {
      update(toastId, { pending: false, tone: "--ok", glyph: "✓", title: "Reprocessing started", body: "Progress appears in the pipeline track above." });
    }
  }

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflow: "auto",
        padding: "22px clamp(14px, 2vw, 26px) 76px",
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}
    >
      {doc.status === "loading" && <DetailSkeleton slow={simulate === "slow"} />}

      {doc.status === "error" && doc.error && (
        <ErrorPanel
          title={doc.error.title}
          detail={doc.error.detail}
          code={doc.error.code}
          onRetry={doc.error.retryable ? doc.retry : undefined}
          actions={
            <Button asChild variant="surface" size="dmQuiet">
              <Link href="/documents">
              Back to documents
              </Link>
            </Button>
          }
        />
      )}

      {detail && doc.status !== "error" && (
        <>
          {/* Identity card ------------------------------------------------ */}
          <div
            className="anim-up"
            style={{
              flex: "none",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 18,
              boxShadow: "0 6px 22px rgba(16,24,40,.05)",
              overflow: "hidden",
              opacity: doc.status === "reloading" ? 0.8 : 1,
              transition: "opacity .15s",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: 20, padding: "22px 24px 20px", flexWrap: "wrap" }}>
              <div
                style={{
                  width: 46,
                  height: 46,
                  flex: "none",
                  borderRadius: 14,
                  background: "var(--accent-soft)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <FileIcon size={21} color="var(--accent)" />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 7, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Link href="/documents" style={{ fontSize: 12 }}>
                    Documents
                  </Link>
                  <span style={{ fontSize: 12, color: "var(--text-3)" }}>/</span>
                  <span className="mono" style={{ fontSize: 12, color: "var(--text-3)" }}>
                    {detail.id}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.03em", color: "var(--text)", textWrap: "balance" }}>
                    {detail.name}
                  </span>
                  <StatusPill detail={detail} />
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                  {[
                    `${detail.pages} pages`,
                    `${detail.sizeMb.toFixed(1)} MB`,
                    `Uploaded ${detail.uploaded}`,
                    detail.status === "completed" ? `Processed in ${detail.processedIn}` : detail.counterparty,
                    `model ${detail.model}`,
                  ].map((meta, i) => (
                    <span key={meta} style={{ display: "contents" }}>
                      {i > 0 && <span style={{ width: 1, height: 10, background: "var(--border)" }} />}
                      <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
                        {meta}
                      </span>
                    </span>
                  ))}
                </div>
              </div>

              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <Button variant="surface" size="dmQuiet"
                  disabled={detail.status !== "completed"}
                  title={detail.status !== "completed" ? "No extraction to download yet" : undefined}
                  onClick={() => push({ tone: "--ok", glyph: "✓", title: "JSON ready", body: `${detail.id}.json · ${detail.fields.length} fields, ${detail.pii.length} PII findings.` })}
                  style={{ height: 38, opacity: detail.status !== "completed" ? 0.5 : 1 }}
                >
                  <DownloadIcon size={15} color="var(--text-3)" />
                  Download JSON
                </Button>
                <Button variant="surface" size="dmQuiet"
                  disabled={detail.status === "processing" || reprocess.pending}
                  title={detail.status === "processing" ? "Already running" : undefined}
                  onClick={() => setConfirmReprocess(true)}
                  style={{ height: 38, opacity: detail.status === "processing" ? 0.5 : 1 }}
                >
                  {reprocess.pending ? <Spinner size={14} color="var(--text-2)" track="var(--border)" /> : <RefreshIcon size={15} color="var(--text-3)" />}
                  Reprocess
                </Button>
                {detail.status === "completed" ? (
                  <Button asChild size="dm">
                    <Link href={`/qa/${detail.id}`} style={{ height: 38, padding: "0 16px" }}>
                    <ChatIcon size={15} color="#fff" />
                    Ask questions
                    </Link>
                  </Button>
                ) : (
                  <Button size="dm"
                    disabled
                    title="Q&A opens once the document is indexed"
                    style={{ height: 38, padding: "0 16px", opacity: 0.5 }}
                  >
                    <ChatIcon size={15} color="#fff" />
                    Ask questions
                  </Button>
                )}
              </div>
            </div>

            {detail.status === "completed" ? (
              <SummaryStrip detail={detail} />
            ) : (
              <div style={{ borderTop: "1px solid var(--border)", background: "var(--surface-2)", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={eyebrow}>Pipeline</span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
                    {detail.status === "processing" && detail.progress
                      ? `${PIPELINE_STEPS[detail.progress.step - 1]} — ${detail.progress.pct}%`
                      : detail.status === "queued"
                        ? "Waiting for a worker"
                        : "Stopped"}
                  </span>
                </div>
                <div className="dm-scroll-x">
                  <div style={{ minWidth: 620 }}>
                    <PipelineTrack
                      step={detail.progress?.step ?? (detail.status === "failed" ? 3 : 0)}
                      state={detail.status === "processing" ? "running" : detail.status === "failed" ? "failed" : "queued"}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Non-complete states ------------------------------------------ */}
          {detail.status === "failed" && detail.error && (
            <div style={{ ...panel, borderColor: "var(--bad-border)", padding: 18, gap: 14 }}>
              <InlineError
                title={detail.error.title}
                detail={detail.error.detail}
                code={`${detail.error.code} · ${detail.error.job} · ${detail.error.at}`}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {detail.error.retryable ? (
                  <Button size="dm" onClick={() => setConfirmReprocess(true)} style={{ padding: "0 16px" }}>
                    Retry from classification
                  </Button>
                ) : (
                  <Button asChild size="dm">
                    <Link href="/upload" style={{ padding: "0 16px" }}>
                    Upload a corrected file
                    </Link>
                  </Button>
                )}
                <Button asChild variant="surface" size="dmQuiet">
                  <Link href="/documents">
                  Back to documents
                  </Link>
                </Button>
              </div>
            </div>
          )}

          {detail.status === "queued" && (
            <div style={{ ...panel, padding: 18, gap: 10 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>Queued for processing</span>
              <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
                This document is waiting for a free worker. Extraction, PII scanning and risk scoring all run once it
                starts — usually within a minute at current queue depth.
              </span>
            </div>
          )}

          {detail.status === "processing" && (
            <div style={{ ...panel, padding: 18, gap: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Spinner size={14} />
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>Analysis in progress</span>
                <span className="mono" style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-3)" }}>
                  step {detail.progress?.step ?? 1} of {PIPELINE_STEPS.length}
                </span>
              </div>
              <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
                Extracted fields, PII findings and the risk score appear here as soon as the run completes. You can leave
                this page — processing continues in the background.
              </span>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 14 }}>
                {["Extracted information", "Sensitive data", "Findings"].map((label) => (
                  <div
                    key={label}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                      padding: "14px 16px",
                      borderRadius: 12,
                      background: "var(--surface-2)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <span style={eyebrow}>{label}</span>
                    <span className="skeleton" style={{ width: "70%", height: 12 }} />
                    <span className="skeleton" style={{ width: "45%", height: 12 }} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completed content -------------------------------------------- */}
          {detail.status === "completed" && (
            <>
              {detail.partial && (
                <InlineError
                  tone="--warn"
                  title="Partial extraction"
                  detail={`${detail.partial.message} Pages ${detail.partial.pagesSkipped.join(" and ")} produced no fields — everything else on this page is complete.`}
                  onRetry={() => setConfirmReprocess(true)}
                />
              )}

              <RiskPanel detail={detail} />

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(340px,1fr))", gap: 18, alignItems: "start" }}>
                <div className="anim-up" style={{ ["--i" as string]: 5, minWidth: 0 }}>
                  <ExtractionPanel detail={detail} />
                </div>
                <div className="anim-up" style={{ ["--i" as string]: 6, minWidth: 0 }}>
                  <FindingsPanel detail={detail} />
                </div>
              </div>
            </>
          )}
        </>
      )}

      <ConfirmDialog
        open={confirmReprocess}
        pending={reprocess.pending}
        title="Reprocess this document?"
        body="The document re-enters the pipeline at classification. Existing fields, PII findings and the risk score stay visible until the new run finishes and replaces them."
        confirmLabel="Reprocess"
        onCancel={() => setConfirmReprocess(false)}
        onConfirm={runReprocess}
      />

      <Toaster toasts={toasts} onDismiss={dismiss} />
      <StateSwitcher value={simulate} options={SIMULATIONS} onChange={setSimulate} />
    </div>
  );
}

/* -- Pieces -------------------------------------------------------------- */

function StatusPill({ detail }: { detail: DocumentDetail }) {
  const tone: Tone =
    detail.status === "completed"
      ? "--ok"
      : detail.status === "processing"
        ? "--warn"
        : detail.status === "failed"
          ? "--bad"
          : "--idle";
  const label =
    detail.status === "completed"
      ? "Completed"
      : detail.status === "processing"
        ? "Processing"
        : detail.status === "failed"
          ? "Failed"
          : "Queued";
  return (
    <span
      style={{
        flex: "none",
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 11,
        fontWeight: 600,
        color: v(tone),
        background: v(tone, "-soft"),
        borderRadius: 999,
        padding: "4px 11px",
      }}
    >
      {detail.status === "processing" ? (
        <Spinner size={9} color={v(tone)} track={v(tone, "-border")} />
      ) : (
        <span className="dot" style={{ background: v(tone) }} />
      )}
      {label}
    </span>
  );
}

function SummaryStrip({ detail }: { detail: DocumentDetail }) {
  const c = detail.classification;
  const avgConfidence = detail.fields.length
    ? detail.fields.reduce((s, f) => s + f.confidence, 0) / detail.fields.length
    : 0;
  const bySeverity = {
    High: detail.findings.filter((f) => f.severity === "High").length,
    Medium: detail.findings.filter((f) => f.severity === "Medium").length,
    Low: detail.findings.filter((f) => f.severity === "Low").length,
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))",
        borderTop: "1px solid var(--border)",
        background: "var(--surface-2)",
      }}
    >
      <SummaryCell label="Classification">
        <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
          <span className="mono" style={{ fontSize: 19, fontWeight: 600, letterSpacing: "-.01em", color: "var(--text)" }}>
            {c.label}
          </span>
          <span
            style={{
              fontSize: 10,
              fontWeight: 500,
              color: "var(--text-2)",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 999,
              padding: "3px 8px",
            }}
          >
            {c.subtype}
          </span>
        </div>
        <span style={{ fontSize: 11, color: "var(--text-3)" }}>
          {c.confidence}% confidence · next best {c.runnerUp} ({c.runnerUpConfidence}%)
        </span>
        <Meter pct={c.confidence} color={v(confidenceTone(c.confidence))} />
      </SummaryCell>

      <SummaryCell label="Extracted fields" divider>
        <span style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-.02em", color: "var(--text)", lineHeight: 1 }}>
          {detail.fields.length}
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-3)" }}> / {detail.fieldsExpected}</span>
        </span>
        <span style={{ fontSize: 11, color: "var(--text-3)" }}>avg {avgConfidence.toFixed(1)}% confidence</span>
        <Meter pct={avgConfidence} color={v(confidenceTone(avgConfidence))} />
      </SummaryCell>

      <SummaryCell label="PII detected" divider>
        <span
          style={{
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: "-.02em",
            color: detail.pii.length ? "var(--warn)" : "var(--ok)",
            lineHeight: 1,
          }}
        >
          {detail.pii.length}
        </span>
        <span style={{ fontSize: 11, color: "var(--text-3)" }}>
          {detail.pii.length ? "masked by policy · reveals audit-logged" : "no sensitive data detected"}
        </span>
        <Meter pct={Math.min(100, detail.pii.length * 18)} color={detail.pii.length ? "var(--warn)" : "var(--ok)"} />
      </SummaryCell>

      <SummaryCell label="Findings" divider>
        <span style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-.02em", color: "var(--text)", lineHeight: 1 }}>
          {detail.findings.length}
        </span>
        <span style={{ fontSize: 11, color: "var(--text-3)" }}>
          {detail.findings.length
            ? `${bySeverity.High} high · ${bySeverity.Medium} medium · ${bySeverity.Low} low`
            : "nothing flagged"}
        </span>
        <div style={{ display: "flex", gap: 3, height: 4 }}>
          {detail.findings.length === 0 ? (
            <div style={{ flex: 1, borderRadius: 999, background: "var(--border)" }} />
          ) : (
            <>
              {bySeverity.High > 0 && <div style={{ flex: bySeverity.High, borderRadius: 999, background: "var(--bad)" }} />}
              {bySeverity.Medium > 0 && <div style={{ flex: bySeverity.Medium, borderRadius: 999, background: "var(--warn)" }} />}
              {bySeverity.Low > 0 && <div style={{ flex: bySeverity.Low, borderRadius: 999, background: "var(--ok)" }} />}
            </>
          )}
        </div>
      </SummaryCell>
    </div>
  );
}

function RiskPanel({ detail }: { detail: DocumentDetail }) {
  const score = detail.risk ?? 0;
  const tone = riskTone(score);
  const band = score <= 33 ? "Low risk" : score <= 66 ? "Elevated risk" : "High risk";
  const highCount = detail.findings.filter((f) => f.severity === "High").length;

  return (
    <div
      className="anim-up"
      style={{
        ["--i" as string]: 1,
        flex: "none",
        background: v(tone, "-soft"),
        border: `1px solid ${v(tone, "-border")}`,
        borderRadius: 18,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))",
          gap: 28,
          padding: "22px clamp(16px, 2vw, 24px)",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18, minWidth: 0 }}>
          <div
            style={{
              position: "relative",
              width: 104,
              height: 104,
              flex: "none",
              borderRadius: "50%",
              background: `conic-gradient(${v(tone)} 0deg ${score * 3.6}deg, var(--surface) ${score * 3.6}deg 360deg)`,
              boxShadow: "0 2px 10px rgba(16,24,40,.08)",
              transition: "background .6s var(--ease-out)",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 11,
                borderRadius: "50%",
                background: "var(--surface)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span className="mono" style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-.04em", lineHeight: 1, color: v(tone) }}>
                {score}
              </span>
              <span className="mono" style={{ fontSize: 10, color: "var(--text-3)", marginTop: 1 }}>
                / 100
              </span>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
            <span style={eyebrow}>Risk analysis</span>
            <span
              style={{
                alignSelf: "flex-start",
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: "-.01em",
                color: v(tone),
                background: "var(--surface)",
                border: `1px solid ${v(tone, "-border")}`,
                borderRadius: 999,
                padding: "5px 13px",
              }}
            >
              {band}
            </span>
            <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
              Recalculated {detail.time}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          <span style={{ fontSize: 13, lineHeight: 1.55, color: "var(--text-2)", textWrap: "pretty" }}>
            {score >= 67
              ? `Score 67–100 requires legal sign-off before countersignature — ${highCount} finding${highCount === 1 ? "" : "s"} ${highCount === 1 ? "is" : "are"} driving this score.`
              : score >= 34
                ? "Elevated scores are routed to a reviewer but do not block signature."
                : "Low-risk documents are auto-approved and need no reviewer action."}{" "}
            <span style={{ color: "var(--accent)", fontWeight: 500 }}>How this is scored →</span>
          </span>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(148px,1fr))", gap: 14 }}>
            {detail.riskCategories.map((cat, i) => {
              const ct = riskTone(cat.score);
              const level = cat.score <= 33 ? "Low" : cat.score <= 66 ? "Medium" : "High";
              return (
                <div
                  key={cat.name}
                  className="anim-up"
                  style={{
                    ["--i" as string]: i + 2,
                    display: "flex",
                    flexDirection: "column",
                    gap: 7,
                    padding: "12px 14px",
                    borderRadius: 12,
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)" }}>{cat.name}</span>
                    <span className="mono" style={{ marginLeft: "auto", fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
                      {cat.score}
                    </span>
                  </div>
                  <div style={{ height: 5, borderRadius: 999, background: "var(--border)", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${cat.score}%`,
                        height: "100%",
                        borderRadius: 10,
                        background: v(ct),
                        transition: "width .6s var(--ease-out), background .3s ease",
                      }}
                    />
                  </div>
                  <span
                    style={{
                      alignSelf: "flex-start",
                      fontSize: 10,
                      fontWeight: 600,
                      letterSpacing: ".06em",
                      textTransform: "uppercase",
                      color: v(ct),
                      background: v(ct, "-soft"),
                      borderRadius: 999,
                      padding: "3px 8px",
                    }}
                  >
                    {level}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function ExtractionPanel({ detail }: { detail: DocumentDetail }) {
  const avg = detail.fields.length ? detail.fields.reduce((s, f) => s + f.confidence, 0) / detail.fields.length : 0;
  const [lowOnly, setLowOnly] = useState(false);
  const fields = lowOnly ? detail.fields.filter((f) => f.confidence < 95) : detail.fields;

  return (
    <div style={panel}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "20px 22px 14px" }}>
        <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-.01em", color: "var(--text)" }}>
          Extracted information
        </span>
        <span className="mono" style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-3)" }}>
          {detail.fields.length} of {detail.fieldsExpected} · avg {avg.toFixed(1)}%
        </span>
        <button
          onClick={() => setLowOnly((l) => !l)}
          title={lowOnly ? "Show every field" : "Show only fields below 95% confidence"}
          style={{
            display: "flex",
            color: lowOnly ? "var(--accent)" : "var(--text-3)",
            cursor: "pointer",
            background: "transparent",
            border: "none",
          }}
        >
          <KebabIcon />
        </button>
      </div>

      {lowOnly && (
        <div style={{ padding: "0 22px 12px" }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--accent)" }}>
            Filtered to {fields.length} field{fields.length === 1 ? "" : "s"} under 95% confidence
          </span>
        </div>
      )}

      {fields.length === 0 ? (
        <div style={{ padding: "8px 22px 22px", display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>
            {lowOnly ? "Every field is above 95% confidence" : "No fields were extracted"}
          </span>
          <span style={{ fontSize: 12, lineHeight: 1.55, color: "var(--text-2)" }}>
            {lowOnly
              ? "Nothing on this document needs a manual confidence check."
              : "The extraction template produced no values for this document type."}
          </span>
        </div>
      ) : (
        fields.map((f) => {
          const ct = confidenceTone(f.confidence);
          return (
            <div
              key={f.key}
              className="hover-surface"
              style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 22px", borderTop: "1px solid var(--border)" }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0, flex: 1 }}>
                <span style={{ ...eyebrow, letterSpacing: ".09em" }}>{f.key}</span>
                <span
                  className="mono"
                  title={f.value}
                  style={{ fontSize: 13, color: "var(--text)", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                >
                  {f.value}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flex: "none" }}>
                <div style={{ width: 52, height: 4, borderRadius: 999, background: "var(--border)", overflow: "hidden" }}>
                  <div style={{ width: `${f.confidence}%`, height: "100%", background: v(ct) }} />
                </div>
                <span className="mono" style={{ fontSize: 11, fontWeight: 500, color: v(ct), width: 34, textAlign: "right" }}>
                  {f.confidence}%
                </span>
                <Link
                  href={`/qa/${detail.id}`}
                  className="mono"
                  style={{ fontSize: 11, whiteSpace: "nowrap", flex: "none", minWidth: 40, textAlign: "right" }}
                >
                  p. {f.page}
                </Link>
              </div>
            </div>
          );
        })
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "18px 22px 12px",
          borderTop: "1px solid var(--border)",
          background: "var(--surface-2)",
          flexWrap: "wrap",
        }}
      >
        <LockIcon size={15} color={detail.pii.length ? "var(--warn)" : "var(--ok)"} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>Sensitive data</span>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: detail.pii.length ? "var(--warn)" : "var(--ok)",
            background: detail.pii.length ? "var(--warn-soft)" : "var(--ok-soft)",
            borderRadius: 999,
            padding: "3px 9px",
          }}
        >
          {detail.pii.length} finding{detail.pii.length === 1 ? "" : "s"}
        </span>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-3)" }}>
          Masked by policy · reveals audit-logged
        </span>
      </div>

      <PiiList items={detail.pii} />
    </div>
  );
}

function PiiList({ items }: { items: PiiFinding[] }) {
  const [revealed, setRevealed] = useState<string[]>([]);
  const [pending, setPending] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div style={{ padding: "0 22px 18px", background: "var(--surface-2)" }}>
        <span style={{ fontSize: 12, color: "var(--text-2)" }}>
          No bank details, tax IDs or personal contact data were detected in this document.
        </span>
      </div>
    );
  }

  const toggle = (id: string) => {
    if (revealed.includes(id)) {
      setRevealed((s) => s.filter((x) => x !== id));
      return;
    }
    // A reveal is audit-logged server-side, so it round-trips.
    setPending(id);
    setTimeout(() => {
      setRevealed((s) => s.concat(id));
      setPending(null);
    }, 550);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", background: "var(--surface-2)", padding: "0 22px 18px" }}>
      {items.map((p) => {
        const on = revealed.includes(p.id);
        const busy = pending === p.id;
        return (
          <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 0" }}>
            <span style={{ fontSize: 12, color: "var(--text-2)", width: 132, flex: "none" }}>{p.type}</span>
            <span
              className="mono"
              style={{
                fontSize: 12,
                color: on ? "var(--text)" : "var(--text-2)",
                letterSpacing: on ? 0 : ".04em",
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {on ? p.value : p.masked}
            </span>
            <span className="mono" style={{ marginLeft: "auto", fontSize: 11, flex: "none", color: "var(--accent)" }}>
              p. {p.page}
            </span>
            <button
              onClick={() => toggle(p.id)}
              disabled={busy}
              style={{
                flex: "none",
                width: 54,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "flex-end",
                gap: 5,
                fontSize: 11,
                fontWeight: 500,
                color: on ? "var(--text-2)" : "var(--accent)",
                cursor: busy ? "default" : "pointer",
                padding: "2px 4px",
                background: "transparent",
                border: "none",
              }}
            >
              {busy && <Spinner size={9} />}
              {busy ? "…" : on ? "Hide" : "Reveal"}
            </button>
          </div>
        );
      })}
    </div>
  );
}

function FindingsPanel({ detail }: { detail: DocumentDetail }) {
  const [expanded, setExpanded] = useState<string[]>([]);
  const LIMIT = 260;

  return (
    <div style={panel}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "20px 22px 16px" }}>
        <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-.01em", color: "var(--text)" }}>Findings</span>
        <span className="mono" style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-3)" }}>
          {detail.findings.length} total
        </span>
        <span style={{ display: "flex", color: "var(--text-3)" }}>
          <KebabIcon />
        </span>
      </div>

      {detail.findings.length === 0 ? (
        <div style={{ padding: "0 22px 22px", display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>No findings</span>
          <span style={{ fontSize: 12, lineHeight: 1.55, color: "var(--text-2)", textWrap: "pretty" }}>
            Nothing in this document breached a policy rule. It was auto-approved without reviewer action.
          </span>
        </div>
      ) : (
        <div style={{ position: "relative", padding: "0 22px 20px" }}>
          <div style={{ position: "absolute", left: 27, top: 4, bottom: 34, width: 1, background: "var(--border)" }} />
          {detail.findings.map((f, i) => {
            const cv = SEVERITY_TONE[f.severity];
            const long = f.description.length > LIMIT;
            const open = expanded.includes(f.id);
            return (
              <div
                key={f.id}
                className="anim-row"
                style={{
                  ["--i" as string]: i,
                  position: "relative",
                  display: "flex",
                  gap: 14,
                  padding: "8px 0 16px",
                }}
              >
                <span
                  style={{
                    width: 11,
                    height: 11,
                    borderRadius: "50%",
                    flex: "none",
                    marginTop: 4,
                    background: v(cv),
                    boxShadow: `0 0 0 3px ${v(cv, "-soft")}`,
                  }}
                />
                <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{f.title}</span>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        letterSpacing: ".06em",
                        textTransform: "uppercase",
                        color: v(cv),
                        background: v(cv, "-soft"),
                        borderRadius: 999,
                        padding: "3px 8px",
                      }}
                    >
                      {f.severity}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, lineHeight: 1.55, color: "var(--text-2)", textWrap: "pretty" }}>
                    {long && !open ? `${f.description.slice(0, LIMIT).trimEnd()}…` : f.description}
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <Link href={`/qa/${detail.id}`} className="mono" style={{ fontSize: 11 }}>
                      page {f.page} →
                    </Link>
                    {long && (
                      <button
                        onClick={() => setExpanded((s) => (open ? s.filter((x) => x !== f.id) : s.concat(f.id)))}
                        style={{ fontSize: 11, fontWeight: 500, color: "var(--accent)", background: "transparent", border: "none", cursor: "pointer" }}
                      >
                        {open ? "Show less" : "Show more"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SummaryCell({ label, divider, children }: { label: string; divider?: boolean; children: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 7,
        padding: "18px 24px",
        borderLeft: divider ? "1px solid var(--border)" : undefined,
      }}
    >
      <span style={eyebrow}>{label}</span>
      {children}
    </div>
  );
}

function Meter({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{ height: 4, borderRadius: 999, background: "var(--border)", overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, height: "100%", background: color, transition: "width .3s" }} />
    </div>
  );
}

function DetailSkeleton({ slow }: { slow: boolean }) {
  return (
    <>
      <div style={{ ...panel, borderRadius: 18, gap: 0 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 20, padding: "22px 24px 20px" }}>
          <span className="skeleton" style={{ width: 46, height: 46, borderRadius: 14, flex: "none" }} />
          <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
            <span className="skeleton" style={{ width: 160, height: 10 }} />
            <span className="skeleton" style={{ width: "46%", height: 22 }} />
            <span className="skeleton" style={{ width: "62%", height: 10 }} />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span className="skeleton" style={{ width: 128, height: 38 }} />
            <span className="skeleton" style={{ width: 108, height: 38 }} />
            <span className="skeleton" style={{ width: 132, height: 38 }} />
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", borderTop: "1px solid var(--border)", background: "var(--surface-2)" }}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", gap: 9, padding: "18px 24px", borderLeft: i ? "1px solid var(--border)" : undefined }}>
              <span className="skeleton" style={{ width: 80, height: 8 }} />
              <span className="skeleton" style={{ width: 120, height: 18 }} />
              <span className="skeleton" style={{ width: "100%", height: 4 }} />
            </div>
          ))}
        </div>
      </div>

      <div style={{ ...panel, borderRadius: 18, padding: "22px 24px", flexDirection: "row", alignItems: "center", gap: 28 }}>
        <span className="skeleton" style={{ width: 104, height: 104, borderRadius: "50%", flex: "none" }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
          <span className="skeleton" style={{ width: "70%", height: 12 }} />
          <span className="skeleton" style={{ width: "100%", height: 62 }} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(340px,1fr))", gap: 18 }}>
        {[7, 5].map((rows, k) => (
          <div key={k} style={{ ...panel, borderRadius: 18, padding: 22, gap: 14 }}>
            <span className="skeleton" style={{ width: 160, height: 14 }} />
            {Array.from({ length: rows }, (_, i) => (
              <span key={i} className="skeleton" style={{ width: `${94 - i * 7}%`, height: 12 }} />
            ))}
          </div>
        ))}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center", paddingTop: 4 }}>
        <Spinner size={12} />
        <span style={{ fontSize: 12, color: "var(--text-3)" }}>
          {slow ? "Still fetching the analysis — this one is slow…" : "Loading document analysis…"}
        </span>
      </div>
    </>
  );
}
