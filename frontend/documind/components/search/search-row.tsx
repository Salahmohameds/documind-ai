"use client";

import { motion } from "@/components/motion";
import { PALETTE_CURSOR } from "@/lib/motion";
import { v } from "@/lib/design";
import { Highlight } from "@/components/search/search-highlight";
import { KIND_ACTION, type SearchHit } from "@/lib/search/types";
import {
  ChatIcon,
  FileIcon,
  GridIcon,
  HashIcon,
  TagIcon,
  UploadIcon,
  WarningIcon,
} from "@/components/ui/icons";

/**
 * One result. The row answers four questions at a glance — what matched, what
 * kind of thing it is, where it lives, and what Enter will do — which is the
 * whole job of a palette row.
 */

/**
 * Rendered as JSX rather than resolved to a component variable: picking a
 * component during render defeats reconciliation, because a fresh identity
 * each pass reads as a different element type.
 *
 * Pages take the icon of the destination they lead to, so the rail and the
 * palette agree about what "Upload" looks like; everything else takes its
 * entity glyph.
 */
function KindGlyph({ hit, color }: { hit: SearchHit; color: string }) {
  const size = 15;

  if (hit.kind === "page") {
    switch (hit.href) {
      case "/chat":
        return <ChatIcon size={size} color={color} />;
      case "/upload":
        return <UploadIcon size={size} color={color} />;
      case "/documents":
        return <FileIcon size={size} color={color} />;
      default:
        return <GridIcon size={size} color={color} />;
    }
  }

  switch (hit.kind) {
    case "document":
      return <FileIcon size={size} color={color} />;
    case "section":
      return <HashIcon size={size} color={color} />;
    case "finding":
      return <WarningIcon size={size} color={color} />;
    default:
      return <TagIcon size={size} color={color} />;
  }
}

export function SearchRow({
  hit,
  query,
  selected,
  onSelect,
  onActivate,
  registerRef,
}: {
  hit: SearchHit;
  query: string;
  selected: boolean;
  onSelect: () => void;
  onActivate: () => void;
  registerRef: (el: HTMLButtonElement | null) => void;
}) {
  const tone = hit.tone ? v(hit.tone) : "var(--text-3)";

  return (
    <button
      ref={registerRef}
      type="button"
      role="option"
      aria-selected={selected}
      // Pointer *move*, not enter: an unmoved cursor sitting over the list
      // shouldn't fight the arrow keys for the selection.
      onPointerMove={selected ? undefined : onSelect}
      onClick={onActivate}
      className="dm-search-row"
      data-selected={selected || undefined}
    >
      {selected && (
        <motion.span
          layoutId="dm-search-cursor"
          transition={PALETTE_CURSOR}
          aria-hidden
          className="dm-search-cursor"
        />
      )}

      <span
        className="dm-search-glyph"
        style={{
          color: tone,
          background: hit.tone ? v(hit.tone, "-soft") : "var(--surface-2)",
          borderColor: hit.tone ? v(hit.tone, "-border") : "var(--border)",
        }}
      >
        <KindGlyph hit={hit} color={tone} />
      </span>

      <span className="dm-search-body">
        <span className="dm-search-title">
          <Highlight text={hit.title} query={query} />
        </span>

        {(hit.subtitle || hit.snippet) && (
          <span className="dm-search-sub">
            {hit.snippet ? (
              <Highlight text={hit.snippet} query={query} />
            ) : (
              <Highlight text={hit.subtitle ?? ""} query={query} />
            )}
          </span>
        )}

        {/* When a snippet took the second line, the parent still has to be
            visible — otherwise "where does this live" goes unanswered. */}
        {hit.snippet && hit.subtitle && (
          <span className="dm-search-parent">
            <Highlight text={hit.subtitle} query={query} />
          </span>
        )}
      </span>

      <span className="dm-search-tail">
        {hit.also ? <span className="dm-search-chip">+{hit.also} docs</span> : null}
        {hit.meta?.slice(0, hit.also ? 1 : 2).map((m) => (
          <span key={m} className="dm-search-chip">
            {m}
          </span>
        ))}
        {/* Spelled out on the selected row only, so the list stays quiet. */}
        <span className="dm-search-action">{KIND_ACTION[hit.kind]}</span>
      </span>
    </button>
  );
}
