import {
  DEMO_CREDENTIALS,
  QA_PAGES,
  QA_FALLBACK,
  UPLOAD_LIMITS,
  answerFor,
} from "@/lib/mock/data";
import { corpus, invalidateCorpus, suggestions } from "@/lib/search/corpus";
import { scoreEntry, snippetAround, tokenize, type Indexed } from "@/lib/search/rank";
import {
  KIND_LABEL,
  KIND_ORDER,
  type SearchGroup,
  type SearchKind,
  type SearchResponse,
} from "@/lib/search/types";
import type {
  ChatScope,
  Dashboard,
  DateRange,
  DocError,
  DocType,
  DocumentDetail,
  DocumentSummary,
  SourceBlock,
  WorkspaceCitation,
} from "@/lib/types";

/**
 * The single seam between the UI and its data.
 *
 * Every function here is async and returns exactly the shape the screens
 * render. The bodies now call this app's own `/api/…` route handlers, which
 * are the only code that knows where `document-service`, `search-service` and
 * `ai-service` live — see `app/api/` and `lib/server/backend.ts`.
 *
 * Two things are still local, and are marked `UNBACKED` where they appear:
 * authentication (no `api-gateway` yet) and the per-document reader fixtures
 * (no `processing-service` to produce page text). Nothing else invents data —
 * where a service has no answer, these functions return an empty or null
 * result and the UI renders its "nothing here" state.
 */

export type Simulate = "ok" | "empty" | "error" | "slow" | "partial";

export class ApiError extends Error {
  constructor(
    readonly title: string,
    readonly detail: string,
    readonly code = "ERR_UPSTREAM_UNAVAILABLE",
    readonly retryable = true,
  ) {
    super(title);
    this.name = "ApiError";
  }
}

export function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });
}

/* -- Transport ----------------------------------------------------------- */

/**
 * One fetch wrapper, so every screen fails the same way.
 *
 * The route handlers all answer errors with `{error, detail, code, retryable}`
 * (see `lib/server/backend.ts`), which maps exactly onto `ApiError` — that is
 * why no caller has to interpret a status code.
 */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  // These paths are relative, which has no meaning without a document base, so
  // a call from the server could only ever fail. During prerendering that is
  // exactly the moment the screen should still be showing its skeleton, so the
  // call parks instead of rejecting: the static shell captures the loading
  // state, and the real request runs after hydration.
  if (typeof window === "undefined") return new Promise<T>(() => {});

  let response: Response;
  try {
    response = await fetch(path, { ...init, headers: { Accept: "application/json", ...init.headers } });
  } catch (cause) {
    // An aborted request is the caller's own doing — let `useAsync` drop it
    // rather than rendering an error the user did not cause.
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(
      "Cannot reach DocuMind",
      "The browser could not reach this app's API. Check your connection and retry.",
      "ERR_NETWORK",
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      error?: string;
      detail?: string;
      code?: string;
      retryable?: boolean;
    } | null;

    throw new ApiError(
      body?.error ?? "Something went wrong",
      body?.detail ?? `The request failed with ${response.status}.`,
      body?.code ?? "ERR_UNKNOWN",
      body?.retryable ?? response.status >= 500,
    );
  }

  return (await response.json()) as T;
}

/**
 * The simulation switch, kept for the state-gallery controls on each screen.
 *
 * It short-circuits *before* the network: these are UI states being previewed,
 * never claims about what a service returned. `"ok"` always goes to the real
 * API.
 */
function simulatedFailure(simulate: Simulate, message: [string, string, string]): void {
  if (simulate !== "error") return;
  throw new ApiError(message[0], message[1], message[2]);
}

async function simulatedDelay(simulate: Simulate, signal?: AbortSignal): Promise<void> {
  if (simulate === "slow") await sleep(3400, signal);
}

/* -- Auth --------------------------------------------------------------- */
/* UNBACKED: api-gateway owns `POST /auth/login` and has not been built. This
 * block is the only remaining fabricated data path in the app. */

export type Session = { email: string; name: string; initials: string };

let attemptsRemaining = 3;
/** Demo lockouts clear on their own so the sign-in page stays explorable. */
const LOCKOUT_MS = 20_000;

export type SignInResult =
  | { ok: true; session: Session }
  | { ok: false; title: string; detail: string; lockedOut: boolean };

export async function signIn(email: string, password: string): Promise<SignInResult> {
  await sleep(1100);

  if (attemptsRemaining <= 0) {
    return {
      ok: false,
      lockedOut: true,
      title: "Account temporarily locked",
      detail:
        "Too many failed attempts. The lock clears automatically in 20 seconds, or reset your password.",
    };
  }

  if (email.trim().toLowerCase() === DEMO_CREDENTIALS.email && password === DEMO_CREDENTIALS.password) {
    attemptsRemaining = 3;
    return { ok: true, session: { email, name: "Rowan Nakamura", initials: "RN" } };
  }

  attemptsRemaining -= 1;
  if (attemptsRemaining <= 0) {
    setTimeout(() => {
      attemptsRemaining = 3;
    }, LOCKOUT_MS);
    return {
      ok: false,
      lockedOut: true,
      title: "Account temporarily locked",
      detail:
        "Too many failed attempts. The lock clears automatically in 20 seconds, or reset your password.",
    };
  }
  return {
    ok: false,
    lockedOut: false,
    title: "Invalid email or password",
    detail: `${attemptsRemaining} attempt${attemptsRemaining === 1 ? "" : "s"} remaining before lockout.`,
  };
}

/* -- Registration ------------------------------------------------------- */
/* UNBACKED: same gateway gap as sign-in. */

export type SignUpInput = {
  name: string;
  email: string;
  org: string;
  password: string;
};

export type SignUpResult =
  | { ok: true; email: string; verificationSentTo: string }
  | { ok: false; field: "email" | "password" | "org" | null; title: string; detail: string };

/** Addresses treated as already registered, to exercise the conflict path. */
const TAKEN_EMAILS = [DEMO_CREDENTIALS.email, "admin@meridian.com", "rowan@meridian.com"];

/** Passwords rejected server-side even though they pass the client rules. */
const BREACHED_PASSWORDS = ["password123", "documind123", "letmein123", "qwerty12345"];

export async function signUp(input: SignUpInput): Promise<SignUpResult> {
  await sleep(1500);

  if (TAKEN_EMAILS.includes(input.email.trim().toLowerCase())) {
    return {
      ok: false,
      field: "email",
      title: "That email already has an account",
      detail:
        "Sign in instead, or use a different address. Password resets go to the original inbox.",
    };
  }

  if (BREACHED_PASSWORDS.includes(input.password.toLowerCase())) {
    return {
      ok: false,
      field: "password",
      title: "This password has appeared in a breach",
      detail:
        "It passes the length rules but is on a known-compromised list. Choose something unique to DocuMind.",
    };
  }

  if (input.org.trim().length < 2) {
    return {
      ok: false,
      field: "org",
      title: "Workspace name is too short",
      detail: "Use the name your team will recognise — it appears on every exported report.",
    };
  }

  return { ok: true, email: input.email, verificationSentTo: input.email };
}

export async function resendVerification(email: string): Promise<{ ok: boolean }> {
  await sleep(1200);
  return { ok: !email.endsWith("@example.com") };
}

/* -- Service health ------------------------------------------------------ */

export type ServiceHealth = {
  service: string;
  state: "ready" | "degraded" | "unreachable";
  detail: string;
  checks?: Record<string, string>;
};

export type HealthReport = {
  status: "ready" | "degraded";
  services: ServiceHealth[];
  checkedAt: string;
};

/** Live readiness of document-service and search-service. */
export function getHealth(signal?: AbortSignal): Promise<HealthReport> {
  return request<HealthReport>("/api/health", { signal });
}

/* -- Dashboard ---------------------------------------------------------- */

export async function getDashboard(
  range: DateRange,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<Dashboard> {
  const simulate = opts.simulate ?? "ok";
  await simulatedDelay(simulate, opts.signal);
  simulatedFailure(simulate, [
    "Dashboard unavailable",
    "The document library did not respond, so no metric could be computed. Processing is unaffected.",
    "ERR_ANALYTICS_UNAVAILABLE",
  ]);

  const dashboard = await request<Dashboard>(`/api/dashboard?range=${range}`, {
    signal: opts.signal,
  });

  // `empty` and `partial` preview real response shapes rather than substituting
  // different data, so what the gallery shows is what the API can actually send.
  if (simulate === "empty") {
    return {
      ...dashboard,
      kpis: dashboard.kpis.map((k) => ({ ...k, value: "0", unit: undefined, delta: undefined, footnote: "no documents in this period" })),
      flagged: [],
      exceptions: [],
      gauge: { pct: 0, target: "No documents scored yet", legend: dashboard.gauge.legend.map((l) => ({ ...l, value: 0 })) },
      series: [],
      volume: 0,
    };
  }
  if (simulate === "partial") {
    return {
      ...dashboard,
      exceptions: [],
      degraded: {
        panel: "Top exception types",
        message: "The exception breakdown could not be computed. Every other panel is current.",
      },
    };
  }

  return dashboard;
}

/* -- Documents ---------------------------------------------------------- */

export type DocumentQuery = {
  search?: string;
  type?: DocType | "All";
  status?: DocumentSummary["status"] | "All";
  sort?: { key: SortKey; dir: "asc" | "desc" };
  page?: number;
  pageSize?: number;
};

export type SortKey = "name" | "type" | "status" | "risk" | "pages" | "uploadedAt";

export type DocumentPage = {
  rows: DocumentSummary[];
  total: number;
  /** Total before search/filters — lets the UI tell "empty" from "no results". */
  unfilteredTotal: number;
  page: number;
  pageSize: number;
  pageCount: number;
};

const EMPTY_PAGE: DocumentPage = {
  rows: [],
  total: 0,
  unfilteredTotal: 0,
  page: 1,
  pageSize: 10,
  pageCount: 1,
};

export async function listDocuments(
  query: DocumentQuery = {},
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<DocumentPage> {
  const simulate = opts.simulate ?? "ok";
  await simulatedDelay(simulate, opts.signal);
  simulatedFailure(simulate, [
    "Could not load documents",
    "The document service did not respond. Your documents are safe — this view will recover on retry.",
    "ERR_INDEX_UNAVAILABLE",
  ]);
  if (simulate === "empty") return { ...EMPTY_PAGE, pageSize: query.pageSize ?? 10 };

  const params = new URLSearchParams();
  if (query.search?.trim()) params.set("search", query.search.trim());
  if (query.type && query.type !== "All") params.set("type", query.type);
  if (query.status && query.status !== "All") params.set("status", query.status);
  if (query.sort) {
    params.set("sort", query.sort.key);
    params.set("dir", query.sort.dir);
  }
  params.set("page", String(query.page ?? 1));
  params.set("pageSize", String(query.pageSize ?? 10));

  return request<DocumentPage>(`/api/documents?${params}`, { signal: opts.signal });
}

export async function getDocument(
  id: string,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<DocumentDetail> {
  const simulate = opts.simulate ?? "ok";
  await simulatedDelay(simulate, opts.signal);
  simulatedFailure(simulate, [
    "Could not load this document",
    "The document service failed while fetching this record. The document itself is safe — only this view failed to load.",
    "ERR_DETAIL_UNAVAILABLE",
  ]);

  return request<DocumentDetail>(`/api/documents/${encodeURIComponent(id)}`, {
    signal: opts.signal,
  });
}

export type DocumentStatus = {
  id: string;
  status: DocumentSummary["status"];
  risk: number | null;
  verdict: DocumentSummary["verdict"];
  progress?: { step: number; pct: number } | null;
  error?: DocError | null;
};

/**
 * The cheap poll for a document still in the pipeline.
 *
 * Screens watching a processing document call this on an interval instead of
 * re-fetching the full detail payload every couple of seconds.
 */
export function getDocumentStatus(id: string, signal?: AbortSignal): Promise<DocumentStatus> {
  return request<DocumentStatus>(`/api/documents/${encodeURIComponent(id)}/status`, { signal });
}

export type DocumentCounts = {
  total: number;
  queued: number;
  processing: number;
  completed: number;
  failed: number;
  inFlight: number;
};

/** Library counts by lifecycle state — what the nav badges show. */
export function getDocumentCounts(signal?: AbortSignal): Promise<DocumentCounts> {
  return request<DocumentCounts>("/api/documents/counts", { signal });
}

/* -- Bulk actions -------------------------------------------------------- */

export type BulkResult = {
  requested: number;
  succeeded: string[];
  failed: { id: string; name: string; reason: string }[];
};

/**
 * UNBACKED: document-service defines the request and result schemas for bulk
 * reprocess and delete (`BulkRequestSchema` / `BulkResultSchema`) but exposes
 * no route for either.
 *
 * These report every id as failed with the real reason rather than pretending
 * to succeed: a fake success would show the row changing state and then snap
 * back on the next poll, which is worse than being told it is unavailable. The
 * UI already renders per-id failure reasons, so this needs no special casing.
 */
function unsupported(ids: string[], rows: DocumentSummary[], reason: string): BulkResult {
  const nameOf = (id: string) => rows.find((r) => r.id === id)?.name ?? id;
  return {
    requested: ids.length,
    succeeded: [],
    failed: ids.map((id) => ({ id, name: nameOf(id), reason })),
  };
}

export async function reprocessDocuments(ids: string[]): Promise<BulkResult> {
  const { rows } = await listDocuments({ pageSize: 100 });
  return unsupported(
    ids,
    rows,
    "Reprocessing is not available yet — document-service exposes no reprocess route.",
  );
}

export async function deleteDocuments(ids: string[]): Promise<BulkResult> {
  const { rows } = await listDocuments({ pageSize: 100 });
  return unsupported(
    ids,
    rows,
    "Deleting is not available yet — document-service exposes no delete route.",
  );
}

/* -- Exports ------------------------------------------------------------- */

export type ExportFile = { filename: string; rows: number; csv: string };

const DOCUMENT_COLUMNS: [string, (d: DocumentSummary) => string | number][] = [
  ["id", (d) => d.id],
  ["name", (d) => d.name],
  ["type", (d) => d.type],
  ["status", (d) => d.status],
  ["risk", (d) => d.risk ?? ""],
  ["verdict", (d) => d.verdict],
  ["pages", (d) => d.pages],
  ["size_mb", (d) => d.sizeMb],
  ["counterparty", (d) => d.counterparty],
  ["uploaded_at", (d) => new Date(d.uploadedAt).toISOString()],
];

/**
 * Builds the CSV from real rows.
 *
 * Export is legitimately a frontend job here — every column is already in the
 * document payload, so round-tripping to a service to reformat data the client
 * holds would add a failure mode and no information.
 */
export async function exportDocuments(ids: string[] | "all"): Promise<ExportFile> {
  const { rows } = await listDocuments({ pageSize: 100 });
  const selected = ids === "all" ? rows : rows.filter((r) => ids.includes(r.id));
  return {
    filename: `documind-documents-${selected.length}.csv`,
    rows: selected.length,
    csv: toCsv(DOCUMENT_COLUMNS.map(([h]) => h), selected.map((d) => DOCUMENT_COLUMNS.map(([, get]) => get(d)))),
  };
}

/** The dashboard export — the same KPI values the screen is showing. */
export async function exportReport(range: DateRange): Promise<ExportFile> {
  const dashboard = await getDashboard(range);
  return {
    filename: `documind-report-${range}.csv`,
    rows: dashboard.kpis.length,
    csv: toCsv(
      ["metric", "value", "change", "basis"],
      dashboard.kpis.map((k) => [k.label, k.value + (k.unit ?? ""), k.delta ?? "", k.footnote]),
    ),
  };
}

function toCsv(headers: string[], rows: (string | number)[][]): string {
  const cell = (v: string | number) => {
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [headers.join(","), ...rows.map((r) => r.map(cell).join(","))].join("\n");
}

/* -- Upload ------------------------------------------------------------- */

export type ValidationResult = { ok: true } | { ok: false; reason: string };

/**
 * Mirrors what document-service will actually accept, so a file that cannot
 * possibly succeed is rejected before it is uploaded rather than after.
 */
export function validateFile(name: string, sizeMb: number): ValidationResult {
  const ext = (name.split(".").pop() ?? "").toLowerCase();
  if (!UPLOAD_LIMITS.extensions.includes(ext)) {
    return {
      ok: false,
      reason: `.${ext || "unknown"} is not supported — upload ${UPLOAD_LIMITS.extensions.join(", ")}.`,
    };
  }
  if (sizeMb > UPLOAD_LIMITS.maxMb) {
    return { ok: false, reason: `${sizeMb.toFixed(1)} MB exceeds the ${UPLOAD_LIMITS.maxMb} MB per-file limit.` };
  }
  return { ok: true };
}

/**
 * Uploads one file and returns the document document-service created.
 *
 * `XMLHttpRequest` rather than `fetch`, because it is the only API that
 * reports upload progress — and a progress bar that reflects bytes actually
 * sent is the whole point of the panel this feeds. The response is a *queued*
 * document: the file is stored and a job is on the Redis stream, but nothing
 * has been classified, extracted or scored. Callers follow it with
 * `getDocumentStatus`.
 */
export function uploadDocument(
  file: File,
  opts: { onProgress?: (pct: number) => void; signal?: AbortSignal } = {},
): Promise<DocumentSummary> {
  return new Promise((resolve, reject) => {
    const body = new FormData();
    body.append("file", file, file.name);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/documents");
    xhr.responseType = "json";

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) opts.onProgress?.(Math.round((e.loaded / e.total) * 100));
    });

    xhr.addEventListener("load", () => {
      const payload = xhr.response as Record<string, unknown> | null;

      if (xhr.status >= 200 && xhr.status < 300) {
        // A new document changes what the palette and the scope counts can see.
        invalidateCorpus();
        invalidateLibrary();
        resolve(payload as unknown as DocumentSummary);
        return;
      }

      reject(
        new ApiError(
          (payload?.error as string) ?? "Upload failed",
          (payload?.detail as string) ?? `The upload failed with ${xhr.status}.`,
          (payload?.code as string) ?? "ERR_UPLOAD_FAILED",
          (payload?.retryable as boolean) ?? xhr.status >= 500,
        ),
      );
    });

    xhr.addEventListener("error", () =>
      reject(
        new ApiError(
          "Cannot reach DocuMind",
          "The browser could not reach this app's API while uploading. Check your connection and retry.",
          "ERR_NETWORK",
        ),
      ),
    );

    xhr.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    opts.signal?.addEventListener("abort", () => xhr.abort());

    xhr.send(body);
  });
}

/* -- Q&A ---------------------------------------------------------------- */

export type QaAnswer = {
  text: string;
  citations: string[];
  thinking: string;
};

/**
 * Per-document Q&A.
 *
 * Both halves are real now: search-service ranks the passages and ai-service
 * writes the answer from them. Two calls rather than one because ai-service
 * deliberately does not retrieve — that boundary is what lets retrieval
 * quality and answer quality be measured separately.
 *
 * Null means there is genuinely no answer: either retrieval returned nothing,
 * or ai-service refused because the passages do not support one. Neither is an
 * error, and the UI renders both as its no-answer state.
 *
 * UNBACKED: the fallback to `answerFor` covers the reader fixtures, which are
 * the only text the reader has until processing-service extracts real pages.
 */
export async function askDocument(
  question: string,
  opts: { simulate?: Simulate; signal?: AbortSignal; documentId?: string } = {},
): Promise<QaAnswer | null> {
  const simulate = opts.simulate ?? "ok";
  await simulatedDelay(simulate, opts.signal);
  simulatedFailure(simulate, [
    "Answer generation failed",
    "The retrieval service returned an error before any passages were ranked. Nothing was charged — retry the question.",
    "ERR_QA_UPSTREAM",
  ]);

  const passages = await retrieve(question, { documentId: opts.documentId, signal: opts.signal });
  if (passages.length > 0) {
    const generated = await generate(question, passages, opts.signal);
    if (generated?.refused) return null;

    return {
      text: generated ? generated.text : passages.map((p) => p.text).join("\n\n"),
      // Chunk ids either way, so the reader resolves a citation the same
      // whether ai-service chose the subset or generation was unavailable and
      // we fell back to every retrieved passage.
      citations: generated
        ? generated.citations.map((c) => c.chunkId)
        : passages.map((p) => p.chunkId),
      thinking: generated
        ? `Answered from ${generated.citations.length} of ${passages.length} ranked passages`
        : `Ranked ${passages.length} passages from this document`,
    };
  }

  const fixture = answerFor(question);
  return fixture
    ? { text: fixture.text, citations: fixture.citations, thinking: fixture.thinking }
    : null;
}

/* -- Retrieval ----------------------------------------------------------- */

export type Passage = {
  chunkId: string;
  documentId: string;
  text: string;
  page: number | null;
  similarity: number;
};

/** Ranked passages from search-service, optionally narrowed to one document. */
export async function retrieve(
  question: string,
  opts: { documentId?: string; topK?: number; signal?: AbortSignal } = {},
): Promise<Passage[]> {
  const params = new URLSearchParams({ q: question });
  if (opts.documentId) params.set("documentId", opts.documentId);
  if (opts.topK) params.set("topK", String(opts.topK));

  const { passages } = await request<{ passages: Passage[] }>(`/api/search?${params}`, {
    signal: opts.signal,
  });
  return passages;
}

/* -- Generation ---------------------------------------------------------- */

export type GeneratedAnswer = {
  text: string;
  citations: { chunkId: string; documentId: string | null; page: number | null; snippet: string }[];
  /** True when every citation marker resolved to a passage we supplied. */
  grounded: boolean;
  /** ai-service saying the passages do not answer the question. */
  refused: boolean;
  confidence: number;
  model: string | null;
};

/**
 * Turns retrieved passages into a written, cited answer via ai-service.
 *
 * Returns null when ai-service cannot be reached, which is a deliberate soft
 * failure: retrieval already succeeded, so the caller can still show the user
 * the passages that matched rather than an error for a question that was
 * answered. A refusal is not a failure and comes back as `refused: true`.
 */
async function generate(
  question: string,
  passages: Passage[],
  signal?: AbortSignal,
): Promise<GeneratedAnswer | null> {
  try {
    return await request<GeneratedAnswer>("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, passages }),
      signal,
    });
  } catch (cause) {
    // The caller navigated away — not something to paper over with passages.
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    return null;
  }
}

/* -- Workspace Q&A ------------------------------------------------------ */

export type WorkspaceAnswer = {
  text: string;
  citations: WorkspaceCitation[];
  thinking: string;
  searched: number;
};

/**
 * Workspace-wide Q&A over the real vector index.
 *
 * Retrieval is scoped here rather than upstream: search-service has no
 * document-type filter, so a scoped question keeps only the hits that landed
 * in a document the user asked about, and only those passages are sent to
 * ai-service to be written up.
 *
 * Null means there is genuinely no answer — an empty index, no passage above
 * the similarity floor, nothing inside the scope, or ai-service refusing
 * because the passages do not support one. None of those is an error, and the
 * UI renders them all as "no answer".
 */
export async function askWorkspace(
  question: string,
  scope: ChatScope,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<WorkspaceAnswer | null> {
  const simulate = opts.simulate ?? "ok";
  await simulatedDelay(simulate, opts.signal);
  simulatedFailure(simulate, [
    "Answer generation failed",
    "The retrieval service returned an error before any passages were ranked. Nothing was charged — retry the question.",
    "ERR_RAG_UPSTREAM",
  ]);
  if (simulate === "empty") return null;

  const library = await loadLibrary(opts.signal);
  const inScope = scope === "All" ? library : library.filter((d) => d.type === scope);
  if (inScope.length === 0) return null;

  const passages = await retrieve(question, { topK: 8, signal: opts.signal });
  const byId = new Map(inScope.map((d) => [d.id, d]));

  // Retrieval has no scope filter, so a scoped question keeps only the hits
  // that landed in a document the user actually asked about.
  const citations: WorkspaceCitation[] = [];
  for (const p of passages) {
    const doc = byId.get(p.documentId);
    if (!doc) continue;
    citations.push({
      id: p.chunkId,
      docId: doc.id,
      docName: doc.name,
      docType: doc.type,
      page: p.page ?? 1,
      context: p.page ? `page ${p.page}` : "matched passage",
      snippet: p.text,
    });
  }

  if (citations.length === 0) return null;

  // Only the in-scope passages are worth paying to generate over, so the
  // filtered set — not everything retrieval returned — is what gets sent.
  const inScopeIds = new Set(citations.map((c) => c.id));
  const generated = await generate(
    question,
    passages.filter((p) => inScopeIds.has(p.chunkId)),
    opts.signal,
  );
  if (generated?.refused) return null;

  return {
    // Falls back to the retrieved passages verbatim when ai-service is
    // unreachable: extractive is worse than a written answer, but it is still
    // the document's own words rather than nothing.
    text: generated ? generated.text : citations.map((c) => c.snippet).join("\n\n"),
    // The cited subset when ai-service picked one, so the sources panel shows
    // what the answer actually leans on.
    citations: generated
      ? citations.filter((c) => generated.citations.some((g) => g.chunkId === c.id))
      : citations,
    thinking: generated
      ? `Answered from ${generated.citations.length} of ${citations.length} in-scope passages across ${inScope.length} documents`
      : `Ranked ${passages.length} passages across ${inScope.length} documents`,
    searched: inScope.length,
  };
}

/** The blocks that make up one page of the document reader.
 *  UNBACKED: extracted page text needs processing-service. */
export function getPage(page: number): SourceBlock[] {
  return QA_PAGES[page] ?? QA_FALLBACK;
}

/* -- Library cache ------------------------------------------------------- */

/**
 * The document list, cached briefly for the callers that need the whole
 * library rather than a page of it — the command palette and the chat scope
 * counter, both of which run on every keystroke.
 */
const LIBRARY_TTL_MS = 20_000;

let libraryCache: { at: number; rows: DocumentSummary[] } | null = null;
let libraryInFlight: Promise<DocumentSummary[]> | null = null;

export function invalidateLibrary(): void {
  libraryCache = null;
  libraryInFlight = null;
}

async function loadLibrary(signal?: AbortSignal): Promise<DocumentSummary[]> {
  if (libraryCache && Date.now() - libraryCache.at < LIBRARY_TTL_MS) return libraryCache.rows;
  // Coalesce concurrent callers — the palette and the scope counter otherwise
  // issue the same request twice on the same keystroke.
  if (libraryInFlight) return libraryInFlight;

  libraryInFlight = listDocuments({ pageSize: 100, sort: { key: "uploadedAt", dir: "desc" } }, { signal })
    .then(({ rows }) => {
      libraryCache = { at: Date.now(), rows };
      libraryInFlight = null;
      return rows;
    })
    .catch((e) => {
      libraryInFlight = null;
      throw e;
    });

  return libraryInFlight;
}

/** How many documents a scope covers — shown before and after a question. */
export async function scopeSize(scope: ChatScope, signal?: AbortSignal): Promise<number> {
  const rows = await loadLibrary(signal);
  return scope === "All" ? rows.length : rows.filter((d) => d.type === scope).length;
}

/* -- Global search ------------------------------------------------------- */

/**
 * The one entry point for the command palette.
 *
 * The index is built from the real document library and cached behind this
 * seam, never in a component: the caller sends a query string and receives
 * only the ranked page of hits it is about to render.
 *
 * Latency is kept low deliberately: search is typed-into, so it has to feel
 * like a local index — which, for everything except the document list fetch
 * behind `loadLibrary`, it is.
 */

/** Trimmed per group so no single kind can crowd out the others. */
const GROUP_CAP: Record<SearchKind, number> = {
  page: 4,
  document: 6,
  section: 5,
  finding: 4,
  field: 4,
};

const TOTAL_CAP = 20;

export async function searchWorkspace(
  query: string,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<SearchResponse> {
  const started = Date.now();
  const simulate = opts.simulate ?? "ok";

  await simulatedDelay(simulate, opts.signal);
  simulatedFailure(simulate, [
    "Search is unavailable",
    "The document library did not respond. Your documents are unaffected — this view will recover on retry.",
    "ERR_SEARCH_UNAVAILABLE",
  ]);

  const q = query.trim();
  const source = simulate === "empty" ? [] : await loadLibrary(opts.signal);

  // No query: offer destinations and what changed most recently, rather than
  // an empty box the user has to guess their way out of.
  if (q === "") {
    const entries = suggestions(source);
    return {
      query: "",
      groups: groupHits(
        entries.map((e) => ({ entry: e, score: e.weight ?? 0 })),
        [],
      ),
      total: entries.length,
      tookMs: Date.now() - started,
      suggested: true,
    };
  }

  const terms = tokenize(q);
  const scored: { entry: Indexed; score: number }[] = [];

  for (const entry of corpus(source)) {
    const score = scoreEntry(entry, terms);
    if (score > 0) scored.push({ entry, score });
  }

  scored.sort((a, b) => b.score - a.score || a.entry.title.localeCompare(b.entry.title));

  return {
    query: q,
    groups: groupHits(scored, terms),
    total: scored.length,
    tookMs: Date.now() - started,
    suggested: false,
  };
}

/** Buckets by kind in display order, deduping, then capping each and the whole. */
function groupHits(scored: { entry: Indexed; score: number }[], terms: string[]): SearchGroup[] {
  const byKind = new Map<SearchKind, { entry: Indexed; score: number; also: number }[]>();
  // Findings and fields come from analysis shared across documents, so the same
  // title legitimately appears many times. Showing it once with a count reads
  // as a finding about the corpus; showing it eight times reads as a broken
  // palette. `scored` is already sorted, so the first is the best.
  const collapsed = new Map<string, { entry: Indexed; score: number; also: number }>();

  for (const s of scored) {
    const collapsible = s.entry.kind === "finding" || s.entry.kind === "field";
    const key = collapsible ? `${s.entry.kind}:${s.entry.lc.title}` : s.entry.id;

    const seen = collapsed.get(key);
    if (seen) {
      seen.also += 1;
      continue;
    }
    const row = { entry: s.entry, score: s.score, also: 0 };
    collapsed.set(key, row);

    const list = byKind.get(s.entry.kind);
    if (list) list.push(row);
    else byKind.set(s.entry.kind, [row]);
  }

  const groups: SearchGroup[] = [];
  let budget = TOTAL_CAP;

  for (const kind of KIND_ORDER) {
    const list = byKind.get(kind);
    if (!list || list.length === 0 || budget <= 0) continue;

    const take = Math.min(GROUP_CAP[kind], list.length, budget);
    budget -= take;

    groups.push({
      kind,
      label: KIND_LABEL[kind],
      more: list.length - take,
      hits: list.slice(0, take).map(({ entry, score, also }) => ({
        id: entry.id,
        kind: entry.kind,
        title: entry.title,
        subtitle: entry.subtitle,
        snippet: bodySnippet(entry, terms),
        meta: entry.meta,
        tone: entry.tone,
        href: entry.href,
        also: also || undefined,
        score,
      })),
    });
  }

  return groups;
}

/**
 * Only attach a snippet when the body is what matched — repeating a clause
 * under a title the user already matched on is noise, not context.
 */
function bodySnippet(entry: Indexed, terms: string[]): string | undefined {
  if (!entry.body || terms.length === 0) return undefined;
  const inBody = terms.some((t) => entry.lc.body.includes(t));
  if (!inBody) return undefined;
  return snippetAround(entry.body, terms);
}
