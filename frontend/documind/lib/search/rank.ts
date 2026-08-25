import type { SearchKind } from "@/lib/search/types";

/**
 * Matching and scoring. Pure functions over plain strings — no React, no data
 * access — so the ranking can be reasoned about (and later replaced by a real
 * search service's scores) without touching anything else.
 */

/** A corpus entry, as the index stores it. */
export type Indexed = {
  id: string;
  kind: SearchKind;
  title: string;
  subtitle?: string;
  /** Free text searched at low weight — clause bodies, descriptions, values. */
  body?: string;
  /** Extra terms that should match but are never displayed (ids, aliases). */
  keywords?: string;
  href: string;
  meta?: string[];
  tone?: import("@/lib/design").Tone;
  /** Tie-breaker within a kind — recency for documents, nav order for pages. */
  weight?: number;
  /** Lowercased once at build time; matching never re-lowercases. */
  lc: { title: string; subtitle: string; body: string; keywords: string };
};

/**
 * Field weights. The gap between title and body is deliberately wide: a query
 * that names a document should never be buried under a clause that happens to
 * mention the same word twenty times.
 */
const FIELD = {
  titleExact: 260,
  titlePrefix: 150,
  titleWord: 120,
  titleAny: 70,
  subtitleWord: 46,
  subtitleAny: 30,
  keyword: 40,
  bodyWord: 20,
  bodyAny: 10,
} as const;

/**
 * Nudges between kinds of equal textual strength. Pages win narrowly because
 * "documents" as a query almost always means "take me to the Documents page",
 * not "find a document with 'documents' in its name".
 */
const KIND_WEIGHT: Record<SearchKind, number> = {
  page: 1.25,
  document: 1.12,
  section: 1,
  finding: 0.96,
  field: 0.9,
};

export function tokenize(query: string): string[] {
  return query
    .toLowerCase()
    .split(/[\s,]+/)
    .map((t) => t.trim())
    .filter((t) => t.length > 0)
    .slice(0, 8);
}

/** True when `hay` contains `term` at the start of some word. */
function hasWordStart(hay: string, term: string): boolean {
  let i = hay.indexOf(term);
  while (i !== -1) {
    if (i === 0 || !/[a-z0-9]/.test(hay[i - 1])) return true;
    i = hay.indexOf(term, i + 1);
  }
  return false;
}

/** The best score any one field yields for a single term, or 0 for no match. */
function scoreTerm(entry: Indexed, term: string): number {
  const { lc } = entry;

  if (lc.title === term) return FIELD.titleExact;
  if (lc.title.startsWith(term)) return FIELD.titlePrefix;
  if (hasWordStart(lc.title, term)) return FIELD.titleWord;
  if (lc.title.includes(term)) return FIELD.titleAny;

  if (lc.keywords.includes(term)) return FIELD.keyword;

  if (lc.subtitle) {
    if (hasWordStart(lc.subtitle, term)) return FIELD.subtitleWord;
    if (lc.subtitle.includes(term)) return FIELD.subtitleAny;
  }

  if (lc.body) {
    if (hasWordStart(lc.body, term)) return FIELD.bodyWord;
    if (lc.body.includes(term)) return FIELD.bodyAny;
  }

  return 0;
}

/**
 * Every term must match somewhere (AND), which is what makes adding a word
 * narrow the list instead of widening it. Returns 0 when the entry is out.
 */
export function scoreEntry(entry: Indexed, terms: string[]): number {
  let total = 0;
  for (const term of terms) {
    const s = scoreTerm(entry, term);
    if (s === 0) return 0;
    total += s;
  }

  // Specificity: among equally-matching titles, prefer the shorter one.
  const brevity = Math.max(0, 40 - entry.title.length) * 0.4;
  // Whole-query phrase match on the title is a strong signal.
  const phrase = terms.length > 1 && entry.lc.title.includes(terms.join(" ")) ? 60 : 0;

  return (total + brevity + phrase) * KIND_WEIGHT[entry.kind] + (entry.weight ?? 0);
}

/* -- Highlighting -------------------------------------------------------- */

export type Range = [start: number, end: number];

/**
 * Character ranges in `text` covered by any term, merged so overlapping terms
 * ("pay" + "payment") render as one highlight rather than nested ones.
 */
export function matchRanges(text: string, terms: string[]): Range[] {
  if (terms.length === 0) return [];
  const lc = text.toLowerCase();
  const found: Range[] = [];

  for (const term of terms) {
    let i = lc.indexOf(term);
    while (i !== -1) {
      found.push([i, i + term.length]);
      i = lc.indexOf(term, i + term.length);
      // A term can appear many times; cap so a pathological body can't blow up.
      if (found.length > 200) break;
    }
  }

  if (found.length === 0) return [];
  found.sort((a, b) => a[0] - b[0]);

  const merged: Range[] = [found[0]];
  for (const [s, e] of found.slice(1)) {
    const last = merged[merged.length - 1];
    if (s <= last[1]) last[1] = Math.max(last[1], e);
    else merged.push([s, e]);
  }
  return merged;
}

/**
 * A window of `body` around the first match, so the row shows the sentence the
 * user's words actually appear in rather than the opening of the clause.
 */
export function snippetAround(body: string, terms: string[], width = 132): string | undefined {
  if (!body) return undefined;
  const lc = body.toLowerCase();

  let at = -1;
  for (const term of terms) {
    const i = lc.indexOf(term);
    if (i !== -1 && (at === -1 || i < at)) at = i;
  }
  if (at === -1) return body.length > width ? `${body.slice(0, width).trimEnd()}…` : body;

  // Start a little before the match, then snap to a word boundary.
  let start = Math.max(0, at - Math.floor(width / 3));
  if (start > 0) {
    const space = body.indexOf(" ", start);
    if (space !== -1 && space < at) start = space + 1;
  }
  const end = Math.min(body.length, start + width);

  return `${start > 0 ? "…" : ""}${body.slice(start, end).trim()}${end < body.length ? "…" : ""}`;
}
