"use client";

import { useRouter } from "next/navigation";
import { useCallback, useMemo, useRef, useState } from "react";
import { Dialog, VisuallyHidden } from "radix-ui";
import { AnimatePresence, motion } from "@/components/motion";
import { PALETTE_PANEL, PALETTE_RESULTS, PALETTE_SCRIM } from "@/lib/motion";
import type { Simulate } from "@/lib/api";
import { useSearch } from "@/components/search/use-search";
import { SearchRow } from "@/components/search/search-row";
import { SearchError, SearchNoResults, SearchSkeleton } from "@/components/search/search-states";
import { Kbd } from "@/components/search/kbd";
import { ReturnIcon, SearchIcon } from "@/components/ui/icons";

/**
 * The global search palette.
 *
 * Radix's Dialog supplies the parts that are easy to get subtly wrong — focus
 * trap, focus restore on close, `aria-modal`, scroll lock, Escape — while
 * Motion drives the entrance, so neither library is fighting the other. The
 * listbox semantics layered on top (`role="combobox"` on the input,
 * `role="listbox"` on the results) are what let the input keep focus while the
 * arrow keys move a selection somewhere else.
 */

/**
 * Non-happy states are hard to reach by hand, so they are reachable by URL —
 * `?search=slow|error|empty`, matching the `?intro` affordance on the splash.
 * Nothing else reads this, and it costs the UI nothing.
 */
function simulateFromUrl(): Simulate {
  if (typeof window === "undefined") return "ok";
  const v = new URLSearchParams(window.location.search).get("search");
  return v === "slow" || v === "error" || v === "empty" ? v : "ok";
}

export function SearchDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="dm-search-scrim"
                variants={PALETTE_SCRIM}
                initial="hidden"
                animate="show"
                exit="exit"
              />
            </Dialog.Overlay>
            <SearchPalette onClose={onClose} />
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}

/**
 * All palette state lives here, one level below the dialog, and only exists
 * while it is open. That is deliberate: closing unmounts it, so the query, the
 * cursor and any in-flight request reset by construction rather than by an
 * effect watching `open` and undoing them afterwards. Opening is therefore
 * always a fresh search — which is what ⌘K means to anyone pressing it.
 */
function SearchPalette({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  // Read once per open: the URL cannot change underneath an open dialog.
  const [simulate] = useState<Simulate>(simulateFromUrl);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const rowRefs = useRef(new Map<string, HTMLButtonElement>());

  const { data, flat, status, error, typing, retry } = useSearch(query, simulate);

  // Each new result set starts at the top; leaving the cursor where it was
  // would silently point it at something the user never asked for. Adjusting
  // during render rather than in an effect means the first paint of the new
  // results already has the right row selected — there is no frame showing a
  // stale one.
  const [renderedFor, setRenderedFor] = useState(data);
  if (data !== renderedFor) {
    setRenderedFor(data);
    setSelected(0);
  }

  const activate = useCallback(
    (href: string) => {
      onClose();
      router.push(href);
    },
    [onClose, router],
  );

  const move = useCallback(
    (delta: number) => {
      if (flat.length === 0) return;
      setSelected((i) => {
        // Wrapping keeps a long list reachable from either end.
        const next = (i + delta + flat.length) % flat.length;
        rowRefs.current.get(flat[next].id)?.scrollIntoView({ block: "nearest" });
        return next;
      });
    },
    [flat],
  );

  const onKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        move(1);
        break;
      case "ArrowUp":
        e.preventDefault();
        move(-1);
        break;
      case "Home":
        if (flat.length) {
          e.preventDefault();
          setSelected(0);
          listRef.current?.scrollTo({ top: 0 });
        }
        break;
      case "End":
        if (flat.length) {
          e.preventDefault();
          setSelected(flat.length - 1);
          rowRefs.current.get(flat[flat.length - 1].id)?.scrollIntoView({ block: "nearest" });
        }
        break;
      case "Enter": {
        const hit = flat[selected];
        if (hit) {
          e.preventDefault();
          activate(hit.href);
        }
        break;
      }
    }
  };

  const activeId = flat[selected]?.id;
  const showSkeleton = status === "loading";
  const showError = status === "error" && error !== null;
  const noResults =
    !showError && !showSkeleton && data !== null && flat.length === 0 && !data.suggested;

  // Keyed on the query the *response* was for, so the crossfade fires when the
  // results actually change rather than on every keystroke.
  const resultsKey = useMemo(
    () => (showError ? "error" : showSkeleton ? "skeleton" : (data?.query ?? "")),
    [showError, showSkeleton, data],
  );

  return (
    <Dialog.Content
      asChild
      forceMount
      aria-describedby={undefined}
      // Radix would focus the first tabbable node; the input is the only thing
      // anyone wants focused here.
      onOpenAutoFocus={(e) => {
        e.preventDefault();
        inputRef.current?.focus();
      }}
    >
      <motion.div
        className="dm-search-panel"
        variants={PALETTE_PANEL}
        initial="hidden"
        animate="show"
        exit="exit"
        onKeyDown={onKeyDown}
      >
        <VisuallyHidden.Root>
          <Dialog.Title>Search DocuMind</Dialog.Title>
        </VisuallyHidden.Root>

        {/* Input ------------------------------------------------------- */}
        <div className="dm-search-field">
          <SearchIcon size={17} color="var(--text-3)" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search documents, pages, sections…"
            className="dm-search-input"
            role="combobox"
            aria-expanded
            aria-controls="dm-search-listbox"
            aria-activedescendant={activeId ? `dm-search-opt-${activeId}` : undefined}
            aria-autocomplete="list"
            autoComplete="off"
            spellCheck={false}
            enterKeyHint="go"
          />
          {/* A thin travelling bar rather than a spinner: it says "still
              working" without implying the list below has gone stale. */}
          {(status === "reloading" || typing) && <span className="dm-search-pulse" />}
          <button
            type="button"
            className="dm-search-esc"
            onClick={onClose}
            aria-label="Close search"
          >
            Esc
          </button>
        </div>

        {/* Results ----------------------------------------------------- */}
        <div
          ref={listRef}
          className="dm-search-list"
          id="dm-search-listbox"
          role="listbox"
          aria-label="Search results"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={resultsKey}
              variants={PALETTE_RESULTS}
              initial="hidden"
              animate="show"
              exit="exit"
            >
              {showError ? (
                <SearchError detail={error.detail} code={error.code} onRetry={retry} />
              ) : showSkeleton ? (
                <SearchSkeleton />
              ) : noResults ? (
                <SearchNoResults query={data?.query ?? query} />
              ) : (
                data?.groups.map((group) => (
                  <div key={group.kind} className="dm-search-group" role="group">
                    <div className="dm-search-group-head">
                      <span>
                        {data.suggested
                          ? group.kind === "document"
                            ? "Recent documents"
                            : "Jump to"
                          : group.label}
                      </span>
                      {group.more > 0 && (
                        <span className="dm-search-group-more">+{group.more} more</span>
                      )}
                    </div>

                    {group.hits.map((hit) => {
                      const index = flat.indexOf(hit);
                      return (
                        <div key={hit.id} id={`dm-search-opt-${hit.id}`}>
                          <SearchRow
                            hit={hit}
                            // Suggestions matched nothing, so nothing should
                            // be highlighted as if it had.
                            query={data.suggested ? "" : data.query}
                            selected={index === selected}
                            onSelect={() => setSelected(index)}
                            onActivate={() => activate(hit.href)}
                            registerRef={(el) => {
                              if (el) rowRefs.current.set(hit.id, el);
                              else rowRefs.current.delete(hit.id);
                            }}
                          />
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer ------------------------------------------------------ */}
        <div className="dm-search-footer">
          <span className="dm-search-hints">
            <span className="dm-search-hint">
              <Kbd>↑</Kbd>
              <Kbd>↓</Kbd>
              navigate
            </span>
            <span className="dm-search-hint">
              <Kbd>
                <ReturnIcon size={11} />
              </Kbd>
              open
            </span>
            <span className="dm-search-hint dm-hide-sm">
              <Kbd>Esc</Kbd>
              close
            </span>
          </span>

          <span className="dm-search-count">
            {showError
              ? "—"
              : data?.suggested
                ? "Start typing to search"
                : data
                  ? `${data.total} result${data.total === 1 ? "" : "s"} · ${data.tookMs}ms`
                  : "Searching…"}
          </span>
        </div>
      </motion.div>
    </Dialog.Content>
  );
}
