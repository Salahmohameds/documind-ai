import type { DocStatus, Tone } from "./design";

export type { DocStatus, Tone };

export type DocType = "Invoice" | "Contract" | "Amendment" | "Statement";

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

export type RiskCategory = { name: string; score: number };

export type Finding = {
  id: string;
  title: string;
  severity: "High" | "Medium" | "Low";
  description: string;
  page: number;
};

export type DocumentDetail = DocumentSummary & {
  classification: {
    label: string;
    subtype: string;
    confidence: number;
    runnerUp: string;
    runnerUpConfidence: number;
  };
  processedIn: string;
  model: string;
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
  delta: string;
  direction: "up" | "down";
  deltaTone: Tone;
  icon: "bars" | "warning" | "shield" | "clock";
  iconTone: Tone;
  footnote: string;
};

export type Dashboard = {
  kpis: Kpi[];
  flagged: DocumentSummary[];
  exceptions: [string, number][];
  gauge: { pct: number; target: string; legend: { label: string; value: number; tone: Tone }[] };
  seriesSeed: number;
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

