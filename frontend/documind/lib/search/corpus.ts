import { STATUS, riskTone } from "@/lib/design";
import { QA_PAGES, WORKSPACE } from "@/lib/mock/data";
import { buildDetail } from "@/lib/mock/data";
import type { DocumentSummary } from "@/lib/types";
import type { Indexed } from "@/lib/search/rank";

/**
 * The searchable corpus.
 *
 * Everything indexed here is content the product already has and already
 * renders somewhere; every `href` is a route that already exists. Nothing is
 * fabricated to pad the results.
 *
 * The index is built once and cached. It is deliberately built *behind* the
 * `searchWorkspace` seam in `lib/api.ts`, never in a component — so when a
 * real search service arrives, the index and this file are what get deleted,
 * and no UI moves.
 */

/* -- Navigation destinations -------------------------------------------- */

/**
 * Mirrors the rail in `components/shell/sidebar.tsx`. Kept as data rather than
 * imported from the sidebar so search doesn't drag a client component (and
 * its icons) into the index.
 */
const PAGES: { title: string; href: string; blurb: string; keywords: string }[] = [
  {
    title: "Dashboard",
    href: "/dashboard",
    blurb: "Operations overview — volume, exceptions, risk and flagged documents.",
    keywords: "home overview metrics kpi analytics stats reporting",
  },
  {
    title: "Ask",
    href: "/chat",
    blurb: "Grounded answers across every document in the workspace, with citations.",
    keywords: "chat question answer rag search ai assistant query",
  },
  {
    title: "Upload",
    href: "/upload",
    blurb: "Ingest documents and watch them through the seven pipeline stages.",
    keywords: "import add new file ingest queue pipeline drop",
  },
  {
    title: "Documents",
    href: "/documents",
    blurb: "The full document library — filter by type, status and risk.",
    keywords: "library files list all browse archive",
  },
];

/* -- Builders ------------------------------------------------------------ */

function lower(e: Omit<Indexed, "lc">): Indexed {
  return {
    ...e,
    lc: {
      title: e.title.toLowerCase(),
      subtitle: (e.subtitle ?? "").toLowerCase(),
      body: (e.body ?? "").toLowerCase(),
      keywords: (e.keywords ?? "").toLowerCase(),
    },
  };
}

function pageEntries(): Indexed[] {
  return PAGES.map((p, i) =>
    lower({
      id: `page:${p.href}`,
      kind: "page",
      title: p.title,
      subtitle: WORKSPACE.org,
      body: p.blurb,
      keywords: p.keywords,
      href: p.href,
      // Preserves rail order when several pages tie.
      weight: (PAGES.length - i) * 2,
    }),
  );
}

function documentEntries(docs: DocumentSummary[]): Indexed[] {
  // Recency as a tie-breaker, normalised so it never outweighs a title match.
  const newest = Math.max(...docs.map((d) => d.uploadedAt), 1);
  const oldest = Math.min(...docs.map((d) => d.uploadedAt), 0);
  const span = Math.max(1, newest - oldest);

  return docs.map((d) =>
    lower({
      id: `document:${d.id}`,
      kind: "document",
      title: d.name,
      subtitle: `${d.type} · ${d.counterparty}`,
      body: `${d.verdict} ${d.uploaded}`,
      // The id and extension are searchable but never shown as the match.
      keywords: `${d.id} ${d.ext} ${d.status} ${d.type} ${d.counterparty}`,
      href: `/documents/${d.id}`,
      meta: [STATUS[d.status].label, `${d.pages} pages`],
      tone: d.risk === null ? STATUS[d.status].tone : riskTone(d.risk),
      weight: ((d.uploadedAt - oldest) / span) * 12,
    }),
  );
}

/**
 * Clause-level content from the document reader.
 *
 * The reader serves the same page fixtures for any document (see `getPage` in
 * `lib/api.ts`), so a section genuinely resolves in any document long enough
 * to contain that page. Rather than emit the same clause once per document —
 * which would flood the palette with duplicates — each section is indexed once
 * and anchored to a single stable document: the longest one that contains the
 * page, which is the document a reader is most likely to be opened on.
 */
function sectionEntries(docs: DocumentSummary[]): Indexed[] {
  const entries: Indexed[] = [];

  for (const [pageKey, blocks] of Object.entries(QA_PAGES)) {
    const page = Number(pageKey);

    const host = docs
      .filter((d) => d.pages >= page && d.status === "completed")
      .sort((a, b) => b.pages - a.pages || a.name.localeCompare(b.name))[0];
    if (!host) continue;

    for (const block of blocks) {
      entries.push(
        lower({
          id: `section:${page}:${block.heading}`,
          kind: "section",
          // Headings arrive as "7.1  Invoicing and payment" (double space).
          title: block.heading.replace(/\s{2,}/g, " ").trim(),
          subtitle: `${host.name} · page ${page}`,
          body: block.text,
          keywords: `clause section page ${page}`,
          href: `/qa/${host.id}?page=${page}`,
          meta: [`p.${page}`],
        }),
      );
    }
  }

  return entries;
}

/**
 * Findings and extracted fields, which `buildDetail` derives per document.
 *
 * Only completed documents have either — anything queued, processing or failed
 * was never analysed, so indexing it would promise a result that isn't there.
 * Capped at the most recent documents because detail is derived on demand and
 * there is no reason to pay for the whole library up front.
 */
const DETAIL_DEPTH = 14;

function detailEntries(docs: DocumentSummary[]): Indexed[] {
  const entries: Indexed[] = [];

  const analysed = docs
    .filter((d) => d.status === "completed")
    .sort((a, b) => b.uploadedAt - a.uploadedAt)
    .slice(0, DETAIL_DEPTH);

  for (const doc of analysed) {
    const detail = buildDetail(doc);

    for (const f of detail.findings) {
      entries.push(
        lower({
          id: `finding:${doc.id}:${f.id}`,
          kind: "finding",
          title: f.title,
          subtitle: `${doc.name} · page ${f.page}`,
          body: f.description,
          keywords: `risk finding ${f.severity} exception`,
          href: `/documents/${doc.id}`,
          meta: [f.severity],
          tone: f.severity === "High" ? "--bad" : f.severity === "Medium" ? "--warn" : "--idle",
        }),
      );
    }

    for (const field of detail.fields) {
      entries.push(
        lower({
          id: `field:${doc.id}:${field.key}`,
          kind: "field",
          title: field.key,
          subtitle: `${doc.name} · page ${field.page}`,
          body: field.value,
          keywords: `extracted field value ${field.value}`,
          href: `/documents/${doc.id}`,
          meta: [`${field.confidence}%`],
        }),
      );
    }
  }

  return entries;
}

/* -- Cache --------------------------------------------------------------- */

let cache: Indexed[] | null = null;

/**
 * Built lazily on the first search and reused after that. Deriving detail for
 * every document is the expensive part, so it must not run per keystroke.
 */
export function corpus(docs: DocumentSummary[]): Indexed[] {
  if (cache) return cache;
  cache = [
    ...pageEntries(),
    ...documentEntries(docs),
    ...sectionEntries(docs),
    ...detailEntries(docs),
  ];
  return cache;
}

/**
 * Called by any mutation that changes what exists — upload, delete, reprocess.
 * Without this the palette would keep offering a document that was just
 * deleted, and would never surface one that was just added.
 */
export function invalidateCorpus(): void {
  cache = null;
}

/** Default suggestions for the empty query: where you can go, what's newest. */
export function suggestions(docs: DocumentSummary[]): Indexed[] {
  const recent = documentEntries(
    [...docs].sort((a, b) => b.uploadedAt - a.uploadedAt).slice(0, 4),
  );
  return [...pageEntries(), ...recent];
}
