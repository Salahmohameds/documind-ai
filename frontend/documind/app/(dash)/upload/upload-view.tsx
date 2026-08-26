"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type CSSProperties, type DragEvent } from "react";
import {
  ApiError,
  getDocumentStatus,
  uploadDocument,
  validateFile,
} from "@/lib/api";
import { PIPELINE_STEPS, UPLOAD_LIMITS, WORKSPACE } from "@/lib/mock/data";
import { useHealth } from "@/lib/use-health";
import type { UploadJob } from "@/lib/types";
import { PipelineTrack } from "@/components/documind/pipeline";
import { ConfirmDialog, EmptyPanel, InlineError, Spinner, Toaster, useToasts } from "@/components/documind/feedback";
import { CloudUploadIcon } from "@/components/ui/icons";
import { Button } from "@/components/ui/button";
import { Anim, AnimatePresence, GrowBar, Sweep } from "@/components/motion";

/** How often the elapsed clock and the pipeline poll advance. */
const CLOCK_MS = 250;
const POLL_MS = 2500;

/** Concurrent uploads. Two keeps a slow file from stalling the whole batch. */
const MAX_CONCURRENT = 2;

const dropzoneBase: CSSProperties = {
  minHeight: 220,
  height: "clamp(220px, 32vh, 260px)",
  borderRadius: 10,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: 16,
};

let jobId = 0;

function newJob(file: File): UploadJob {
  const sizeMb = file.size / 1_000_000;
  const check = validateFile(file.name, sizeMb);
  return {
    id: `job_${++jobId}`,
    file,
    name: file.name,
    ext: (file.name.split(".").pop() ?? "").toUpperCase(),
    sizeMb,
    // The classifier runs server-side, so the type is unknown until the
    // pipeline reports one. Guessing from the filename would put a label on
    // the document that no service ever agreed to.
    type: "Detecting\u2026",
    stage: check.ok ? "queued" : "rejected",
    rejected: check.ok ? undefined : check.reason,
    uploadPct: 0,
    step: 0,
    stepPct: 0,
    startedAt: Date.now(),
    elapsedMs: 0,
    retries: 0,
  };
}

function fmtElapsed(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

const TERMINAL: UploadJob["stage"][] = ["done", "failed", "cancelled", "rejected"];

/** Maps a document lifecycle state onto the pipeline track the panel renders. */
function stepForStatus(status: string, reported?: { step: number } | null): number {
  if (status === "completed") return PIPELINE_STEPS.length;
  if (status === "queued") return 1;
  // The pipeline reports its own stage once processing-service is running;
  // until then a processing document sits at the first post-upload step.
  return reported?.step ?? 2;
}

function errorFor(cause: unknown, name: string): UploadJob["error"] {
  const api = cause instanceof ApiError ? cause : null;
  return {
    code: api?.code ?? "ERR_UPLOAD_FAILED",
    title: api?.title ?? "Upload failed",
    detail: api?.detail ?? `${name} could not be uploaded.`,
    job: "upload",
    at: new Date().toISOString(),
    retryable: api?.retryable ?? true,
  };
}

/**
 * Owns the real ingestion run.
 *
 * Every stage transition here is caused by something a service actually said:
 * the transfer percentage comes from the XHR upload progress event, and the
 * pipeline stage comes from polling `GET /documents/{id}/status`. Nothing
 * advances on a timer of its own.
 */
function useUploadQueue() {
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const controllers = useRef(new Map<string, AbortController>());
  // Guards against a second start for the same job when the effect re-runs
  // before React has committed the "uploading" state.
  const started = useRef(new Set<string>());

  const patch = useCallback((id: string, next: Partial<UploadJob>) => {
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, ...next } : j)));
  }, []);

  // The elapsed clock, which is the only thing that legitimately ticks.
  useEffect(() => {
    const t = setInterval(() => {
      setJobs((prev) => {
        let changed = false;
        const next = prev.map((j) => {
          if (TERMINAL.includes(j.stage)) return j;
          changed = true;
          return { ...j, elapsedMs: Date.now() - j.startedAt };
        });
        return changed ? next : prev;
      });
    }, CLOCK_MS);
    return () => clearInterval(t);
  }, []);

  const send = useCallback(
    async (job: UploadJob) => {
      const controller = new AbortController();
      controllers.current.set(job.id, controller);
      patch(job.id, { stage: "uploading", uploadPct: 0 });

      try {
        const doc = await uploadDocument(job.file, {
          signal: controller.signal,
          onProgress: (uploadPct) => patch(job.id, { uploadPct }),
        });
        patch(job.id, {
          stage: "processing",
          uploadPct: 100,
          docId: doc.id,
          type: doc.type,
          step: stepForStatus(doc.status, doc.progress),
          stepPct: doc.progress?.pct ?? 0,
        });
      } catch (cause) {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        patch(job.id, { stage: "failed", error: errorFor(cause, job.name) });
      } finally {
        controllers.current.delete(job.id);
      }
    },
    [patch],
  );

  // Admits queued jobs up to the concurrency limit.
  useEffect(() => {
    const active = jobs.filter((j) => j.stage === "uploading").length;
    const free = MAX_CONCURRENT - active;
    if (free <= 0) return;

    for (const job of jobs.filter((j) => j.stage === "queued").slice(0, free)) {
      if (started.current.has(job.id)) continue;
      started.current.add(job.id);
      void send(job);
    }
  }, [jobs, send]);

  // Follows every uploaded document until its pipeline run settles. The key is
  // a string so the effect restarts only when the set of live jobs changes,
  // not on every progress tick.
  const live = jobs
    .filter((j) => j.stage === "processing" && j.docId)
    .map((j) => `${j.id}:${j.docId}`)
    .join(",");

  useEffect(() => {
    if (live === "") return;
    const controller = new AbortController();

    const poll = async () => {
      const pairs = live.split(",").map((entry) => entry.split(":") as [string, string]);
      await Promise.all(
        pairs.map(async ([id, docId]) => {
          try {
            const status = await getDocumentStatus(docId, controller.signal);
            if (status.status === "completed") {
              patch(id, { stage: "done", step: PIPELINE_STEPS.length, stepPct: 100 });
            } else if (status.status === "failed") {
              patch(id, { stage: "failed", error: status.error ?? errorFor(null, docId) });
            } else {
              patch(id, {
                step: stepForStatus(status.status, status.progress),
                stepPct: status.progress?.pct ?? 0,
              });
            }
          } catch {
            // A dropped poll is not a failed document - the next tick retries.
          }
        }),
      );
    };

    const t = setInterval(poll, POLL_MS);
    return () => {
      controller.abort();
      clearInterval(t);
    };
  }, [live, patch]);

  const add = useCallback((files: File[]) => {
    setJobs((prev) => {
      const room = UPLOAD_LIMITS.maxBatch - prev.length;
      return [...prev, ...files.slice(0, Math.max(0, room)).map(newJob)];
    });
  }, []);

  /**
   * Re-uploads the file. There is no reprocess route, so a retry genuinely
   * creates a new document rather than re-running the old one.
   */
  const retry = useCallback((id: string) => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === id
          ? {
              ...j,
              stage: "queued",
              step: 0,
              stepPct: 0,
              uploadPct: 0,
              error: undefined,
              docId: undefined,
              retries: j.retries + 1,
              startedAt: Date.now(),
              elapsedMs: 0,
            }
          : j,
      ),
    );
    started.current.delete(id);
  }, []);

  const cancel = useCallback((id: string) => {
    controllers.current.get(id)?.abort();
    controllers.current.delete(id);
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, stage: "cancelled" } : j)));
  }, []);

  const remove = useCallback((id: string) => {
    controllers.current.get(id)?.abort();
    controllers.current.delete(id);
    setJobs((prev) => prev.filter((j) => j.id !== id));
  }, []);

  const clearFinished = useCallback(
    () =>
      setJobs((prev) =>
        prev.filter((j) => j.stage !== "done" && j.stage !== "cancelled" && j.stage !== "rejected"),
      ),
    [],
  );

  const clearAll = useCallback(() => {
    for (const c of controllers.current.values()) c.abort();
    controllers.current.clear();
    setJobs([]);
  }, []);

  return { jobs, add, retry, cancel, remove, clearFinished, clearAll };
}

export function UploadView() {
  const { jobs, add, retry, cancel, remove, clearFinished, clearAll } = useUploadQueue();
  const health = useHealth();
  const [dragging, setDragging] = useState(false);
  const [dragCount, setDragCount] = useState(0);
  const [confirmClear, setConfirmClear] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { toasts, push, dismiss } = useToasts();
  const announced = useRef(new Set<string>());

  const uploading = jobs.filter((j) => j.stage === "uploading" || j.stage === "queued");
  const processing = jobs.filter((j) => j.stage === "processing");
  const done = jobs.filter((j) => j.stage === "done");
  const failed = jobs.filter((j) => j.stage === "failed");
  const rejected = jobs.filter((j) => j.stage === "rejected");
  const cancelled = jobs.filter((j) => j.stage === "cancelled");
  const inFlight = uploading.length + processing.length;
  const finished = inFlight === 0 && jobs.length > 0;

  const uploadedMb = jobs.reduce((sum, j) => sum + (j.sizeMb * j.uploadPct) / 100, 0);
  const totalMb = jobs.reduce((sum, j) => sum + j.sizeMb, 0);
  const uploadPct = totalMb ? Math.round((uploadedMb / totalMb) * 100) : 0;

  // Announce each terminal outcome once.
  useEffect(() => {
    for (const j of jobs) {
      if (j.stage !== "done" && j.stage !== "failed") continue;
      if (announced.current.has(j.id + j.stage + j.retries)) continue;
      announced.current.add(j.id + j.stage + j.retries);
      if (j.stage === "done") {
        push({ tone: "--ok", glyph: "✓", title: "Document indexed", body: `${j.name} finished in ${fmtElapsed(j.elapsedMs)}.` });
      } else {
        push({ tone: "--bad", glyph: "✕", title: "Pipeline failed", body: `${j.name} — ${j.error?.code ?? "unknown error"}.` });
      }
    }
  }, [jobs, push]);

  const onFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    add(Array.from(files));
  };

  // Paste-to-upload, as advertised in the dropzone copy.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const files = e.clipboardData?.files;
      if (files && files.length) onFiles(files);
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragging(true);
    setDragCount(e.dataTransfer?.items?.length ?? 0);
  };
  const onDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    onFiles(e.dataTransfer?.files ?? null);
  };

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflow: "auto",
        padding: "20px clamp(14px, 2vw, 24px) 76px",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* Header --------------------------------------------------------- */}
      <Anim
        style={{ flex: "none", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-.025em", color: "var(--text)" }}>Upload</span>
          <span style={{ fontSize: 12, color: "var(--text-3)" }}>
            Ingest documents and track pipeline progress · {WORKSPACE.region}
          </span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <div
            className="card"
            style={{ display: "flex", alignItems: "center", gap: 8, height: 36, padding: "0 12px", borderRadius: 10 }}
          >
            <span
              className="dot"
              style={{
                width: 6,
                height: 6,
                background:
                  health.status === "ready"
                    ? "var(--ok)"
                    : health.status === "degraded"
                      ? "var(--warn)"
                      : "var(--text-3)",
              }}
            />
            <span
              style={{ fontSize: 12, fontWeight: 500, color: "var(--text-2)" }}
              title={health.detail}
            >
              {health.label}
            </span>
            <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
              p50 3.4s
            </span>
          </div>
          <Button variant="surface" size="dmQuiet">Connect bucket</Button>
        </div>
      </Anim>

      {/* Dropzone ------------------------------------------------------- */}
      <Anim
        style={{ flex: "none", display: "flex", flexDirection: "column", gap: 10 }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            onFiles(e.target.files);
            e.target.value = "";
          }}
        />

        <AnimatePresence mode="wait" initial={false}>
        {dragging ? (
          <Anim
            key="dragging"
            preset="scale"
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            style={{
              ...dropzoneBase,
              border: "1.5px solid var(--accent)",
              background: "var(--accent-soft)",
              transition: "border-color .18s ease, background .18s ease",
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                border: "1px solid var(--accent-border)",
                background: "var(--surface)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                color: "var(--accent)",
              }}
            >
              ↓
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 15, fontWeight: 600, color: "var(--accent)" }}>
                Drop to upload{dragCount ? ` ${dragCount} file${dragCount === 1 ? "" : "s"}` : ""}
              </span>
              <span className="mono" style={{ fontSize: 12, color: "var(--text-2)" }}>
                {UPLOAD_LIMITS.extensions.join(", ").toUpperCase()} · max {UPLOAD_LIMITS.maxMb} MB each
              </span>
            </div>
          </Anim>
        ) : inFlight > 0 ? (
          <Anim
            key="inflight"
            preset="scale"
            style={{
              ...dropzoneBase,
              gap: 18,
              padding: 32,
              border: "1px solid var(--border)",
              background: "var(--surface)",
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                border: "1px solid var(--accent-border)",
                background: "var(--accent-soft)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Spinner size={18} />
            </div>
            <div style={{ width: 440, maxWidth: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "baseline" }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>
                  {uploading.length > 0
                    ? `Uploading ${uploading.length} file${uploading.length === 1 ? "" : "s"}`
                    : `Processing ${processing.length} file${processing.length === 1 ? "" : "s"}`}
                </span>
                <span className="mono" style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-2)" }}>
                  {uploadPct}%
                </span>
              </div>
              <div style={{ height: 6, borderRadius: 10, background: "var(--border)", overflow: "hidden" }}>
                <div style={{ width: `${uploadPct}%`, height: "100%", background: "var(--accent)", transition: "width .2s linear" }} />
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span
                  className="mono"
                  style={{ fontSize: 11, color: "var(--text-3)", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                >
                  {(uploading[0] ?? processing[0])?.name} · {uploadedMb.toFixed(1)} / {totalMb.toFixed(1)} MB
                </span>
                <span className="mono" style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-3)", flex: "none" }}>
                  {done.length} of {jobs.length} complete
                </span>
              </div>
            </div>
            <Button variant="outlineStrong" size="dmQuiet" onClick={() => setConfirmClear(true)} style={{ height: 30, padding: "0 12px" }}>
              Cancel all
            </Button>
          </Anim>
        ) : finished ? (
          <Anim
            key="finished"
            preset="scale"
            style={{
              ...dropzoneBase,
              border: `1px solid var(${failed.length ? "--warn" : "--ok"}-border)`,
              background: `var(${failed.length ? "--warn" : "--ok"}-soft)`,
            }}
          >
            <Anim
              preset="pop"
              style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                border: `1px solid var(${failed.length ? "--warn" : "--ok"}-border)`,
                background: "var(--surface)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                color: `var(${failed.length ? "--warn" : "--ok"})`,
              }}
            >
              {failed.length ? "!" : "✓"}
            </Anim>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, textAlign: "center", maxWidth: 460 }}>
              <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>
                {failed.length === 0
                  ? `${done.length} file${done.length === 1 ? "" : "s"} indexed`
                  : `${done.length} of ${done.length + failed.length} files indexed`}
              </span>
              <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
                {failed.length === 0
                  ? "Every document completed classification, extraction, PII scanning and risk scoring."
                  : `${failed.length} document${failed.length === 1 ? "" : "s"} stopped mid-pipeline. Retry below — extraction failures usually clear on a second run.`}
                {rejected.length > 0 && ` ${rejected.length} file${rejected.length === 1 ? " was" : "s were"} rejected before upload.`}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Button size="dm" onClick={() => inputRef.current?.click()} style={{ padding: "0 16px" }}>
                Upload more
              </Button>
              <Link
                href="/documents"
                style={{ height: 32, display: "inline-flex", alignItems: "center", fontSize: 13, fontWeight: 500, padding: "0 8px" }}
              >
                View documents →
              </Link>
            </div>
          </Anim>
        ) : (
          <Anim
            key="idle"
            preset="scale"
            className="hover-surface"
            onDragOver={onDragOver}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            style={{
              ...dropzoneBase,
              border: "1.5px dashed var(--border-strong)",
              background: "var(--surface)",
              cursor: "pointer",
              transition: "border-color .18s ease, background .18s ease",
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "var(--surface-2)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CloudUploadIcon size={22} color="var(--text-3)" />
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>Drag documents here to upload</span>
              <span style={{ fontSize: 13, color: "var(--text-2)" }}>
                or <span style={{ color: "var(--accent)" }}>browse your computer</span> · paste with ⌘V
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }} onClick={(e) => e.stopPropagation()}>
              <Button size="dm" onClick={() => inputRef.current?.click()} style={{ height: 34, fontWeight: 500, padding: "0 16px" }}>
                Select files
              </Button>
            </div>
          </Anim>
        )}
        </AnimatePresence>

        <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "0 2px", flexWrap: "wrap" }}>
          {[
            `${UPLOAD_LIMITS.extensions.map((e) => e.toUpperCase()).join(" · ")}`,
            `max ${UPLOAD_LIMITS.maxMb} MB per file`,
            `up to ${UPLOAD_LIMITS.maxBatch} files per batch`,
          ].map((t, i) => (
            <span key={t} style={{ display: "contents" }}>
              {i > 0 && <span style={{ width: 1, height: 12, background: "var(--border)" }} />}
              <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
                {t}
              </span>
            </span>
          ))}
          <span
            className="mono"
            style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-3)" }}
            title={health.detail}
          >
            {health.services.map((svc) => `${svc.service}: ${svc.state}`).join("  \u00b7  ") ||
              "checking services\u2026"}
          </span>
        </div>
      </Anim>

      {/* Queue ---------------------------------------------------------- */}
      {jobs.length === 0 ? (
        <EmptyPanel
          compact
          glyph="⌁"
          title="Nothing in the queue"
          body="Files you add appear here with live progress through all seven pipeline stages — upload, classification, extraction, PII scanning, risk scoring and indexing."
        />
      ) : (
        <Anim
          className="card"
          style={{
            flex: "none",
            minHeight: "fit-content",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              flex: "none",
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "14px 16px",
              borderBottom: "1px solid var(--border)",
              flexWrap: "wrap",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>Upload queue</span>
            <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
              {[
                `${jobs.length} file${jobs.length === 1 ? "" : "s"}`,
                done.length && `${done.length} complete`,
                processing.length && `${processing.length} processing`,
                uploading.length && `${uploading.length} uploading`,
                failed.length && `${failed.length} failed`,
                rejected.length && `${rejected.length} rejected`,
                cancelled.length && `${cancelled.length} cancelled`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
              {done.length + cancelled.length + rejected.length > 0 && (
                <Button variant="outlineStrong" size="dmSm" onClick={clearFinished}>
                  Clear finished
                </Button>
              )}
              <Button variant="outlineStrong" size="dmSm"
                onClick={() => setConfirmClear(true)}
                disabled={jobs.length === 0}
              >
                Clear queue
              </Button>
            </div>
          </div>

          <AnimatePresence initial={false}>
          {jobs.map((job) => (
            <QueueRow
              key={job.id}
              job={job}
              onRetry={() => retry(job.id)}
              onCancel={() => cancel(job.id)}
              onRemove={() => remove(job.id)}
            />
          ))}
          </AnimatePresence>
        </Anim>
      )}

      <ConfirmDialog
        open={confirmClear}
        danger
        title="Clear the upload queue?"
        body={
          inFlight > 0
            ? `${inFlight} file${inFlight === 1 ? " is" : "s are"} still in flight. Cancelling stops them mid-pipeline — nothing partially processed is kept.`
            : "This removes every row from the queue. Documents that already finished stay in your library."
        }
        confirmLabel={inFlight > 0 ? "Cancel and clear" : "Clear queue"}
        onCancel={() => setConfirmClear(false)}
        onConfirm={() => {
          clearAll();
          setConfirmClear(false);
        }}
      />

      <Toaster toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}

/* -- Queue row ----------------------------------------------------------- */

const STAGE_META: Record<UploadJob["stage"], { tone: string; label: (j: UploadJob) => string }> = {
  queued: { tone: "--idle", label: () => "Waiting for a slot" },
  uploading: { tone: "--accent", label: (j) => `Uploading ${j.uploadPct}%` },
  processing: { tone: "--accent", label: (j) => PIPELINE_STEPS[Math.max(0, j.step - 1)] },
  done: { tone: "--ok", label: () => "Complete" },
  failed: { tone: "--bad", label: (j) => `Failed at ${PIPELINE_STEPS[Math.max(0, j.step - 1)]}` },
  cancelled: { tone: "--idle", label: () => "Cancelled" },
  rejected: { tone: "--warn", label: () => "Rejected" },
};

function QueueRow({
  job,
  onRetry,
  onCancel,
  onRemove,
}: {
  job: UploadJob;
  onRetry: () => void;
  onCancel: () => void;
  onRemove: () => void;
}) {
  const meta = STAGE_META[job.stage];
  const tone = meta.tone;
  const showTrack = job.stage === "processing" || job.stage === "done" || job.stage === "failed";

  return (
    // `layout` closes the gap when a row is removed, instead of the rows
    // below it jumping up.
    <Anim
      preset="row"
      layout
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 14,
        padding: 16,
        borderBottom: "1px solid var(--border)",
        transition: "background .3s ease, opacity .3s ease",
        background:
          job.stage === "failed"
            ? "var(--bad-soft)"
            : job.stage === "rejected"
              ? "var(--warn-soft)"
              : job.stage === "cancelled"
                ? "var(--surface-2)"
                : "transparent",
        opacity: job.stage === "cancelled" ? 0.7 : 1,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <span
          className="mono"
          style={{
            width: 26,
            height: 26,
            flex: "none",
            borderRadius: 10,
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 8,
            fontWeight: 600,
            color: "var(--text-3)",
          }}
        >
          {job.ext.slice(0, 4) || "?"}
        </span>
        <span
          title={job.name}
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: "var(--text)",
            flex: "1 1 200px",
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            textDecoration: job.stage === "cancelled" ? "line-through" : undefined,
          }}
        >
          {job.name}
        </span>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-3)", flex: "none" }}>
          {job.sizeMb.toFixed(1)} MB
        </span>
        {job.stage !== "rejected" && (
          <span className="pill pill-neutral" style={{ flex: "none" }}>
            {job.type}
          </span>
        )}
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            flex: "none",
            fontSize: 11,
            fontWeight: 500,
            padding: "2px 8px",
            borderRadius: 10,
            color: `var(${tone})`,
            background: job.stage === "failed" || job.stage === "rejected" ? "var(--surface)" : `var(${tone}-soft)`,
            border: `1px solid var(${tone}-border)`,
          }}
        >
          {job.stage === "uploading" || job.stage === "processing" ? (
            <Spinner size={9} color={`var(${tone})`} track={`var(${tone}-border)`} />
          ) : (
            <span className="dot" style={{ background: `var(${tone})` }} />
          )}
          {meta.label(job)}
          {job.retries > 0 && job.stage !== "failed" && (
            <span className="mono" style={{ opacity: 0.7 }}>· retry {job.retries}</span>
          )}
        </span>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10, flex: "none" }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
            {job.stage === "done"
              ? `Completed in ${fmtElapsed(job.elapsedMs)}`
              : job.stage === "failed"
                ? `Failed after ${fmtElapsed(job.elapsedMs)}`
                : job.stage === "rejected" || job.stage === "cancelled"
                  ? ""
                  : `Elapsed ${fmtElapsed(job.elapsedMs)}`}
          </span>
          {job.stage === "done" && job.docId && (
            <Link href={`/documents/${job.docId}`} style={{ fontSize: 12, fontWeight: 500 }}>
              View document →
            </Link>
          )}
          {job.stage === "failed" && (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {job.error?.retryable ? (
                <Button size="dmSm" onClick={onRetry}>
                  Retry {PIPELINE_STEPS[Math.max(0, job.step - 1)].toLowerCase()}
                </Button>
              ) : (
                <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
                  not retryable
                </span>
              )}
              <Button variant="outlineStrong" size="dmSm" onClick={onRemove} style={{ padding: "0 10px" }}>
                Remove
              </Button>
            </div>
          )}
          {(job.stage === "uploading" || job.stage === "processing" || job.stage === "queued") && (
            <Button variant="outlineStrong" size="dmSm" onClick={onCancel} style={{ padding: "0 10px" }}>
              Cancel
            </Button>
          )}
          {(job.stage === "cancelled" || job.stage === "rejected") && (
            <Button variant="outlineStrong" size="dmSm" onClick={onRemove} style={{ padding: "0 10px" }}>
              Remove
            </Button>
          )}
        </div>
      </div>

      {showTrack && (
        <div className="dm-scroll-x">
          <div style={{ minWidth: 620 }}>
            <PipelineTrack
              step={job.step}
              state={job.stage === "done" ? "done" : job.stage === "failed" ? "failed" : "running"}
            />
          </div>
        </div>
      )}

      {job.stage === "uploading" && (
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Sweep style={{ flex: 1, height: 4, borderRadius: 10, background: "var(--border)" }}>
            <GrowBar pct={job.uploadPct} color="var(--accent)" />
          </Sweep>
          <span className="mono" style={{ fontSize: 11, color: "var(--text-3)", flex: "none" }}>
            {((job.sizeMb * job.uploadPct) / 100).toFixed(1)} / {job.sizeMb.toFixed(1)} MB
          </span>
        </div>
      )}

      {job.stage === "processing" && (
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ flex: 1, height: 4, borderRadius: 10, background: "var(--border)", overflow: "hidden" }}>
            <div style={{ width: `${job.stepPct}%`, height: "100%", background: "var(--accent)", transition: "width .16s linear" }} />
          </div>
          <span className="mono" style={{ fontSize: 11, color: "var(--text-3)", flex: "none" }}>
            {PIPELINE_STEPS[Math.max(0, job.step - 1)]} — {Math.min(100, job.stepPct)}%
          </span>
        </div>
      )}

      {job.stage === "failed" && job.error && (
        <InlineError
          title={job.error.title}
          detail={job.error.detail}
          code={`${job.error.code} · ${job.error.job} · ${job.error.at}`}
        />
      )}

      {job.stage === "rejected" && job.rejected && (
        <InlineError tone="--warn" title="File rejected before upload" detail={job.rejected} />
      )}
    </Anim>
  );
}
