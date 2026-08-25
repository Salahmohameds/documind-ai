"use client";

import { useCallback, useEffect, useSyncExternalStore, type ReactNode } from "react";

const STORAGE_KEY = "documind:sidebar-collapsed";
/** Below this the rail can't share the row with content, so it becomes an overlay. */
const NARROW_QUERY = "(max-width: 1023px)";

/**
 * The rail's state lives in a tiny external store rather than React state:
 * `useSyncExternalStore` reads `localStorage` and `matchMedia` without a
 * post-mount `setState`, and its server snapshot keeps hydration honest.
 *
 * Two independent flags, because they answer different questions:
 *  - `collapsed` — the user's saved preference, and what governs wide screens.
 *  - `overlayOpen` — session-only, and what governs narrow ones, where the rail
 *    floats over the content instead of displacing it. A saved "expanded" must
 *    not force the overlay open on a phone, hence the split.
 */

const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/* -- collapsed (persisted) ---------------------------------------------- */

let collapsedSnapshot: boolean | null = null;

function getCollapsed(): boolean {
  if (collapsedSnapshot === null) {
    try {
      collapsedSnapshot = window.localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      collapsedSnapshot = false;
    }
  }
  return collapsedSnapshot;
}

function setCollapsed(next: boolean) {
  collapsedSnapshot = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
  } catch {
    /* storage can be unavailable — the in-memory value still applies */
  }
  emit();
}

/* -- overlayOpen (session only) ----------------------------------------- */

let overlayOpen = false;

function getOverlayOpen(): boolean {
  return overlayOpen;
}

export function setOverlayOpen(next: boolean) {
  if (overlayOpen === next) return;
  overlayOpen = next;
  emit();
}

/* -- narrow (viewport) --------------------------------------------------- */

let narrowSnapshot: boolean | null = null;

function subscribeNarrow(listener: () => void) {
  const mql = window.matchMedia(NARROW_QUERY);
  const onChange = () => {
    narrowSnapshot = mql.matches;
    // Leaving narrow mode drops any overlay that was open.
    if (!mql.matches) overlayOpen = false;
    listener();
  };
  mql.addEventListener("change", onChange);
  listeners.add(listener);
  return () => {
    mql.removeEventListener("change", onChange);
    listeners.delete(listener);
  };
}

function getNarrow(): boolean {
  if (narrowSnapshot === null) narrowSnapshot = window.matchMedia(NARROW_QUERY).matches;
  return narrowSnapshot;
}

/** The server can't measure a viewport, so it renders the wide, expanded rail. */
const serverFalse = () => false;

export function useSidebar() {
  const narrow = useSyncExternalStore(subscribeNarrow, getNarrow, serverFalse);
  const stored = useSyncExternalStore(subscribe, getCollapsed, serverFalse);
  const open = useSyncExternalStore(subscribe, getOverlayOpen, serverFalse);

  const toggle = useCallback(() => {
    if (getNarrow()) setOverlayOpen(!getOverlayOpen());
    else setCollapsed(!getCollapsed());
  }, []);

  return {
    /** Whether the rail currently renders in its icon-only form. */
    collapsed: narrow ? !open : stored,
    narrow,
    /** True only when the rail is floating above the content. */
    overlay: narrow && open,
    toggle,
  };
}

/** Binds `[` to the toggle, the shortcut most shells use for a side rail. */
export function SidebarProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "[") {
        e.preventDefault();
        if (getNarrow()) setOverlayOpen(!getOverlayOpen());
        else setCollapsed(!getCollapsed());
      }
      if (e.key === "Escape" && getNarrow()) setOverlayOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return <>{children}</>;
}

export function ChevronsLeftIcon({ size = 15, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m11 17-5-5 5-5" />
      <path d="m18 17-5-5 5-5" />
    </svg>
  );
}
