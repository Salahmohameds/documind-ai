/**
 * Document-service access, shared by the routes that need the whole library.
 *
 * `GET /documents` upstream takes only `page` and `page_size` — it cannot
 * search, filter or sort. Rather than push that limitation into the UI (which
 * would filter one page at a time and report wrong totals), this module folds
 * the library in here and the route applies the query to the complete set.
 *
 * That is a deliberate stopgap: the correct home for search/filter/sort is a
 * SQL `WHERE`/`ORDER BY` in document-service. `MAX_PAGES` is the ceiling that
 * keeps this honest — past it, the fold is refused rather than silently
 * truncated, because a truncated fold would report totals that are simply wrong.
 */

import { BackendError, call, envelope } from "@/lib/server/backend";
import type { DocumentDetail, DocumentSummary } from "@/lib/types";

/** The largest page document-service will serve. */
const UPSTREAM_PAGE_SIZE = 100;

/** 20 × 100 = 20 000 documents. Beyond this the fold must not be attempted. */
const MAX_PAGES = 20;

type UpstreamPage = {
  rows: DocumentSummary[];
  total: number;
  unfilteredTotal: number;
  page: number;
  pageSize: number;
  pageCount: number;
};

export type DocumentQueryParams = {
  search: string;
  type: string;
  status: string;
  sortKey: SortKey;
  sortDir: "asc" | "desc";
  page: number;
  pageSize: number;
};

export type SortKey = "name" | "type" | "status" | "risk" | "pages" | "uploadedAt";

const SORT_KEYS: SortKey[] = ["name", "type", "status", "risk", "pages", "uploadedAt"];

export function parseDocumentQuery(url: URL): DocumentQueryParams {
  const sortKey = url.searchParams.get("sort") ?? "uploadedAt";
  const pageSize = clamp(Number(url.searchParams.get("pageSize")) || 10, 1, UPSTREAM_PAGE_SIZE);
  return {
    search: (url.searchParams.get("search") ?? "").trim().toLowerCase(),
    type: url.searchParams.get("type") ?? "All",
    status: url.searchParams.get("status") ?? "All",
    sortKey: (SORT_KEYS as string[]).includes(sortKey) ? (sortKey as SortKey) : "uploadedAt",
    sortDir: url.searchParams.get("dir") === "asc" ? "asc" : "desc",
    page: Math.max(1, Number(url.searchParams.get("page")) || 1),
    pageSize,
  };
}

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, Math.round(n)));
}

/** Every document in the library, in upstream order (newest first). */
export async function fetchAllDocuments(signal?: AbortSignal): Promise<DocumentSummary[]> {
  const first = await fetchPage(1, signal);
  const pageCount = Math.max(1, Math.ceil(first.total / UPSTREAM_PAGE_SIZE));

  if (pageCount > MAX_PAGES) {
    throw new BackendError(
      envelope(
        "Library too large to list",
        `The library holds ${first.total} documents. Searching and sorting are still applied in the frontend, ` +
          `which supports up to ${MAX_PAGES * UPSTREAM_PAGE_SIZE}. Move filtering into document-service to lift this.`,
        "ERR_LIBRARY_TOO_LARGE",
        false,
      ),
      507,
    );
  }

  if (pageCount === 1) return first.rows;

  const rest = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, i) => fetchPage(i + 2, signal)),
  );
  return [...first.rows, ...rest.flatMap((p) => p.rows)];
}

function fetchPage(page: number, signal?: AbortSignal): Promise<UpstreamPage> {
  return call<UpstreamPage>(
    "documents",
    `/documents?page=${page}&page_size=${UPSTREAM_PAGE_SIZE}`,
    { signal },
  );
}

/** Applies search, filters, sort and pagination to a folded library. */
export function applyQuery(all: DocumentSummary[], q: DocumentQueryParams) {
  const filtered = all.filter(
    (d) =>
      (q.type === "All" || d.type === q.type) &&
      (q.status === "All" || d.status === q.status) &&
      (q.search === "" ||
        d.name.toLowerCase().includes(q.search) ||
        d.id.toLowerCase().includes(q.search) ||
        d.counterparty.toLowerCase().includes(q.search)),
  );

  const sign = q.sortDir === "asc" ? 1 : -1;
  const sorted = [...filtered].sort((a, b) => {
    const av = a[q.sortKey] ?? -1;
    const bv = b[q.sortKey] ?? -1;
    if (typeof av === "string" && typeof bv === "string") return sign * av.localeCompare(bv);
    return sign * (Number(av) - Number(bv));
  });

  const pageCount = Math.max(1, Math.ceil(sorted.length / q.pageSize));
  const page = Math.min(q.page, pageCount);

  return {
    rows: sorted.slice((page - 1) * q.pageSize, page * q.pageSize),
    total: sorted.length,
    unfilteredTotal: all.length,
    page,
    pageSize: q.pageSize,
    pageCount,
  };
}

/**
 * One document, for server components that only need its name for a title.
 *
 * Returns null instead of throwing: a metadata function must not take a page
 * down because a service was briefly unreachable, and a missing title degrades
 * to the generic one.
 */
export async function fetchDocument(id: string): Promise<DocumentDetail | null> {
  try {
    return await call<DocumentDetail>(
      "documents",
      `/documents/${encodeURIComponent(id)}`,
    );
  } catch {
    return null;
  }
}
