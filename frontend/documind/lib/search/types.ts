import type { Tone } from "@/lib/design";

/**
 * What global search can return. Each kind maps to a real entity that already
 * exists in the product and to a route that already exists in the app — there
 * are no invented result types here.
 */
export type SearchKind =
  /** A file in the library. → /documents/[id] */
  | "document"
  /** A destination in the product's own navigation. → its nav route */
  | "page"
  /** A clause/heading in the document reader. → /qa/[id]?page=n */
  | "section"
  /** A risk finding raised against a document. → /documents/[id] */
  | "finding"
  /** An extracted field value. → /documents/[id] */
  | "field";

export type SearchHit = {
  /** Stable and unique across the whole corpus — also the React key. */
  id: string;
  kind: SearchKind;
  /** The primary label. Matches here outrank matches anywhere else. */
  title: string;
  /** Where this lives: parent document, page number, workspace area. */
  subtitle?: string;
  /** The matching text, already windowed around the hit. */
  snippet?: string;
  /** Short chips — type, status, severity. Kept to two or fewer. */
  meta?: string[];
  /** Colours the kind glyph when the entity carries a status. */
  tone?: Tone;
  /** A real route. Never synthesised. */
  href: string;
  /**
   * How many *other* documents carry this same finding or field. The shared
   * analysis fixtures mean a clause like "Automatic renewal detected" is
   * genuinely raised against many documents; the palette shows it once and
   * counts the rest rather than repeating the row.
   */
  also?: number;
  score: number;
};

export type SearchGroup = {
  kind: SearchKind;
  label: string;
  hits: SearchHit[];
  /** Hits that matched but were trimmed from this group. */
  more: number;
};

export type SearchResponse = {
  query: string;
  groups: SearchGroup[];
  total: number;
  /** Round-trip in ms, shown in the footer — honest about where time goes. */
  tookMs: number;
  /**
   * True when the query was empty and these are default suggestions rather
   * than matches, so the UI can label the groups differently.
   */
  suggested: boolean;
};

/** Display order and labels. Also the order groups render in. */
export const KIND_LABEL: Record<SearchKind, string> = {
  page: "Pages",
  document: "Documents",
  section: "Sections",
  finding: "Findings",
  field: "Extracted fields",
};

export const KIND_ORDER: SearchKind[] = ["page", "document", "section", "finding", "field"];

/** What Enter does, spelled out on the selected row so there's no guessing. */
export const KIND_ACTION: Record<SearchKind, string> = {
  page: "Go to page",
  document: "Open document",
  section: "Open in reader",
  finding: "View finding",
  field: "View extraction",
};
