"use client";

import { Fragment, useMemo } from "react";
import { matchRanges, tokenize } from "@/lib/search/rank";

/**
 * Marks the parts of `text` the query actually matched.
 *
 * This is what turns a list of titles into an explanation: the user can see
 * *why* each row is here without reading it. Rendered as `<mark>` so it also
 * carries the meaning to assistive tech, restyled off the browser default.
 */
export function Highlight({ text, query }: { text: string; query: string }) {
  const ranges = useMemo(() => matchRanges(text, tokenize(query)), [text, query]);

  if (ranges.length === 0) return <>{text}</>;

  const parts: React.ReactNode[] = [];
  let at = 0;

  ranges.forEach(([start, end], i) => {
    if (start > at) parts.push(<Fragment key={`t${i}`}>{text.slice(at, start)}</Fragment>);
    parts.push(
      <mark
        key={`m${i}`}
        style={{
          background: "var(--accent-soft)",
          color: "var(--accent)",
          borderRadius: 3,
          padding: "0 1px",
          // The palette sets its own colour per line; keep the weight relative
          // so a highlight inside a title stays a title.
          fontWeight: "inherit",
        }}
      >
        {text.slice(start, end)}
      </mark>,
    );
    at = end;
  });

  if (at < text.length) parts.push(<Fragment key="tail">{text.slice(at)}</Fragment>);
  return <>{parts}</>;
}
