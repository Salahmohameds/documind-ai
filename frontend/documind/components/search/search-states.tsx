"use client";

import { Anim, Shimmer, Stagger } from "@/components/motion";
import { Button } from "@/components/ui/button";
import { SearchIcon, WarningIcon } from "@/components/ui/icons";

/**
 * Everything the palette shows when it is not showing results. Each state is
 * built to the same silhouette — glyph, headline, one supporting line — so
 * moving between them reads as one surface changing its mind, not as three
 * different screens.
 */

function Frame({
  glyph,
  title,
  body,
  tone = "--idle",
  children,
}: {
  glyph: React.ReactNode;
  title: string;
  body: string;
  tone?: "--idle" | "--bad";
  children?: React.ReactNode;
}) {
  return (
    <Anim preset="fade" className="dm-search-state">
      <span
        className="dm-search-state-glyph"
        style={
          tone === "--bad"
            ? {
                color: "var(--bad)",
                background: "var(--bad-soft)",
                borderColor: "var(--bad-border)",
              }
            : undefined
        }
      >
        {glyph}
      </span>
      <span className="dm-search-state-title">{title}</span>
      <span className="dm-search-state-body">{body}</span>
      {children}
    </Anim>
  );
}

/** The first frame after opening, before any response has landed. */
export function SearchSkeleton() {
  return (
    <Stagger gap={0.04} className="dm-search-skeleton" aria-hidden>
      {[0, 1, 2, 3, 4].map((i) => (
        <Anim key={i} preset="row" className="dm-search-skeleton-row">
          <Shimmer delay={i * 0.08} style={{ width: 30, height: 30, borderRadius: 9 }} />
          <span style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
            <Shimmer delay={i * 0.08} style={{ width: `${52 - i * 5}%`, height: 11 }} />
            <Shimmer delay={i * 0.08} style={{ width: `${34 - i * 3}%`, height: 9 }} />
          </span>
        </Anim>
      ))}
    </Stagger>
  );
}

export function SearchNoResults({ query }: { query: string }) {
  return (
    <Frame
      glyph={<SearchIcon size={17} color="var(--text-3)" />}
      title={`No matches for “${query.length > 32 ? `${query.slice(0, 32)}…` : query}”`}
      body="Nothing in your documents, pages, sections, findings or extracted fields matches every word. Try fewer words, or search for a counterparty or clause number."
    />
  );
}

export function SearchError({
  detail,
  code,
  onRetry,
}: {
  detail: string;
  code?: string;
  onRetry: () => void;
}) {
  return (
    <Frame
      tone="--bad"
      glyph={<WarningIcon size={17} color="var(--bad)" />}
      title="Search is unavailable"
      body={detail}
    >
      <span className="dm-search-state-actions">
        <Button size="dm" onClick={onRetry} style={{ height: 32, padding: "0 14px" }}>
          Try again
        </Button>
        {code && (
          <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
            {code}
          </span>
        )}
      </span>
    </Frame>
  );
}
