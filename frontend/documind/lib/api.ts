import {
  DEMO_CREDENTIALS,
  DOCUMENTS,
  EMPTY_DASHBOARD,
  QA_PAGES,
  QA_FALLBACK,
  UPLOAD_LIMITS,
  answerFor,
  buildDashboard,
  chatAnswerFor,
  buildDetail,
  degradedDashboard,
  hash,
  mockError,
} from "@/lib/mock/data";
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
 * render, so replacing a body with `fetch("/api/…")` is a local change — no
 * component has to move. The `simulate` option exists only so the mock can be
 * driven into its failure/empty states from the UI; drop it when the real
 * services land.
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

const BASE_LATENCY = 620;

export function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });
}

async function latency(simulate: Simulate, signal?: AbortSignal) {
  await sleep(simulate === "slow" ? 3400 : BASE_LATENCY + Math.random() * 380, signal);
}

function fail(simulate: Simulate, message: [string, string, string?]): void {
  if (simulate !== "error") return;
  throw new ApiError(message[0], message[1], message[2]);
}

/* -- Auth --------------------------------------------------------------- */

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
      detail: "Too many failed attempts. The lock clears automatically in 20 seconds, or reset your password.",
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
      detail: "Too many failed attempts. The lock clears automatically in 20 seconds, or reset your password.",
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

export type SignUpInput = {
  name: string;
  email: string;
  org: string;
  password: string;
};

export type SignUpResult =
  | { ok: true; email: string; verificationSentTo: string }
  | { ok: false; field: "email" | "password" | "org" | null; title: string; detail: string };

/** Addresses the mock treats as already registered, to exercise the conflict. */
const TAKEN_EMAILS = [DEMO_CREDENTIALS.email, "admin@meridian.com", "rowan@meridian.com"];

/** Passwords the mock rejects server-side even though they pass the client rules. */
const BREACHED_PASSWORDS = ["password123", "documind123", "letmein123", "qwerty12345"];

export async function signUp(input: SignUpInput): Promise<SignUpResult> {
  await sleep(1500);

  if (TAKEN_EMAILS.includes(input.email.trim().toLowerCase())) {
    return {
      ok: false,
      field: "email",
      title: "That email already has an account",
      detail: "Sign in instead, or use a different address. Password resets go to the original inbox.",
    };
  }

  if (BREACHED_PASSWORDS.includes(input.password.toLowerCase())) {
    return {
      ok: false,
      field: "password",
      title: "This password has appeared in a breach",
      detail: "It passes the length rules but is on a known-compromised list. Choose something unique to DocuMind.",
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

/* -- Dashboard ---------------------------------------------------------- */

export async function getDashboard(
  range: DateRange,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<Dashboard> {
  const simulate = opts.simulate ?? "ok";
  await latency(simulate, opts.signal);
  fail(simulate, [
    "Analytics service unavailable",
    "The metrics warehouse did not respond within 10s. Document processing is unaffected — only this dashboard is stale.",
    "ERR_ANALYTICS_TIMEOUT",
  ]);
  if (simulate === "empty") return EMPTY_DASHBOARD;
  if (simulate === "partial") return degradedDashboard(range);
  return buildDashboard(range);
}

export async function exportReport(range: DateRange): Promise<{ filename: string; rows: number }> {
  await sleep(1800);
  const d = buildDashboard(range);
  return { filename: `documind-report-${range}.csv`, rows: Number(d.kpis[0].value.replace(/,/g, "")) };
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

/** Mutable copy so local actions (delete, reprocess) survive re-queries. */
let documents: DocumentSummary[] = DOCUMENTS.map((d) => ({ ...d }));

export async function listDocuments(
  query: DocumentQuery = {},
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<DocumentPage> {
  const simulate = opts.simulate ?? "ok";
  await latency(simulate, opts.signal);
  fail(simulate, [
    "Could not load documents",
    "The document index returned 503. This is usually transient — retrying normally succeeds within a few seconds.",
    "ERR_INDEX_UNAVAILABLE",
  ]);

  const source = simulate === "empty" ? [] : documents;
  const { search = "", type = "All", status = "All", page = 1, pageSize = 10 } = query;
  const q = search.trim().toLowerCase();

  let rows = source.filter(
    (d) =>
      (type === "All" || d.type === type) &&
      (status === "All" || d.status === status) &&
      (q === "" ||
        d.name.toLowerCase().includes(q) ||
        d.id.toLowerCase().includes(q) ||
        d.counterparty.toLowerCase().includes(q)),
  );

  if (query.sort) {
    const { key, dir } = query.sort;
    const sign = dir === "asc" ? 1 : -1;
    rows = [...rows].sort((a, b) => {
      const av = a[key] ?? -1;
      const bv = b[key] ?? -1;
      if (typeof av === "string" && typeof bv === "string") return sign * av.localeCompare(bv);
      return sign * (Number(av) - Number(bv));
    });
  }

  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(page, pageCount);

  return {
    rows: rows.slice((safePage - 1) * pageSize, safePage * pageSize),
    total: rows.length,
    unfilteredTotal: source.length,
    page: safePage,
    pageSize,
    pageCount,
  };
}

export async function getDocument(
  id: string,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<DocumentDetail> {
  const simulate = opts.simulate ?? "ok";
  await latency(simulate, opts.signal);
  fail(simulate, [
    "Could not load this document",
    "The extraction store returned 502 while fetching the analysis. The document itself is safe — only this view failed to load.",
    "ERR_DETAIL_UNAVAILABLE",
  ]);

  const doc = documents.find((d) => d.id === id);
  if (!doc) throw new ApiError("Document not found", `No document matches ${id}. It may have been deleted.`, "ERR_NOT_FOUND", false);
  return buildDetail(doc);
}

export type BulkResult = {
  requested: number;
  succeeded: string[];
  failed: { id: string; name: string; reason: string }[];
};

export async function reprocessDocuments(ids: string[]): Promise<BulkResult> {
  await sleep(1400);
  const succeeded: string[] = [];
  const failed: BulkResult["failed"] = [];

  for (const id of ids) {
    const doc = documents.find((d) => d.id === id);
    if (!doc) continue;
    // Encrypted documents can never be reprocessed — that drives partial success.
    if (doc.error && !doc.error.retryable) {
      failed.push({ id, name: doc.name, reason: "Password protected — remove the restriction and re-upload." });
      continue;
    }
    doc.status = "processing";
    doc.error = undefined;
    doc.risk = null;
    doc.verdict = "Pending";
    doc.progress = { step: 2, pct: 10 };
    succeeded.push(id);
  }

  return { requested: ids.length, succeeded, failed };
}

export async function deleteDocuments(ids: string[]): Promise<BulkResult> {
  await sleep(1100);
  const succeeded: string[] = [];
  const failed: BulkResult["failed"] = [];

  for (const id of ids) {
    const doc = documents.find((d) => d.id === id);
    if (!doc) continue;
    if (doc.status === "processing") {
      failed.push({ id, name: doc.name, reason: "Still processing — cancel the job before deleting." });
      continue;
    }
    succeeded.push(id);
  }

  documents = documents.filter((d) => !succeeded.includes(d.id));
  return { requested: ids.length, succeeded, failed };
}

export async function exportDocuments(ids: string[] | "all"): Promise<{ filename: string; rows: number }> {
  await sleep(1500);
  const rows = ids === "all" ? documents.length : ids.length;
  return { filename: `documind-documents-${rows}.csv`, rows };
}

/** Advance one processing document — drives the live-progress ticker. */
export function tickProcessing(): void {
  for (const doc of documents) {
    if (doc.status !== "processing" || !doc.progress) continue;
    const next = doc.progress.pct + 9;
    if (next < 100) {
      doc.progress = { ...doc.progress, pct: next };
    } else if (doc.progress.step < 7) {
      doc.progress = { step: doc.progress.step + 1, pct: 0 };
    } else {
      doc.status = "completed";
      doc.risk = hash(doc.id) % 100;
      doc.verdict = doc.risk >= 60 ? "Needs review" : "Auto-approved";
      doc.flags = Math.max(0, Math.round(doc.risk / 24));
      doc.progress = undefined;
    }
  }
}

/* -- Upload ------------------------------------------------------------- */

export type ValidationResult = { ok: true } | { ok: false; reason: string };

export function validateFile(name: string, sizeMb: number): ValidationResult {
  const ext = (name.split(".").pop() ?? "").toLowerCase();
  if (!UPLOAD_LIMITS.extensions.includes(ext)) {
    return { ok: false, reason: `.${ext || "unknown"} is not supported — upload ${UPLOAD_LIMITS.extensions.join(", ")}.` };
  }
  if (sizeMb > UPLOAD_LIMITS.maxMb) {
    return { ok: false, reason: `${sizeMb.toFixed(1)} MB exceeds the ${UPLOAD_LIMITS.maxMb} MB per-file limit.` };
  }
  return { ok: true };
}

export function classifyByName(name: string): DocType {
  const n = name.toLowerCase();
  if (n.includes("inv")) return "Invoice";
  if (n.includes("amend")) return "Amendment";
  if (n.includes("statement")) return "Statement";
  return "Contract";
}

/**
 * Decides whether a simulated pipeline run fails, and where. Real code replaces
 * this with the status coming back from the job API.
 */
export function pipelineOutcome(
  name: string,
  attempt: number,
  forceFail: boolean,
): { failAtStep: number; error: DocError } | null {
  const seed = hash(name + attempt);
  const shouldFail = forceFail || (attempt === 0 && seed % 5 === 0);
  if (!shouldFail) return null;
  const kinds = ["no_text_layer", "timeout", "classify"] as const;
  return { failAtStep: 3 + (seed % 3), error: mockError(kinds[seed % kinds.length], seed % 97) };
}

/** Registers a finished upload so it shows up in the documents list. */
export function commitUpload(name: string, sizeMb: number, type: DocType): DocumentSummary {
  const seed = hash(name + Date.now());
  const risk = seed % 100;
  const doc: DocumentSummary = {
    id: `doc_${(seed >>> 4).toString(16).padStart(8, "0").slice(0, 8)}`,
    name,
    ext: (name.split(".").pop() ?? "pdf").toUpperCase(),
    type,
    status: "completed",
    risk,
    pages: 3 + (seed % 40),
    sizeMb,
    counterparty: "Unassigned counterparty",
    uploaded: "Aug 25, 10:12",
    uploadedAt: Date.now(),
    time: "just now",
    flags: Math.max(0, Math.round(risk / 24)),
    verdict: risk >= 60 ? "Needs review" : "Auto-approved",
  };
  documents = [doc, ...documents];
  return doc;
}

/* -- Q&A ---------------------------------------------------------------- */

export type QaAnswer = {
  text: string;
  citations: string[];
  thinking: string;
};

export async function askDocument(
  question: string,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<QaAnswer | null> {
  const simulate = opts.simulate ?? "ok";
  await sleep(simulate === "slow" ? 2600 : 900, opts.signal);
  fail(simulate, [
    "Answer generation failed",
    "The retrieval service returned 500 before any tokens were produced. Nothing was charged — retry the question.",
    "ERR_QA_UPSTREAM",
  ]);
  const a = answerFor(question);
  return a ? { text: a.text, citations: a.citations, thinking: a.thinking } : null;
}

/* -- Workspace Q&A ------------------------------------------------------ */

/** How many documents a scope covers — shown before and after a question. */
export function scopeSize(scope: ChatScope): number {
  return scope === "All" ? documents.length : documents.filter((d) => d.type === scope).length;
}

export type WorkspaceAnswer = {
  text: string;
  citations: WorkspaceCitation[];
  thinking: string;
  searched: number;
};

/** Null means the corpus genuinely has nothing to say — not an error. */
export async function askWorkspace(
  question: string,
  scope: ChatScope,
  opts: { simulate?: Simulate; signal?: AbortSignal } = {},
): Promise<WorkspaceAnswer | null> {
  const simulate = opts.simulate ?? "ok";
  await sleep(simulate === "slow" ? 2800 : 1000, opts.signal);
  fail(simulate, [
    "Answer generation failed",
    "The retrieval service returned 500 before any passages were ranked. Nothing was charged — retry the question.",
    "ERR_RAG_UPSTREAM",
  ]);

  const searched = scopeSize(scope);
  if (searched === 0) return null;

  const answer = chatAnswerFor(question);
  if (!answer) return null;

  // A scoped question only cites documents inside that scope.
  const citations =
    scope === "All" ? answer.citations : answer.citations.filter((c) => c.docType === scope);
  if (citations.length === 0) return null;

  return { text: answer.text, citations, thinking: answer.thinking, searched };
}

/** The blocks that make up one page of the document reader. */
export function getPage(page: number): SourceBlock[] {
  return QA_PAGES[page] ?? QA_FALLBACK;
}
