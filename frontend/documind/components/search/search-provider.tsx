"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { SearchDialog } from "@/components/search/search-dialog";

/**
 * Owns the one piece of global state search needs — whether the palette is
 * open — and the shortcut that toggles it.
 *
 * Mounted in the dashboard layout rather than the root layout, so `/login` and
 * `/register` never load the palette, never bind ⌘K, and are unaffected by any
 * of this.
 */

type SearchContext = {
  open: boolean;
  openSearch: () => void;
  closeSearch: () => void;
};

const Ctx = createContext<SearchContext | null>(null);

export function useSearchPalette(): SearchContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSearchPalette must be used inside <SearchProvider>");
  return ctx;
}

/** Typing into a field should never be hijacked by a bare shortcut. */
function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  return (
    el.tagName === "INPUT" ||
    el.tagName === "TEXTAREA" ||
    el.tagName === "SELECT" ||
    el.isContentEditable
  );
}

export function SearchProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const openSearch = useCallback(() => setOpen(true), []);
  const closeSearch = useCallback(() => setOpen(false), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const cmdK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k";
      if (cmdK) {
        e.preventDefault();
        // Toggling — rather than always opening — is what stops a second ⌘K
        // from stacking another dialog on the first.
        setOpen((v) => !v);
        return;
      }
      // "/" is the other muscle-memory opener, but only when the user isn't
      // already typing somewhere.
      if (e.key === "/" && !isTypingTarget(e.target) && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setOpen(true);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const value = useMemo(
    () => ({ open, openSearch, closeSearch }),
    [open, openSearch, closeSearch],
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      <SearchDialog open={open} onClose={closeSearch} />
    </Ctx.Provider>
  );
}
