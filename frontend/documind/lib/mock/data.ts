import type {
  ChatScope,
  Citation,
  Dashboard,
  DateRange,
  DocError,
  DocType,
  DocumentDetail,
  DocumentSummary,
  ExtractedField,
  Finding,
  PiiFinding,
  SourceBlock,
  WorkspaceCitation,
} from "@/lib/types";

/**
 * The entire mock dataset lives here. Nothing outside `lib/mock/` imports it —
 * screens go through `lib/api.ts`, so swapping this file for real responses is
 * a one-file change.
 */

export const WORKSPACE = {
  org: "Meridian Logistics",
  orgFull: "Meridian Logistics LLC",
  user: "Rowan Nakamura",
  email: "ops@meridian.com",
  initials: "RN",
  plan: "Pro",
  region: "us-ashburn-1",
};

/** The only credentials the mock auth accepts. */
export const DEMO_CREDENTIALS = { email: "ops@meridian.com", password: "documind2026" };

export const PIPELINE_STEPS = [
  "Uploaded",
  "Classified",
  "Extracted",
  "PII Scanned",
  "Risk Scored",
  "Indexed",
  "Complete",
] as const;

export const UPLOAD_LIMITS = {
  extensions: ["pdf", "docx", "tiff", "png"],
  maxMb: 200,
  maxBatch: 50,
};

/* -- Error catalogue ---------------------------------------------------- */

const ERRORS: Record<string, Omit<DocError, "job" | "at">> = {
  no_text_layer: {
    code: "ERR_EXTRACT_NO_TEXT_LAYER",
    title: "Extraction failed — page 3 could not be parsed",
    detail:
      "The document contains a scanned image layer with no recoverable text. Re-run with OCR enabled, or upload a text-based PDF. No fields, PII findings or risk score were produced.",
    retryable: true,
  },
  encrypted: {
    code: "ERR_DOC_ENCRYPTED",
    title: "Document is password protected",
    detail:
      "DocuMind could not open the file — it is encrypted with an owner password. Remove the restriction and upload again. Nothing was extracted or indexed.",
    retryable: false,
  },
  timeout: {
    code: "ERR_PIPELINE_TIMEOUT",
    title: "Pipeline timed out during risk scoring",
    detail:
      "The risk model did not return within 60s. Classification and extraction completed and were kept; the risk score is missing. Retrying re-runs scoring only.",
    retryable: true,
  },
  classify: {
    code: "ERR_CLASSIFY_LOW_CONFIDENCE",
    title: "Classification below the acceptance threshold",
    detail:
      "Top class scored 41.6%, under the 60% floor for this workspace. The document was not routed to an extraction template. Retry after choosing a type manually.",
    retryable: true,
  },
};

export type ErrorKind = keyof typeof ERRORS;

export function mockError(kind: ErrorKind, seed: number): DocError {
  const e = ERRORS[kind];
  const hh = String(9 + (seed % 12)).padStart(2, "0");
  const mm = String((seed * 7) % 60).padStart(2, "0");
  return {
    ...e,
    job: `job_${((seed * 2654435761) >>> 8).toString(16).slice(0, 8)}`,
    at: `${hh}:${mm}:0${seed % 10} UTC`,
  };
}

/* -- Documents ---------------------------------------------------------- */

type Seed = [
  name: string,
  type: DocType,
  status: DocumentSummary["status"],
  risk: number | null,
  pages: number,
  sizeMb: number,
  counterparty: string,
  day: number,
  hour: number,
  minute: number,
];

const SEEDS: Seed[] = [
  ["ACME_Q3_MSA_countersigned.pdf", "Contract", "completed", 18, 42, 4.2, "Acme Freight Holdings", 25, 9, 14],
  ["INV-2026-04417_Northwind.pdf", "Invoice", "completed", 7, 3, 1.8, "Northwind Traders", 25, 8, 52],
  ["Vendor_NDA_Kestrel_v4.docx", "Contract", "processing", null, 11, 2.6, "Kestrel Systems", 25, 8, 31],
  ["INV-2026-04416_Halcyon.pdf", "Invoice", "failed", null, 5, 12.4, "Halcyon Shipping", 25, 7, 58],
  ["Global_MSA_Amendment_2.pdf", "Amendment", "completed", 72, 28, 6.1, "Acme Freight Holdings", 24, 18, 22],
  ["INV-2026-04409_Perrin.tiff", "Invoice", "queued", null, 2, 0.9, "Perrin & Co.", 24, 17, 40],
  ["SOW_Ridgeline_Consulting.pdf", "Contract", "completed", 29, 16, 3.3, "Ridgeline Consulting", 24, 16, 5],
  ["INV-2026-04398_Cardinal.pdf", "Invoice", "completed", 91, 4, 1.1, "Cardinal Logistics", 24, 15, 11],
  ["Master_Services_Baltic.docx", "Contract", "processing", null, 54, 9.8, "Baltic Freight Co.", 24, 14, 47],
  ["INV-2026-04385_Atlas.pdf", "Invoice", "completed", 12, 3, 0.7, "Atlas Logistics", 24, 13, 29],
  ["Statement_AUG_Northwind.pdf", "Statement", "completed", 22, 9, 2.2, "Northwind Traders", 24, 11, 8],
  ["INV-2026-04371_Sable.pdf", "Invoice", "failed", null, 6, 3.9, "Sable Transport", 24, 10, 2],
  ["Amendment_1_Halcyon_SLA.pdf", "Amendment", "completed", 58, 12, 2.8, "Halcyon Shipping", 23, 19, 44],
  ["INV-2026-04360_Meridian_Rail.pdf", "Invoice", "completed", 34, 5, 1.4, "Meridian Rail", 23, 17, 12],
  ["NDA_Pacific_Cargo_2026.pdf", "Contract", "completed", 45, 8, 1.9, "Pacific Cargo Ltd.", 23, 15, 30],
  ["Statement_JUL_Cardinal.pdf", "Statement", "completed", 15, 11, 2.4, "Cardinal Logistics", 23, 13, 55],
  ["INV-2026-04344_TransGlobal.pdf", "Invoice", "completed", 78, 7, 2.1, "TransGlobal Inc.", 23, 12, 3],
  ["MSA_TransGlobal_2026_full_execution_copy_final.pdf", "Contract", "completed", 67, 96, 24.7, "TransGlobal Inc.", 23, 9, 21],
  ["INV-2026-04331_Midwest.pdf", "Invoice", "completed", 23, 3, 0.6, "Midwest Haulers", 22, 18, 40],
  ["Amendment_3_Atlas_Rates.docx", "Amendment", "processing", null, 6, 1.2, "Atlas Logistics", 22, 16, 17],
  ["INV-2026-04320_Kestrel.pdf", "Invoice", "completed", 41, 4, 1.0, "Kestrel Systems", 22, 14, 9],
  ["Statement_JUL_Baltic.pdf", "Statement", "failed", null, 14, 5.5, "Baltic Freight Co.", 22, 11, 51],
  ["SOW_Amendment_Ridgeline.pdf", "Amendment", "completed", 31, 9, 1.7, "Ridgeline Consulting", 22, 10, 14],
  ["INV-2026-04311_Sable.pdf", "Invoice", "completed", 88, 5, 1.3, "Sable Transport", 21, 17, 36],
  ["Framework_Agreement_Perrin.pdf", "Contract", "completed", 63, 34, 7.8, "Perrin & Co.", 21, 15, 2],
  ["INV-2026-04298_Pacific.pdf", "Invoice", "queued", null, 4, 1.1, "Pacific Cargo Ltd.", 21, 12, 48],
  ["Statement_JUN_Atlas.pdf", "Statement", "completed", 19, 10, 2.0, "Atlas Logistics", 21, 10, 25],
  ["NDA_Midwest_Haulers_v2.docx", "Contract", "completed", 26, 7, 1.5, "Midwest Haulers", 20, 16, 40],
  ["INV-2026-04287_Cardinal.pdf", "Invoice", "completed", 55, 6, 1.6, "Cardinal Logistics", 20, 14, 11],
  ["Amendment_2_Kestrel_Term.pdf", "Amendment", "completed", 49, 5, 1.1, "Kestrel Systems", 20, 12, 30],
  ["MSA_Sable_Transport_2025.pdf", "Contract", "completed", 71, 38, 8.4, "Sable Transport", 19, 18, 5],
  ["INV-2026-04271_Northwind.pdf", "Invoice", "completed", 9, 3, 0.8, "Northwind Traders", 19, 15, 44],
  ["Statement_JUN_TransGlobal.pdf", "Statement", "completed", 38, 13, 3.1, "TransGlobal Inc.", 19, 13, 20],
  ["INV-2026-04260_Halcyon.pdf", "Invoice", "completed", 84, 4, 1.2, "Halcyon Shipping", 19, 11, 2],
];

const MONTH = "Aug";
const FAIL_KINDS: ErrorKind[] = ["no_text_layer", "encrypted", "timeout", "classify"];

export function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function relative(day: number, hour: number, minute: number): string {
  const minsAgo = (25 - day) * 1440 + (10 - hour) * 60 + (0 - minute) + 600;
  if (minsAgo < 60) return `${Math.max(1, minsAgo)}m ago`;
  if (minsAgo < 1440) return `${Math.round(minsAgo / 60)}h ago`;
  return `${Math.round(minsAgo / 1440)}d ago`;
}

let failIdx = 0;

export const DOCUMENTS: DocumentSummary[] = SEEDS.map(
  ([name, type, status, risk, pages, sizeMb, counterparty, day, hour, minute]) => {
    const seed = hash(name);
    const id = `doc_${(seed >>> 4).toString(16).padStart(8, "0").slice(0, 8)}`;
    return {
      id,
      name,
      ext: name.split(".").pop()!.toUpperCase(),
      type,
      status,
      risk,
      pages,
      sizeMb,
      counterparty,
      uploaded: `${MONTH} ${day}, ${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
      uploadedAt: Date.UTC(2026, 7, day, hour, minute),
      time: relative(day, hour, minute),
      flags: status === "completed" && risk !== null ? Math.max(0, Math.round(risk / 24)) : 0,
      verdict:
        status === "completed"
          ? (risk ?? 0) >= 60
            ? "Needs review"
            : "Auto-approved"
          : status === "failed"
            ? "Needs review"
            : "Pending",
      progress: status === "processing" ? { step: 2 + (seed % 4), pct: 20 + (seed % 70) } : undefined,
      error: status === "failed" ? mockError(FAIL_KINDS[failIdx++ % FAIL_KINDS.length], seed % 97) : undefined,
    };
  },
);

/* -- Document detail ---------------------------------------------------- */

const CONTRACT_FIELDS: ExtractedField[] = [
  { key: "Parties", value: "Meridian Logistics LLC · {{counterparty}}", confidence: 97, page: 1 },
  { key: "Start date", value: "2026-09-01", confidence: 99, page: 2 },
  { key: "End date", value: "2029-08-31", confidence: 99, page: 2 },
  { key: "Payment terms", value: "Net 45 from invoice receipt", confidence: 91, page: 11 },
  { key: "Total value", value: "4,820,000.00", confidence: 96, page: 12 },
  { key: "Currency", value: "USD", confidence: 99, page: 12 },
  { key: "Governing law", value: "Republic of Ireland — courts of Dublin", confidence: 83, page: 22 },
  {
    key: "Notice address",
    value: "Attn. Contracts Desk, 4400 Meridian Way, Suite 1200, Ashburn VA 20147, United States",
    confidence: 88,
    page: 26,
  },
];

const INVOICE_FIELDS: ExtractedField[] = [
  { key: "Invoice number", value: "{{invoice}}", confidence: 99, page: 1 },
  { key: "Supplier", value: "{{counterparty}}", confidence: 98, page: 1 },
  { key: "Invoice date", value: "2026-08-14", confidence: 97, page: 1 },
  { key: "Due date", value: "2026-09-28", confidence: 95, page: 1 },
  { key: "Subtotal", value: "18,440.00", confidence: 99, page: 2 },
  { key: "Tax (VAT 20%)", value: "3,688.00", confidence: 94, page: 2 },
  { key: "Total due", value: "22,128.00 USD", confidence: 98, page: 2 },
  { key: "Purchase order", value: "PO-2026-11842", confidence: 72, page: 1 },
];

const PII_POOL: Omit<PiiFinding, "id">[] = [
  { type: "Bank account", masked: "••••••1234", value: "GB29 NWBK 6016 1331 9268 19", page: 12 },
  { type: "Tax ID (EIN)", masked: "••••••8871", value: "47-2938871", page: 1 },
  { type: "Signatory email", masked: "••••••@meridian.com", value: "r.nakamura@meridian.com", page: 27 },
  { type: "Phone number", masked: "••••••4402", value: "+1 202 555 4402", page: 27 },
  { type: "Passport number", masked: "••••••7719", value: "X4820 7719", page: 30 },
  { type: "Home address", masked: "•••••• Ashburn, VA", value: "118 Cottonwood Lane, Ashburn, VA 20147", page: 31 },
];

const FINDING_POOL: Omit<Finding, "id">[] = [
  { title: "Automatic renewal detected", severity: "High", description: "Term renews for 36 months unless cancelled 90 days before expiry.", page: 4 },
  { title: "Unlimited liability exposure", severity: "High", description: "No liability cap for data breach or IP indemnity claims.", page: 17 },
  { title: "Payment terms exceed policy", severity: "High", description: "Net 45 against a Net 30 standard; 15-day working-capital gap.", page: 11 },
  { title: "Governing law is non-standard", severity: "Medium", description: "Disputes settled in Ireland rather than Delaware.", page: 22 },
  { title: "Assignment clause is one-sided", severity: "Low", description: "Counterparty may assign without consent; Meridian may not.", page: 24 },
  { title: "Indexation tied to an unpublished rate", severity: "Medium", description: "Annual uplift references a supplier-internal index with no audit right.", page: 19 },
  { title: "Termination for convenience is asymmetric", severity: "Medium", description: "Counterparty may exit on 30 days' notice; Meridian requires 180.", page: 20 },
  { title: "Line items do not reconcile to the purchase order", severity: "High", description: "Three line items totalling 4,180.00 have no matching PO commitment.", page: 2 },
  { title: "Duplicate invoice number in the last 90 days", severity: "Low", description: "The same supplier invoice number was settled on 2026-06-02.", page: 1 },
];

const CLAUSE_TAIL =
  "Each party shall maintain, throughout the term and for six (6) years thereafter, complete and accurate books and records relating to its performance under this Agreement, and shall make such records available for inspection by the other party or its appointed auditors on not less than ten (10) business days' written notice, no more than twice in any twelve (12) month period, during normal business hours and subject to the receiving party's reasonable confidentiality and site-safety requirements.";

export function buildDetail(doc: DocumentSummary): DocumentDetail {
  const seed = hash(doc.id);
  const isInvoice = doc.type === "Invoice" || doc.type === "Statement";
  const base = isInvoice ? INVOICE_FIELDS : CONTRACT_FIELDS;
  const complete = doc.status === "completed";

  const fields = (complete ? base : []).map((f) => ({
    ...f,
    value: f.value
      .replace("{{counterparty}}", doc.counterparty)
      .replace("{{invoice}}", doc.name.replace(/_.*/, "").replace(/\.\w+$/, "")),
    page: Math.min(f.page, doc.pages),
  }));

  const piiCount = complete ? (seed % 5) + (doc.pages > 20 ? 2 : 0) : 0;
  const pii = PII_POOL.slice(0, Math.min(piiCount, PII_POOL.length)).map((p, i) => ({
    ...p,
    id: `pii_${i}`,
    page: Math.min(p.page, doc.pages),
  }));

  const risk = doc.risk ?? 0;
  const findingCount = complete ? Math.min(FINDING_POOL.length, 1 + Math.round(risk / 18)) : 0;
  const findings = FINDING_POOL.slice(0, findingCount).map((f, i) => ({
    ...f,
    id: `find_${i}`,
    page: Math.min(f.page, doc.pages),
    description: i === 1 ? `${f.description} ${CLAUSE_TAIL}` : f.description,
  }));

  const conf = 100 - (seed % 6) - (risk > 66 ? 2 : 0);

  return {
    ...doc,
    classification: {
      label: doc.type.toUpperCase(),
      subtype: isInvoice ? "Commercial · goods" : "Amendment · MSA",
      confidence: Number(conf.toFixed(1)),
      runnerUp: isInvoice ? "Statement" : "Statement of Work",
      runnerUpConfidence: Number(((100 - conf) * 0.6).toFixed(1)),
    },
    processedIn: `${(2 + (seed % 40) / 10).toFixed(1)}s`,
    model: "idp-classify-v4",
    fields,
    fieldsExpected: base.length,
    pii,
    riskCategories: [
      { name: "Financial", score: Math.min(100, risk + 12) },
      { name: "Legal", score: Math.max(0, risk - 14) },
      { name: "Operational", score: Math.max(0, Math.min(100, risk - 1)) },
    ],
    findings,
    partial:
      complete && seed % 7 === 0
        ? {
            message: "2 pages were skipped — they contain only scanned images with no text layer.",
            pagesSkipped: [Math.min(3, doc.pages), Math.min(9, doc.pages)],
          }
        : undefined,
  };
}

/* -- Dashboard ---------------------------------------------------------- */

const RANGE_FACTOR: Record<DateRange, number> = { "7d": 0.28, "30d": 1, "90d": 2.8 };

export const RANGE_LABEL: Record<DateRange, string> = {
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  "90d": "Last 90 days",
};

export const RANGE_DATES: Record<DateRange, string> = {
  "7d": "Aug 19 — Aug 25, 2026",
  "30d": "Jul 27 — Aug 25, 2026",
  "90d": "May 28 — Aug 25, 2026",
};

export function buildDashboard(range: DateRange): Dashboard {
  const f = RANGE_FACTOR[range];
  const n = (x: number) => Math.round(x * f);

  return {
    kpis: [
      { key: "processed", label: "Documents processed", value: n(1247).toLocaleString(), delta: "12%", direction: "up", deltaTone: "--ok", icon: "bars", iconTone: "--accent", footnote: `vs. ${n(1113).toLocaleString()} previous period` },
      { key: "exceptions", label: "Exceptions detected", value: n(89).toLocaleString(), delta: "4%", direction: "up", deltaTone: "--warn", icon: "warning", iconTone: "--warn", footnote: `vs. ${n(86)} previous period` },
      { key: "high", label: "High risk documents", value: String(n(12)), delta: "2", direction: "down", deltaTone: "--ok", icon: "shield", iconTone: "--bad", footnote: `risk ≥ 67 · ${n(14)} previous period` },
      { key: "review", label: "Avg review time", value: range === "7d" ? "2.1" : range === "30d" ? "2.4" : "3.0", unit: " min", delta: "18%", direction: "down", deltaTone: "--ok", icon: "clock", iconTone: "--ok", footnote: "vs. 2.9 min previous period" },
    ],
    flagged: DOCUMENTS.filter((d) => d.verdict === "Needs review" || d.status === "failed" || d.status === "processing").slice(0, 6),
    exceptions: [
      ["Incomplete counterparty", 84],
      ["Unmatched line items", 71],
      ["Missing signature block", 63],
      ["Tax ID invalid", 48],
      ["PII in free text", 39],
      ["Metadata tampered", 22],
    ],
    gauge: {
      pct: range === "7d" ? 68 : range === "30d" ? 61 : 57,
      target: range === "7d" ? "Ahead of the 70% target" : "On track for 70% target",
      legend: [
        { label: "Low", value: n(761), tone: "--ok" },
        { label: "Elevated", value: n(287), tone: "--warn" },
        { label: "High", value: n(199), tone: "--bad" },
      ],
    },
    seriesSeed: range === "7d" ? 7 : range === "30d" ? 0 : 31,
    generatedAt: "Aug 25, 10:04",
  };
}

export const EMPTY_DASHBOARD: Dashboard = {
  kpis: buildDashboard("30d").kpis.map((k) => ({
    ...k,
    value: "0",
    unit: undefined,
    delta: "0%",
    footnote: "no documents in this period",
  })),
  flagged: [],
  exceptions: [],
  gauge: {
    pct: 0,
    target: "No documents scored yet",
    legend: [
      { label: "Low", value: 0, tone: "--ok" },
      { label: "Elevated", value: 0, tone: "--warn" },
      { label: "High", value: 0, tone: "--bad" },
    ],
  },
  seriesSeed: -1,
  generatedAt: "—",
};

/** A dashboard where one panel failed to compute — the partial-success case. */
export function degradedDashboard(range: DateRange): Dashboard {
  return {
    ...buildDashboard(range),
    exceptions: [],
    degraded: {
      panel: "Top exception types",
      message: "The exception aggregator timed out. Every other panel is current as of Aug 25, 10:04.",
    },
  };
}

/* -- Q&A ---------------------------------------------------------------- */

export const CITATIONS: Citation[] = [
  { id: "c1", page: 11, label: "page 11", context: "Section 7.1 — Invoicing and payment" },
  { id: "c2", page: 12, label: "page 12", context: "Schedule B — Fees and interest" },
  { id: "c3", page: 4, label: "page 4", context: "Section 4.2 — Term and renewal" },
  { id: "c4", page: 17, label: "page 17", context: "Section 8.3 — Limitation of liability" },
  { id: "c5", page: 22, label: "page 22", context: "Section 11.6 — Governing law" },
];

export const QA_PAGES: Record<number, SourceBlock[]> = {
  4: [
    { heading: "4.1  Initial term", text: "The initial term of this Agreement commences on the Effective Date and continues for thirty-six (36) months, unless terminated earlier in accordance with Section 9." },
    { heading: "4.2  Automatic renewal", cite: "c3", text: "Upon expiry of the initial term, this Agreement shall renew automatically for successive periods of thirty-six (36) months unless either party gives written notice of non-renewal no later than ninety (90) days prior to the end of the then-current term." },
    { heading: "4.3  Notice of non-renewal", text: "Notice under Section 4.2 must be delivered to the addresses set out in Schedule A and is effective on receipt. Notice given after the ninety (90) day window shall apply to the following renewal term only." },
    { heading: "4.4  Effect of renewal", text: "All fees, service levels and liability provisions in force immediately prior to renewal continue to apply during each renewal term unless amended in writing and signed by both parties." },
  ],
  11: [
    { heading: "7.1  Invoicing and payment", cite: "c1", text: "Supplier shall invoice monthly in arrears. Undisputed invoices are payable in full within forty-five (45) days of receipt of invoice by Customer's accounts payable function, in the currency stated in Schedule B." },
    { heading: "7.2  Disputed amounts", text: "Customer may withhold payment of any line item disputed in good faith, provided that Customer notifies Supplier in writing within fifteen (15) days of invoice receipt and pays all undisputed amounts when due." },
    { heading: "7.3  Suspension", text: "Where an undisputed invoice remains unpaid sixty (60) days after its due date, Supplier may suspend performance on ten (10) business days' written notice." },
  ],
  12: [
    { heading: "Schedule B  Fees", cite: "c2", text: "Late payment of any undisputed amount accrues interest at one and one-half percent (1.5%) per month, calculated daily from the due date until payment is received in full." },
    { heading: "Schedule B  Total contract value", text: "The aggregate value of services under this Amendment is USD 4,820,000.00 over the initial term, exclusive of taxes and pass-through expenses." },
    { heading: "Schedule B  Currency", text: "All amounts are stated and payable in United States Dollars (USD). Currency conversion, where required, applies the spot rate published on the invoice date." },
  ],
  17: [
    { heading: "8.1  Direct damages", text: "Each party's aggregate liability for direct damages arising out of or in connection with this Agreement is limited to the fees paid or payable in the twelve (12) months preceding the event giving rise to the claim." },
    { heading: "8.3  Excluded from the cap", cite: "c4", text: "The limitation in Section 8.1 does not apply to liability arising from a breach of confidentiality, a personal data breach, or an indemnity given under Section 10 (Intellectual property), which are unlimited in amount." },
    { heading: "8.4  Consequential loss", text: "Neither party is liable for indirect or consequential loss, loss of profit, loss of anticipated savings or loss of goodwill, whether or not foreseeable." },
  ],
  22: [
    { heading: "11.6  Governing law", cite: "c5", text: "This Agreement and any dispute or claim arising out of or in connection with it is governed by and construed in accordance with the laws of the Republic of Ireland." },
    { heading: "11.7  Jurisdiction", text: "The courts of Dublin have exclusive jurisdiction to settle any dispute or claim arising out of or in connection with this Agreement or its subject matter." },
    { heading: "11.8  Severability", text: `If any provision of this Agreement is held to be invalid or unenforceable, that provision shall be severed and the remainder shall continue in full force. ${CLAUSE_TAIL}` },
  ],
};

export const QA_FALLBACK: SourceBlock[] = [
  { heading: "9.4  Assignment", text: "Neither party may assign this Agreement without the prior written consent of the other, save that Supplier may assign to an affiliate on notice to Customer." },
  { heading: "9.5  Entire agreement", text: "This Agreement, together with its Schedules, constitutes the entire agreement between the parties and supersedes all prior proposals and understandings, whether written or oral." },
  { heading: "9.6  Counterparts", text: "This Agreement may be executed in counterparts, each of which is deemed an original and which together constitute one and the same instrument." },
];

/** The verbatim passage a per-document citation points at. */
export function qaSnippet(citeId: string): string {
  for (const blocks of Object.values(QA_PAGES)) {
    const hit = blocks.find((b) => b.cite === citeId);
    if (hit) return hit.text;
  }
  return "";
}

export const QA_SUGGESTIONS = [
  "What are the payment terms?",
  "Are there any auto-renewal clauses?",
  "Is our liability capped?",
  "Which law governs this agreement?",
];

type Answer = { match: RegExp; text: string; citations: string[]; thinking: string };

export const QA_ANSWERS: Answer[] = [
  {
    match: /pay|invoic|net|term|due|interest/i,
    thinking: "Reading pages 11–12 · checking payment schedule",
    text: "Payment is due **Net 45 from invoice receipt**, which is 15 days beyond the Net 30 standard in Meridian's procurement policy. Late payments accrue 1.5% monthly interest calculated daily, and the supplier may suspend performance once an undisputed invoice is 60 days overdue. Disputed line items may be withheld only if notice is given within 15 days of receipt.",
    citations: ["c1", "c2"],
  },
  {
    match: /renew|expir|cancel|notice/i,
    thinking: "Reading pages 4–7 · checking notice periods",
    text: "Yes. Section 4.2 renews the term automatically for successive **36-month periods** unless either party gives written notice at least 90 days before expiry. Notice is only effective on receipt at the Schedule A address, and late notice rolls into the following renewal term — so the practical cancellation deadline for the current term is 2029-06-02.",
    citations: ["c3"],
  },
  {
    match: /liabil|cap|indemnit|damage|breach/i,
    thinking: "Reading pages 16–18 · comparing against policy",
    text: "Liability is capped at the fees paid in the preceding 12 months for ordinary direct damages, but Section 8.3 carves out **confidentiality breaches, personal data breaches and IP indemnities — those are unlimited**. Consequential loss is excluded for both parties. This is the single largest driver of the document's risk score.",
    citations: ["c4"],
  },
  {
    match: /law|jurisdiction|court|dispute|govern/i,
    thinking: "Reading pages 21–23 · locating the governing-law clause",
    text: "The agreement is governed by the laws of the **Republic of Ireland**, with exclusive jurisdiction in the courts of Dublin. Meridian's standard position is Delaware law, so this clause is flagged as non-standard — it does not block signature, but legal sign-off is required before countersignature.",
    citations: ["c5"],
  },
];

export const QA_DEFAULT_ANSWER: Answer = {
  match: /.*/,
  thinking: "Searching all 12 pages · ranking passages",
  text: "Here is what the document says on that point. The agreement runs for an initial 36-month term at a total value of **USD 4,820,000.00**, payable Net 45 in arrears. The clauses most likely to matter for your review are the automatic renewal in Section 4.2, the uncapped liability carve-outs in Section 8.3, and the Irish governing law in Section 11.6 — all three are reflected in the document's risk score.",
  citations: ["c3", "c4", "c5"],
};

/** Questions that should demonstrate the grounded "not in this document" state. */
export const QA_NO_ANSWER = /salary|employee|headcount|weather|stock price|ceo|hiring/i;

export function answerFor(question: string): Answer | null {
  if (QA_NO_ANSWER.test(question)) return null;
  return QA_ANSWERS.find((a) => a.match.test(question)) ?? QA_DEFAULT_ANSWER;
}

/* -- Workspace Q&A ------------------------------------------------------ */

/**
 * Citations resolve against the real document list, so every chip in a chat
 * answer links to a document that actually exists in this workspace.
 */
function cite(
  id: string,
  name: string,
  page: number,
  context: string,
  snippet: string,
): WorkspaceCitation {
  const doc = DOCUMENTS.find((d) => d.name === name);
  if (!doc) throw new Error(`Unknown document in citation fixture: ${name}`);
  return { id, docId: doc.id, docName: doc.name, docType: doc.type, page, context, snippet };
}

type WorkspaceAnswer = {
  match: RegExp;
  thinking: string;
  text: string;
  citations: WorkspaceCitation[];
};

export const CHAT_SUGGESTIONS = [
  "Which contracts auto-renew in the next 90 days?",
  "Where are our payment terms worse than Net 30?",
  "Which documents have uncapped liability?",
  "Which invoices need review and why?",
];

export const CHAT_SCOPES: ChatScope[] = ["All", "Contract", "Amendment", "Invoice", "Statement"];

export const CHAT_ANSWERS: WorkspaceAnswer[] = [
  {
    match: /renew|expir|term|cancel|notice/i,
    thinking: "Retrieving renewal clauses · comparing notice windows",
    text: "**Three agreements auto-renew inside the next 90 days.** Global MSA Amendment 2 renews for a further 36 months unless notice lands by 2029-06-02. The TransGlobal MSA renews annually with a shorter 60-day window, and the Perrin framework agreement rolls month-to-month once the initial term lapses. All three put the notice burden on Meridian — none require the counterparty to remind us.",
    citations: [
      cite("w1", "Global_MSA_Amendment_2.pdf", 4, "Section 4.2 — Automatic renewal", "Upon expiry of the initial term, this Agreement shall renew automatically for successive periods of thirty-six (36) months unless either party gives written notice of non-renewal no later than ninety (90) days prior to the end of the then-current term."),
      cite("w2", "MSA_TransGlobal_2026_full_execution_copy_final.pdf", 31, "Section 12.1 — Term", "This Agreement continues for successive twelve (12) month periods unless terminated on not less than sixty (60) days' written notice prior to the anniversary of the Effective Date."),
      cite("w3", "Framework_Agreement_Perrin.pdf", 12, "Section 5.4 — Continuation", "Where no successor framework is executed, this Agreement continues on a month-to-month basis on the same commercial terms until terminated by either party on thirty (30) days' notice."),
    ],
  },
  {
    match: /pay|net |net-|invoic|terms|interest|late/i,
    thinking: "Retrieving payment clauses · comparing against Net 30 policy",
    text: "**Two agreements sit outside the Net 30 policy.** Global MSA Amendment 2 and the ACME MSA are both Net 45 from invoice receipt — a 15-day working-capital gap each — and both accrue 1.5% monthly interest on late payment. The Sable Transport MSA is compliant at Net 30 but allows suspension after only 30 days of non-payment, which is tighter than our standard 60.",
    citations: [
      cite("w4", "Global_MSA_Amendment_2.pdf", 11, "Section 7.1 — Invoicing and payment", "Undisputed invoices are payable in full within forty-five (45) days of receipt of invoice by Customer's accounts payable function."),
      cite("w5", "ACME_Q3_MSA_countersigned.pdf", 11, "Section 7.1 — Invoicing and payment", "Supplier shall invoice monthly in arrears; undisputed amounts fall due forty-five (45) days from receipt, with interest at one and one-half percent (1.5%) per month thereafter."),
      cite("w6", "MSA_Sable_Transport_2025.pdf", 24, "Section 9.2 — Suspension", "Supplier may suspend performance where any undisputed invoice remains unpaid thirty (30) days after its due date."),
    ],
  },
  {
    match: /liabil|cap|indemnit|damage|breach|exposure/i,
    thinking: "Retrieving liability clauses · checking carve-outs",
    text: "**Two agreements carry uncapped exposure.** The ACME MSA excludes confidentiality breaches, personal data breaches and IP indemnities from its liability cap, and the TransGlobal MSA has no cap at all on regulatory fines passed through to Meridian. Everything else in the corpus caps liability at 12 months of fees. These two are the largest single contributors to the current high-risk count.",
    citations: [
      cite("w7", "ACME_Q3_MSA_countersigned.pdf", 17, "Section 8.3 — Excluded from the cap", "The limitation in Section 8.1 does not apply to liability arising from a breach of confidentiality, a personal data breach, or an indemnity given under Section 10, which are unlimited in amount."),
      cite("w8", "MSA_TransGlobal_2026_full_execution_copy_final.pdf", 44, "Section 14.6 — Regulatory penalties", "Customer shall reimburse Supplier for any fine, penalty or levy imposed by a competent authority arising from Customer's instructions, without limitation as to amount."),
    ],
  },
  {
    match: /risk|review|flag|exception|approve|worst|highest/i,
    thinking: "Ranking by risk score · reading the flagged findings",
    text: "**Three invoices are above the 67 review threshold.** The Cardinal invoice scores 91 — three line items totalling 4,180.00 have no matching purchase-order commitment. The Sable invoice scores 88 on a duplicate invoice number already settled in June. The Halcyon invoice scores 84 for an invalid tax ID. None of the three can be auto-approved; all need an operator decision before payment runs.",
    citations: [
      cite("w9", "INV-2026-04398_Cardinal.pdf", 2, "Line items — reconciliation", "Three line items totalling USD 4,180.00 do not reconcile to any open purchase-order commitment for this supplier."),
      cite("w10", "INV-2026-04311_Sable.pdf", 1, "Invoice header", "Invoice number INV-2026-04311 matches a document settled on 2026-06-02 for the same supplier and amount."),
      cite("w11", "INV-2026-04260_Halcyon.pdf", 1, "Supplier details", "The stated tax identification number fails checksum validation for the supplier's registered jurisdiction."),
    ],
  },
  {
    match: /pii|personal|gdpr|privacy|sensitive|data protection/i,
    thinking: "Retrieving PII findings · checking masking policy",
    text: "**Sensitive data appears in free text in two contracts.** The ACME MSA carries a signatory's direct email and phone number in the execution block, and the Perrin framework agreement includes a named individual's home address in the notices schedule. Both are masked by policy in the UI and every reveal is audit-logged — but they remain in the source PDFs, so redaction is a document-level fix, not a display one.",
    citations: [
      cite("w12", "ACME_Q3_MSA_countersigned.pdf", 27, "Execution block", "Signed for and on behalf of Meridian Logistics LLC — r.nakamura@meridian.com, +1 202 555 4402."),
      cite("w13", "Framework_Agreement_Perrin.pdf", 30, "Schedule C — Notices", "Personal address of the nominated contact: 118 Cottonwood Lane, Ashburn, VA 20147."),
    ],
  },
];

export const CHAT_DEFAULT_ANSWER: WorkspaceAnswer = {
  match: /.*/,
  thinking: "Searching the corpus · ranking passages",
  text: "Here is what the corpus says on that point. Across the indexed contracts and amendments the recurring commercial themes are a **36-month default term with automatic renewal**, Net 45 payment against a Net 30 policy, and liability carve-outs that leave data-breach exposure uncapped. Those three drive most of the current high-risk scores — ask about any of them and I will cite the specific clauses.",
  citations: [
    cite("w14", "Global_MSA_Amendment_2.pdf", 4, "Section 4.2 — Automatic renewal", "This Agreement shall renew automatically for successive periods of thirty-six (36) months unless either party gives written notice of non-renewal."),
    cite("w15", "ACME_Q3_MSA_countersigned.pdf", 17, "Section 8.3 — Excluded from the cap", "Liability arising from a personal data breach is unlimited in amount."),
  ],
};

export function chatAnswerFor(question: string): WorkspaceAnswer | null {
  if (QA_NO_ANSWER.test(question)) return null;
  return CHAT_ANSWERS.find((a) => a.match.test(question)) ?? CHAT_DEFAULT_ANSWER;
}
