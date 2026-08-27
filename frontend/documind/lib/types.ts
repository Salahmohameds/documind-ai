import type { DocStatus, Tone } from "./design";

export type { DocStatus, Tone };

/**
 * "Unknown" is what document-service stores until a classifier has run. It is
 * part of the union rather than coerced to a guess, so the UI can say "not
 * classified yet" instead of labelling every upload a Contract.
 */
export type DocType = "Invoice" | "Contract" | "Amendment" | "Statement" | "Unknown";

export type DocumentSummary = {
  id: string;
  name: string;
  ext: string;
  type: DocType;
  status: DocStatus;
  /** null while queued / processing / failed — nothing was scored. */
  risk: number | null;
  pages: number;
  sizeMb: number;
  counterparty: string;
  uploaded: string;
  uploadedAt: number;
  /** Relative form, as shown on the dashboard. */
  time: string;
  flags: number;
  verdict: "Auto-approved" | "Needs review" | "Pending";
  /** Only set while status === "processing". */
  progress?: { step: number; pct: number };
  /** Only set when status === "failed". */
  error?: DocError;
};

export type DocError = {
  code: string;
  title: string;
  detail: string;
  job: string;
  at: string;
  retryable: boolean;
};

export type ExtractedField = {
  key: string;
  value: string;
  confidence: number;
  page: number;
};

export type PiiFinding = {
  id: string;
  type: string;
  masked: string;
  value: string;
  page: number;
};

export type RiskCategory = {
  name: string;
  score: number;
  /**
   * The band ai-service actually decided.
   *
   * Per-category risk is derived from which rules fired, not scored, so the
   * band is the measurement and `score` is a stand-in positioned inside the
   * band's range so threshold logic still works. Shown in preference to the
   * number wherever it is present.
   */
  band?: string | null;
};

export type Finding = {
  id: string;
  title: string;
  severity: "High" | "Medium" | "Low";
  description: string;
  page: number;
};

/**
 * Everything past the summary is written by the analysis pipeline, so all of
 * it is optional: a document that has only just been uploaded genuinely has no
 * classification, no extracted fields and no risk breakdown, and the type says
 * so rather than forcing the UI to invent placeholders.
 */
export type DocumentDetail = DocumentSummary & {
  classification?: {
    label: string;
    subtype: string;
    confidence: number;
    runnerUp: string;
    runnerUpConfidence: number;
  } | null;
  processedIn?: string | null;
  model?: string | null;
  fields: ExtractedField[];
  fieldsExpected: number;
  pii: PiiFinding[];
  riskCategories: RiskCategory[];
  findings: Finding[];
  /** Extraction can partially succeed — some pages unreadable. */
  partial?: { message: string; pagesSkipped: number[] };
};

/* -- Dashboard ---------------------------------------------------------- */

export type Kpi = {
  key: string;
  label: string;
  value: string;
  unit?: string;
  /** Absent for live gauges, where a period-over-period comparison is meaningless. */
  delta?: string;
  direction?: "up" | "down";
  deltaTone?: Tone;
  icon: "bars" | "warning" | "shield" | "clock";
  iconTone: Tone;
  footnote: string;
};

export type Dashboard = {
  kpis: Kpi[];
  flagged: DocumentSummary[];
  exceptions: [string, number][];
  gauge: { pct: number; target: string; legend: { label: string; value: number; tone: Tone }[] };
  /**
   * Real daily ingestion counts per document type, oldest day first, one entry
   * per day in the selected range. A type with no uploads is omitted entirely
   * rather than plotted as a flat line at zero.
   */
  series: { name: string; counts: number[] }[];
  /** Documents uploaded inside the selected window — drives the empty state. */
  volume: number;
  generatedAt: string;
  /** Set when one panel of the dashboard could not be computed. */
  degraded?: { panel: string; message: string };
};

export type DateRange = "7d" | "30d" | "90d";

/* -- Upload ------------------------------------------------------------- */

export type UploadStage =
  | "queued"
  | "uploading"
  | "processing"
  | "done"
  | "failed"
  | "cancelled"
  | "rejected";

export type UploadJob = {
  id: string;
  /**
   * The file itself, kept so the job can actually be sent and re-sent.
   *
   * Absent on an adopted job: a document that was already in the pipeline when
   * this tab opened has no File behind it, only an id to follow.
   */
  file?: File;
  name: string;
  ext: string;
  sizeMb: number;
  type: DocType | "Detecting…";
  stage: UploadStage;
  /** 0–100 transfer percentage. */
  uploadPct: number;
  /** 1-based index into PIPELINE_STEPS reached so far. */
  step: number;
  /** Progress within the current pipeline step, 0–100. */
  stepPct: number;
  startedAt: number;
  elapsedMs: number;
  error?: DocError;
  docId?: string;
  /** Set when the file never started — wrong type or too large. */
  rejected?: string;
  retries: number;
  /**
   * The document's own lifecycle state, as document-service last reported it.
   *
   * Distinct from `stage`, which describes this browser's upload job. The two
   * disagree in exactly the case that matters: once the bytes are sent the job
   * is "processing", but the document can still be sitting at "queued" because
   * no worker has claimed it.
   */
  docStatus?: "queued" | "processing" | "completed" | "failed";
  /**
   * True when this row was picked up from the server rather than uploaded here.
   *
   * Such a row can be followed and reprocessed but never re-sent — there is no
   * file in this browser to send.
   */
  adopted?: boolean;
  /** When the pipeline last reported anything new about this document. */
  lastChangeAt?: number;
  /**
   * How long the pipeline has been silent, advanced by the elapsed clock.
   *
   * Derived into state rather than computed at render: a component that reads
   * the wall clock while rendering produces a different tree on every pass,
   * which React treats as impure.
   */
  stalledMs: number;
};

/* -- Q&A ---------------------------------------------------------------- */

export type Citation = { id: string; page: number; label: string; context: string };

export type QaStatus = "thinking" | "streaming" | "done" | "error" | "no-answer";

export type QaMessage =
  | { id: string; role: "user"; text: string; at: number }
  | {
      id: string;
      role: "assistant";
      at: number;
      status: QaStatus;
      /** Progressive text — grows while streaming. */
      text: string;
      full: string;
      thinkingLabel?: string;
      citations: string[];
      error?: { title: string; detail: string };
      question: string;
    };

export type SourceBlock = { heading: string; text: string; cite?: string };

/* -- Workspace Q&A (RAG across the corpus) ------------------------------ */

/** A citation that has to identify its document, not just a page. */
export type WorkspaceCitation = {
  id: string;
  docId: string;
  docName: string;
  docType: DocType;
  page: number;
  context: string;
  snippet: string;
};

/** What the retriever is allowed to search. */
export type ChatScope = "All" | DocType;

export type ChatMessage =
  | { id: string; role: "user"; text: string; at: number; scope: ChatScope }
  | {
      id: string;
      role: "assistant";
      at: number;
      status: QaStatus;
      /** Progressive text — grows while streaming. */
      text: string;
      full: string;
      thinkingLabel?: string;
      citations: WorkspaceCitation[];
      /** How many documents the retriever looked at, for the provenance line. */
      searched: number;
      error?: { title: string; detail: string };
      question: string;
      scope: ChatScope;
    };

