"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import {
  deleteDocuments,
  exportDocuments,
  listDocuments,
  reprocessDocuments,
  tickProcessing,
  type DocumentQuery,
  type Simulate,
  type SortKey,
} from "@/lib/api";
import { useAction, useAsync, useDebounced } from "@/lib/use-async";
import { PIPELINE_STEPS } from "@/lib/mock/data";
import { STATUS, riskTone, tonedPill } from "@/lib/design";
import type { DocType, DocumentSummary } from "@/lib/types";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ConfirmDialog,
  EmptyPanel,
  ErrorPanel,
  Spinner,
  StateSwitcher,
  Toaster,
  useToasts,
} from "@/components/documind/feedback";
import { CaretDownIcon, SearchIcon, UploadIcon } from "@/components/ui/icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Anim, AnimatePresence, Shimmer } from "@/components/motion";

const GRID = "34px minmax(0,1fr) 104px 132px 78px 54px 116px 36px";
const TYPES: (DocType | "All")[] = ["All", "Invoice", "Contract", "Amendment", "Statement"];
const STATUSES: (DocumentSummary["status"] | "All")[] = ["All", "completed", "processing", "failed", "queued"];
const SIZES = [10, 25, 50];
const SKELETON_WIDTHS = [58, 44, 51, 39, 62, 47, 55, 42, 60, 49];

const SIMULATIONS = [
  { value: "ok" as const, label: "Default" },
  { value: "slow" as const, label: "Slow" },
  { value: "empty" as const, label: "Empty" },
  { value: "error" as const, label: "Error" },
];

const headerCell: CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  letterSpacing: ".08em",
  textTransform: "uppercase",
  color: "var(--text-3)",
};

function chipStyle(active: boolean): CSSProperties {
  return {
    flex: "none",
    font: "inherit",
    display: "flex",
    alignItems: "center",
    gap: 8,
    height: 32,
    padding: "0 10px",
    borderRadius: 10,
    cursor: "pointer",
    background: active ? "var(--accent-soft)" : "var(--surface)",
    border: `1px solid ${active ? "var(--accent-border)" : "var(--border)"}`,
  };
}

function checkboxStyle(on: boolean): CSSProperties {
  return {
    width: 14,
    height: 14,
    borderRadius: 4,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 9,
    lineHeight: 1,
    cursor: "pointer",
    color: "#fff",
    background: on ? "var(--accent)" : "transparent",
    border: `1px solid ${on ? "var(--accent)" : "var(--border-strong)"}`,
    transition: "background .16s ease, border-color .16s ease",
  };
}

function pageBtnStyle(active: boolean, disabled = false): CSSProperties {
  return {
    minWidth: 26,
    height: 26,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 10,
    fontSize: 12,
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.4 : 1,
    padding: "0 6px",
    color: active ? "#fff" : "var(--text-2)",
    background: active ? "var(--accent)" : "var(--surface)",
    border: `1px solid ${active ? "var(--accent)" : "var(--border-strong)"}`,
  };
}

const STATUS_LABEL: Record<string, string> = {
  All: "All",
  completed: "Completed",
  processing: "Processing",
  failed: "Failed",
  queued: "Queued",
};

/* -- Menu ---------------------------------------------------------------- */

/**
 * Menus are portaled (Radix) rather than absolutely positioned: the filter card
 * and table rows sit in their own stacking contexts, so an inline menu renders
 * behind the content below it no matter how high its z-index goes.
 */
function Menu({
  trigger,
  children,
  align = "start",
  width = 172,
}: {
  trigger: ReactNode;
  children: ReactNode;
  align?: "start" | "end";
  width?: number;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
      <DropdownMenuContent
        align={align}
        sideOffset={6}
        style={{ width }}
        className="rounded-xl p-1.5 shadow-[0_14px_34px_rgba(11,18,32,.16)]"
      >
        {children}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function MenuItem({
  children,
  onSelect,
  href,
  disabled,
  disabledHint,
  danger,
  selected,
}: {
  children: ReactNode;
  onSelect?: () => void;
  href?: string;
  disabled?: boolean;
  disabledHint?: string;
  danger?: boolean;
  selected?: boolean;
}) {
  const style: CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 8,
    width: "100%",
    padding: "7px 9px",
    borderRadius: 9,
    fontSize: 12,
    cursor: disabled ? "not-allowed" : "pointer",
    color: danger ? "var(--bad)" : "var(--text-2)",
    background: selected ? "var(--surface-2)" : undefined,
  };

  const body = (
    <>
      <span style={{ minWidth: 0, flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>{children}</span>
      {selected && <span style={{ flex: "none", fontSize: 10, color: "var(--accent)" }}>✓</span>}
    </>
  );

  if (href && !disabled) {
    return (
      <DropdownMenuItem asChild onSelect={onSelect} style={style}>
        <Link href={href}>{body}</Link>
      </DropdownMenuItem>
    );
  }

  return (
    <DropdownMenuItem
      disabled={disabled}
      onSelect={onSelect}
      title={disabled ? disabledHint : undefined}
      style={style}
    >
      {body}
    </DropdownMenuItem>
  );
}

/* -- Page ---------------------------------------------------------------- */

export function DocumentsView() {
  const [simulate, setSimulate] = useState<Simulate>("ok");
  const [rawQuery, setRawQuery] = useState("");
  const search = useDebounced(rawQuery);
  const [type, setType] = useState<DocType | "All">("All");
  const [status, setStatus] = useState<DocumentSummary["status"] | "All">("All");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "uploadedAt", dir: "desc" });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(SIZES[0]);
  const [sel, setSel] = useState<string[]>([]);
  const [confirm, setConfirm] = useState<null | "delete" | "reprocess">(null);
  const { toasts, push, update, dismiss } = useToasts();

  const query: DocumentQuery = useMemo(
    () => ({ search, type, status, sort, page, pageSize }),
    [search, type, status, sort, page, pageSize],
  );

  const docs = useAsync(
    (signal) => listDocuments(query, { simulate, signal }),
    [search, type, status, sort.key, sort.dir, page, pageSize, simulate],
  );

  // Any change to the result set starts again from page 1.
  const changeQuery = <T,>(set: (v: T) => void) => (value: T) => {
    set(value);
    setPage(1);
  };
  const onSearch = changeQuery(setRawQuery);
  const onType = changeQuery<DocType | "All">(setType);
  const onStatus = changeQuery<DocumentSummary["status"] | "All">(setStatus);
  const onPageSize = changeQuery<number>(setPageSize);
  const onSimulate = changeQuery<Simulate>(setSimulate);

  // Live pipeline ticker — processing rows advance on their own.
  const { data: docPage, reload } = docs;
  useEffect(() => {
    const anyProcessing = docPage?.rows.some((d) => d.status === "processing");
    if (!anyProcessing || simulate !== "ok") return;
    const t = setInterval(() => {
      tickProcessing();
      reload();
    }, 2200);
    return () => clearInterval(t);
  }, [docPage, reload, simulate]);

  const deleteAction = useAction(deleteDocuments);
  const reprocessAction = useAction(reprocessDocuments);
  const exportAction = useAction(exportDocuments);

  const rows = docs.data?.rows ?? [];
  const total = docs.data?.total ?? 0;
  const unfiltered = docs.data?.unfilteredTotal ?? 0;
  const pageCount = docs.data?.pageCount ?? 1;
  const filtersActive = type !== "All" || status !== "All" || search.trim().length > 0;
  const selectedRows = rows.filter((r) => sel.includes(r.id));
  const allSelected = rows.length > 0 && rows.every((r) => sel.includes(r.id));
  const busy = docs.status === "loading" || deleteAction.pending || reprocessAction.pending;

  const clearFilters = () => {
    setType("All");
    setStatus("All");
    setRawQuery("");
    setPage(1);
  };

  const toggleSort = (key: SortKey) =>
    setSort((s) => ({ key, dir: s.key === key && s.dir === "desc" ? "asc" : "desc" }));

  async function runDelete() {
    const ids = [...sel];
    const result = await deleteAction.run(ids);
    setConfirm(null);
    if (!result) return;
    setSel([]);
    docs.reload();
    if (result.failed.length === 0) {
      push({ tone: "--ok", glyph: "✓", title: `${result.succeeded.length} deleted`, body: "Documents and their extractions were removed." });
    } else if (result.succeeded.length === 0) {
      push({ tone: "--bad", glyph: "✕", title: "Nothing was deleted", body: result.failed[0].reason });
    } else {
      push({
        tone: "--warn",
        glyph: "!",
        title: `${result.succeeded.length} of ${result.requested} deleted`,
        body: `${result.failed.length} could not be removed — ${result.failed[0].reason}`,
      });
    }
  }

  async function runReprocess() {
    const ids = [...sel];
    const result = await reprocessAction.run(ids);
    setConfirm(null);
    if (!result) return;
    setSel([]);
    docs.reload();
    if (result.failed.length === 0) {
      push({ tone: "--accent", glyph: "↻", title: `${result.succeeded.length} queued for reprocessing`, body: "Progress appears in the Status column as each stage completes." });
    } else {
      push({
        tone: "--warn",
        glyph: "!",
        title: `${result.succeeded.length} of ${result.requested} queued`,
        body: `${result.failed[0].name} — ${result.failed[0].reason}`,
      });
    }
  }

  async function runExport(ids: string[] | "all") {
    const id = push({ tone: "--accent", glyph: "", pending: true, title: "Preparing export…", body: "Building the CSV — this usually takes a few seconds." }, 0);
    const result = await exportAction.run(ids);
    if (result) {
      update(id, { pending: false, tone: "--ok", glyph: "✓", title: "Export ready", body: `${result.filename} · ${result.rows} rows.`, action: { label: "Download", onClick: () => dismiss(id) } });
    } else {
      update(id, { pending: false, tone: "--bad", glyph: "✕", title: "Export failed", body: "The export service did not respond. Try again." });
    }
  }

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflow: "auto",
        padding: "20px clamp(14px, 2vw, 24px) 76px",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      {/* Header --------------------------------------------------------- */}
      <Anim
        style={{ flex: "none", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-.025em", color: "var(--text)" }}>
            Documents
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-3)" }}>
            {docs.status === "error"
              ? "Could not reach the document index"
              : docs.status === "loading"
                ? "Loading documents…"
                : unfiltered === 0
                  ? "No documents ingested yet"
                  : `${total.toLocaleString()} of ${unfiltered.toLocaleString()} documents · ${filtersActive ? "filters applied" : "all types and statuses"}`}
            {docs.status === "reloading" && <Spinner size={11} />}
          </span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <Button variant="surface" size="dmQuiet"
            onClick={() => runExport("all")}
            disabled={exportAction.pending || unfiltered === 0}
            style={{ opacity: exportAction.pending || unfiltered === 0 ? 0.55 : 1 }}
          >
            {exportAction.pending && <Spinner size={12} color="var(--text-2)" track="var(--border)" />}
            {exportAction.pending ? "Exporting…" : "Export CSV"}
          </Button>
          <Button asChild size="dm">
            <Link href="/upload">
            <UploadIcon size={15} color="#fff" />
            Upload
            </Link>
          </Button>
        </div>
      </Anim>

      {/* Filter bar ----------------------------------------------------- */}
      <Anim
        className="card"
        style={{
          flex: "none",
          padding: 12,
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            flex: "1 1 220px",
            minWidth: 180,
            maxWidth: 320,
            display: "flex",
            alignItems: "center",
            gap: 8,
            height: 32,
            padding: "0 10px",
            border: "1px solid var(--border)",
            borderRadius: 10,
            background: "var(--surface-2)",
          }}
        >
          <SearchIcon size={13} color="var(--text-3)" />
          <Input
            className="h-auto min-w-0 flex-1 rounded-none border-0 bg-transparent p-0 text-xs text-[var(--text)] shadow-none md:text-xs focus-visible:border-0 focus-visible:ring-0 disabled:bg-transparent dark:bg-transparent dark:disabled:bg-transparent"
            value={rawQuery}
            onChange={(e) => onSearch(e.target.value)}
            placeholder="Search filename, ID or counterparty…"
            aria-label="Search documents"
          />
          {rawQuery !== search && <Spinner size={11} />}
          {rawQuery && rawQuery === search && (
            <button
              onClick={() => onSearch("")}
              aria-label="Clear search"
              style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--text-3)", fontSize: 11 }}
            >
              ✕
            </button>
          )}
        </div>

        <Menu
          trigger={
            <button style={chipStyle(type !== "All")}>
              <span style={{ fontSize: 11, color: "var(--text-3)" }}>Type</span>
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)" }}>{type}</span>
              <CaretDownIcon size={12} color="var(--text-3)" />
            </button>
          }
        >
          {TYPES.map((t) => (
            <MenuItem key={t} selected={type === t} onSelect={() => onType(t)}>
              {t}
            </MenuItem>
          ))}
        </Menu>

        <Menu
          trigger={
            <button style={chipStyle(status !== "All")}>
              <span style={{ fontSize: 11, color: "var(--text-3)" }}>Status</span>
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)" }}>
                {STATUS_LABEL[status]}
              </span>
              <CaretDownIcon size={12} color="var(--text-3)" />
            </button>
          }
        >
          {STATUSES.map((st) => (
            <MenuItem key={st} selected={status === st} onSelect={() => onStatus(st)}>
              {STATUS_LABEL[st]}
            </MenuItem>
          ))}
        </Menu>

        <div className="hover-surface dm-hide-md" style={chipStyle(false)}>
          <span style={{ fontSize: 11, color: "var(--text-3)" }}>Uploaded</span>
          <span className="mono" style={{ fontSize: 12, color: "var(--text)" }}>
            Aug 01 — Aug 25
          </span>
          <CaretDownIcon size={12} color="var(--text-3)" />
        </div>

        {filtersActive && (
          <Button variant="ghost" size="dm"
            onClick={clearFilters}
            style={{
              marginLeft: "auto",
              height: 32,
              fontSize: 12,
              fontWeight: 500,
              color: "var(--text-2)",
              background: "transparent",
              border: "1px solid transparent",
              padding: "0 10px",
            }}
          >
            Clear filters
          </Button>
        )}
      </Anim>

      {/* Error ---------------------------------------------------------- */}
      {docs.status === "error" && docs.error && (
        <ErrorPanel
          title={docs.error.title}
          detail={docs.error.detail}
          code={docs.error.code}
          onRetry={docs.retry}
          actions={
            <Button variant="surface" size="dmQuiet" onClick={() => onSimulate("ok")}>
              Switch to a healthy index
            </Button>
          }
        />
      )}

      {/* Loading -------------------------------------------------------- */}
      {docs.status === "loading" && (
        <div className="card" style={{ flex: "none", overflow: "hidden" }}>
          <div className="dm-scroll-x">
          <div style={{ minWidth: 940 }}>
          <HeaderRow sort={sort} onSort={() => {}} disabled />
          {SKELETON_WIDTHS.slice(0, pageSize > 10 ? 10 : pageSize).map((w, i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: GRID,
                gap: 8,
                height: 56,
                alignItems: "center",
                padding: "0 18px",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <Shimmer delay={i * 0.08} style={{ width: 14, height: 14, borderRadius: 4 }} />
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Shimmer delay={i * 0.08} style={{ width: 22, height: 22, flex: "none" }} />
                <Shimmer delay={i * 0.08} style={{ width: `${w}%`, height: 12 }} />
              </div>
              <Shimmer delay={i * 0.08} style={{ width: 66, height: 16 }} />
              <Shimmer delay={i * 0.08} style={{ width: 96, height: 16 }} />
              <Shimmer delay={i * 0.08} style={{ width: 44, height: 16 }} />
              <Shimmer delay={i * 0.08} style={{ justifySelf: "end", width: 26, height: 10 }} />
              <Shimmer delay={i * 0.08} style={{ justifySelf: "end", width: 84, height: 10 }} />
              <span />
            </div>
          ))}
          </div>
          </div>
          <div
            style={{
              height: 44,
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "0 12px",
              background: "var(--surface-2)",
            }}
          >
            <Spinner size={12} />
            <span style={{ fontSize: 12, color: "var(--text-3)" }}>
              {simulate === "slow" ? "Still querying the index — this one is slow…" : "Loading documents — querying index…"}
            </span>
          </div>
        </div>
      )}

      {/* Empty workspace ------------------------------------------------ */}
      {docs.status !== "loading" && docs.status !== "error" && unfiltered === 0 && (
        <EmptyPanel
          title="No documents yet"
          body="Upload invoices or contracts to start classification, field extraction, PII detection and risk scoring. Processed documents appear here within seconds."
          actions={
            <>
              <Button asChild size="dm">
                <Link href="/upload" style={{ padding: "0 16px" }}>
                Upload documents
                </Link>
              </Button>
              <Button variant="surface" size="dmQuiet">Connect Object Storage bucket</Button>
            </>
          }
          footnote={
            <>
              <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
                PDF · DOCX · TIFF · PNG
              </span>
              <span style={{ width: 1, height: 12, background: "var(--border)" }} />
              <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
                max 200 MB / file
              </span>
            </>
          }
        />
      )}

      {/* No results ----------------------------------------------------- */}
      {docs.status !== "loading" && docs.status !== "error" && unfiltered > 0 && total === 0 && (
        <EmptyPanel
          glyph={<SearchIcon size={17} color="var(--s400)" />}
          compact
          title="No documents match these filters"
          body={`Nothing in the ${unfiltered.toLocaleString()} indexed documents matches ${search ? `“${search}”` : "the current filters"}. Widen the type or status filter, or clear the search.`}
          actions={
            <Button size="dm" onClick={clearFilters} style={{ padding: "0 16px" }}>
              Clear filters
            </Button>
          }
        />
      )}

      {/* Table ---------------------------------------------------------- */}
      {docs.status !== "loading" && docs.status !== "error" && total > 0 && (
        <Anim
          className="card"
          style={{
            flex: "none",
            minHeight: "fit-content",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            opacity: docs.status === "reloading" ? 0.72 : 1,
            transition: "opacity .15s",
          }}
        >
          {sel.length > 0 && (
            <Anim
              preset="down"
              style={{
                minHeight: 40,
                flex: "none",
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "0 12px",
                background: "var(--accent-soft)",
                borderBottom: "1px solid var(--accent-border)",
              }}
            >
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--accent)" }}>
                {sel.length} document{sel.length === 1 ? "" : "s"} selected
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: 8 }}>
                <Button variant="outlineStrong" size="dmQuiet"
                  onClick={() => setConfirm("reprocess")}
                  disabled={busy}
                  style={{ height: 26, padding: "0 10px" }}
                >
                  Reprocess
                </Button>
                <Button variant="outlineStrong" size="dmQuiet"
                  onClick={() => runExport(sel)}
                  disabled={exportAction.pending}
                  style={{ height: 26, padding: "0 10px" }}
                >
                  Export
                </Button>
                <Button variant="destructiveSoft" size="dmQuiet"
                  onClick={() => setConfirm("delete")}
                  disabled={busy}
                  style={{ height: 26, padding: "0 10px", fontSize: 12 }}
                >
                  Delete
                </Button>
              </div>
              {selectedRows.some((r) => r.status === "processing") && (
                <span className="mono" style={{ fontSize: 11, color: "var(--warn)" }}>
                  · includes documents still processing
                </span>
              )}
              <button
                onClick={() => setSel([])}
                style={{
                  marginLeft: "auto",
                  fontSize: 12,
                  color: "var(--text-3)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Deselect all
              </button>
            </Anim>
          )}

          <div className="dm-scroll-x" style={{ minWidth: 0 }}>
          <div style={{ minWidth: 940 }}>
          <HeaderRow
            sort={sort}
            onSort={toggleSort}
            allSelected={allSelected}
            partial={sel.length > 0 && !allSelected}
            onToggleAll={() => setSel(allSelected ? [] : rows.map((r) => r.id))}
          />

          <AnimatePresence initial={false}>
          {rows.map((d) => (
            <Row
              key={d.id}
              doc={d}
              selected={sel.includes(d.id)}
              onToggle={() => setSel((s) => (s.includes(d.id) ? s.filter((x) => x !== d.id) : s.concat(d.id)))}
              onReprocess={async () => {
                const r = await reprocessAction.run([d.id]);
                docs.reload();
                if (r && r.failed.length) push({ tone: "--bad", glyph: "✕", title: "Could not reprocess", body: r.failed[0].reason });
                else push({ tone: "--accent", glyph: "↻", title: "Reprocessing started", body: `${d.name} re-entered the pipeline.` });
              }}
              onDelete={() => {
                setSel([d.id]);
                setConfirm("delete");
              }}
              onExport={() => runExport([d.id])}
            />
          ))}
          </AnimatePresence>
          </div>
          </div>

          <div
            style={{
              minHeight: 44,
              flex: "none",
              display: "flex",
              alignItems: "center",
              gap: 16,
              padding: "6px 12px",
              flexWrap: "wrap",
              borderTop: "1px solid var(--border)",
              background: "var(--surface-2)",
            }}
          >
            <span style={{ fontSize: 12, color: "var(--text-3)" }}>
              Showing {(page - 1) * pageSize + 1}–{(page - 1) * pageSize + rows.length} of {total.toLocaleString()}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 12, color: "var(--text-3)" }}>Rows</span>
              <Menu
                width={92}
                trigger={
                  <button
                    className="mono"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      height: 26,
                      padding: "0 8px",
                      border: "1px solid var(--border-strong)",
                      borderRadius: 10,
                      background: "var(--surface)",
                      cursor: "pointer",
                      fontSize: 12,
                      color: "var(--text)",
                    }}
                  >
                    {pageSize}
                    <CaretDownIcon size={12} color="var(--text-3)" />
                  </button>
                }
              >
                {SIZES.map((n) => (
                  <MenuItem key={n} selected={pageSize === n} onSelect={() => onPageSize(n)}>
                    {n}
                  </MenuItem>
                ))}
              </Menu>
            </div>
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
              <span
                className="mono"
                style={pageBtnStyle(false, page === 1)}
                onClick={() => page > 1 && setPage(page - 1)}
              >
                ‹
              </span>
              {pageWindow(page, pageCount).map((n, i) =>
                n === null ? (
                  <span key={`gap${i}`} className="mono" style={{ fontSize: 12, color: "var(--text-3)", padding: "0 4px" }}>
                    …
                  </span>
                ) : (
                  <span key={n} className="mono" style={pageBtnStyle(page === n)} onClick={() => setPage(n)}>
                    {n}
                  </span>
                ),
              )}
              <span
                className="mono"
                style={pageBtnStyle(false, page === pageCount)}
                onClick={() => page < pageCount && setPage(page + 1)}
              >
                ›
              </span>
            </div>
          </div>
        </Anim>
      )}

      <ConfirmDialog
        open={confirm === "delete"}
        danger
        pending={deleteAction.pending}
        title={`Delete ${sel.length} document${sel.length === 1 ? "" : "s"}?`}
        body="Extractions, PII findings and risk scores are deleted with the document. Documents still processing cannot be deleted until their job is cancelled."
        confirmLabel="Delete permanently"
        onCancel={() => setConfirm(null)}
        onConfirm={runDelete}
      >
        <div
          style={{
            maxHeight: 120,
            overflow: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 4,
            padding: 10,
            borderRadius: 10,
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
          }}
        >
          {selectedRows.map((r) => (
            <span key={r.id} className="mono" style={{ fontSize: 11, color: "var(--text-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {r.name}
              {r.status === "processing" && <span style={{ color: "var(--warn)" }}> · processing</span>}
            </span>
          ))}
        </div>
      </ConfirmDialog>

      <ConfirmDialog
        open={confirm === "reprocess"}
        pending={reprocessAction.pending}
        title={`Reprocess ${sel.length} document${sel.length === 1 ? "" : "s"}?`}
        body="Each document re-enters the pipeline from classification. Existing extractions stay visible until the new run completes. Password-protected documents will be skipped."
        confirmLabel="Reprocess"
        onCancel={() => setConfirm(null)}
        onConfirm={runReprocess}
      />

      <Toaster toasts={toasts} onDismiss={dismiss} />
      <StateSwitcher value={simulate} options={SIMULATIONS} onChange={onSimulate} />
    </div>
  );
}

/* -- Table pieces -------------------------------------------------------- */

function pageWindow(page: number, count: number): (number | null)[] {
  if (count <= 6) return Array.from({ length: count }, (_, i) => i + 1);
  const out: (number | null)[] = [1];
  const from = Math.max(2, page - 1);
  const to = Math.min(count - 1, page + 1);
  if (from > 2) out.push(null);
  for (let i = from; i <= to; i++) out.push(i);
  if (to < count - 1) out.push(null);
  out.push(count);
  return out;
}

function HeaderRow({
  sort,
  onSort,
  allSelected,
  partial,
  onToggleAll,
  disabled,
}: {
  sort: { key: SortKey; dir: "asc" | "desc" };
  onSort: (key: SortKey) => void;
  allSelected?: boolean;
  partial?: boolean;
  onToggleAll?: () => void;
  disabled?: boolean;
}) {
  const head = (label: string, key: SortKey, extra?: CSSProperties) => (
    <span
      onClick={disabled ? undefined : () => onSort(key)}
      style={{
        ...headerCell,
        ...extra,
        cursor: disabled ? "default" : "pointer",
        userSelect: "none",
        color: sort.key === key && !disabled ? "var(--text-2)" : "var(--text-3)",
      }}
    >
      {label}
      {sort.key === key && !disabled && <span style={{ marginLeft: 4 }}>{sort.dir === "asc" ? "↑" : "↓"}</span>}
    </span>
  );

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: GRID,
        gap: 8,
        alignItems: "center",
        padding: "14px 18px 12px",
        borderBottom: "1px solid var(--border)",
      }}
    >
      {disabled ? (
        <span style={{ width: 14, height: 14, borderRadius: 4, border: "1px solid var(--border-strong)" }} />
      ) : (
        <span style={checkboxStyle(!!allSelected)} onClick={onToggleAll} role="checkbox" aria-checked={!!allSelected}>
          {allSelected ? "✓" : partial ? "–" : ""}
        </span>
      )}
      {head("Filename", "name", { paddingLeft: 40 })}
      {head("Type", "type", { paddingLeft: 2 })}
      {head("Status", "status", { paddingLeft: 2 })}
      {head("Risk", "risk", { paddingLeft: 2 })}
      {head("Pages", "pages", { textAlign: "right", justifySelf: "stretch" })}
      {head("Uploaded", "uploadedAt", { textAlign: "right", justifySelf: "stretch" })}
      <span />
    </div>
  );
}

function Row({
  doc,
  selected,
  onToggle,
  onReprocess,
  onDelete,
  onExport,
}: {
  doc: DocumentSummary;
  selected: boolean;
  onToggle: () => void;
  onReprocess: () => void;
  onDelete: () => void;
  onExport: () => void;
}) {
  const st = STATUS[doc.status];
  const rt = doc.risk === null ? "--idle" : riskTone(doc.risk);
  const processing = doc.status === "processing";

  return (
    // `layout` is what makes the rows below a deleted one slide up to close
    // the gap, rather than jumping.
    <Anim
      preset="row"
      layout
      style={{
        position: "relative",
        borderBottom: "1px solid var(--border)",
        background: selected ? "var(--accent-soft)" : doc.status === "failed" ? "var(--bad-soft)" : "transparent",
        transition: "background .18s ease",
      }}
    >
      <Link
        href={`/documents/${doc.id}`}
        className={selected ? undefined : "hover-surface"}
        style={{
          display: "grid",
          gridTemplateColumns: GRID,
          gap: 8,
          height: 56,
          alignItems: "center",
          padding: "0 18px",
        }}
      >
        <span
          style={checkboxStyle(selected)}
          role="checkbox"
          aria-checked={selected}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onToggle();
          }}
        >
          {selected ? "✓" : ""}
        </span>

        <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
          <span
            className="mono"
            style={{
              width: 30,
              height: 30,
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
            {doc.ext.slice(0, 4)}
          </span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, minWidth: 0 }}>
            <span
              title={doc.name}
              style={{
                fontSize: 13,
                fontWeight: 500,
                color: "var(--text)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {doc.name}
            </span>
            <span className="mono" style={{ fontSize: 10, color: "var(--text-3)", flex: "none" }}>
              {doc.id}
            </span>
          </div>
        </div>

        <span className="pill pill-neutral" style={{ justifySelf: "start" }}>
          {doc.type}
        </span>

        <span className="pill" style={{ justifySelf: "start", ...tonedPill(st.tone) }} title={doc.error?.title}>
          {processing ? (
            <Spinner size={9} color="var(--warn)" track="var(--warn-border)" />
          ) : (
            <span className="dot" style={{ background: `var(${st.tone})` }} />
          )}
          {processing && doc.progress ? PIPELINE_STEPS[doc.progress.step - 1] : st.label}
        </span>

        <span
          className="mono"
          style={{
            justifySelf: "start",
            fontSize: 12,
            fontWeight: 500,
            padding: "4px 11px",
            borderRadius: 999,
            ...tonedPill(rt),
          }}
        >
          {doc.risk ?? "—"}
        </span>

        <span className="mono" style={{ fontSize: 12, color: "var(--text-2)", textAlign: "right" }}>
          {doc.pages}
        </span>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-3)", textAlign: "right" }}>
          {doc.uploaded}
        </span>
        <span />
      </Link>

      <div style={{ position: "absolute", right: 14, top: 16 }}>
        <Menu
          align="end"
          width={186}
          trigger={
            <button
              className="hover-text hover-surface"
              aria-label="Row actions"
              style={{
                width: 24,
                height: 24,
                borderRadius: 10,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-3)",
                background: "transparent",
                border: "none",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              ⋯
            </button>
          }
        >
          <MenuItem href={`/documents/${doc.id}`}>Open document</MenuItem>
          <MenuItem
            href={`/qa/${doc.id}`}
            disabled={doc.status !== "completed"}
            disabledHint="Available once processing completes"
          >
            Ask questions
          </MenuItem>
          <MenuItem
            disabled={doc.status === "processing" || doc.error?.retryable === false}
            disabledHint={doc.status === "processing" ? "Already running" : "This document cannot be reprocessed"}
            onSelect={onReprocess}
          >
            Reprocess
          </MenuItem>
          <MenuItem
            disabled={doc.status !== "completed"}
            disabledHint="No extraction to export yet"
            onSelect={onExport}
          >
            Export JSON
          </MenuItem>
          <MenuItem
            danger
            disabled={doc.status === "processing"}
            disabledHint="Cancel the job before deleting"
            onSelect={onDelete}
          >
            Delete
          </MenuItem>
        </Menu>
      </div>

      {processing && doc.progress && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 18px 10px" }}>
          <div style={{ flex: 1, height: 3, borderRadius: 10, background: "var(--border)", overflow: "hidden" }}>
            <div
              style={{
                width: `${Math.round(((doc.progress.step - 1) / PIPELINE_STEPS.length) * 100 + doc.progress.pct / PIPELINE_STEPS.length)}%`,
                height: "100%",
                background: "var(--accent)",
                transition: "width .4s",
              }}
            />
          </div>
          <span className="mono" style={{ fontSize: 10, color: "var(--text-3)", flex: "none" }}>
            step {doc.progress.step} of {PIPELINE_STEPS.length} · {doc.progress.pct}%
          </span>
        </div>
      )}

      {doc.status === "failed" && doc.error && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "0 18px 10px" }}>
          <span className="mono" style={{ fontSize: 10, color: "var(--bad)", flex: "none" }}>
            {doc.error.code}
          </span>
          <span
            style={{
              fontSize: 11,
              color: "var(--text-2)",
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {doc.error.title}
          </span>
          {doc.error.retryable ? (
            <Button variant="outlineStrong" size="dmSm" onClick={onReprocess} style={{ marginLeft: "auto", flex: "none", height: 24 }}>
              Retry
            </Button>
          ) : (
            <span className="mono" style={{ marginLeft: "auto", flex: "none", fontSize: 10, color: "var(--text-3)" }}>
              not retryable
            </span>
          )}
        </div>
      )}
    </Anim>
  );
}
