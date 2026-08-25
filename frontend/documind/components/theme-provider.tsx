"use client";

import { useCallback, useSyncExternalStore } from "react";
import { Switch } from "@/components/ui/switch";

export type Theme = "light" | "dark";

const STORAGE_KEY = "documind-theme";

/**
 * `<html data-theme>` is the source of truth — it is set before first paint by
 * the init script below, and read back through useSyncExternalStore so the
 * React tree never has to re-derive it.
 */
const listeners = new Set<() => void>();

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  return () => listeners.delete(onChange);
}

function getSnapshot(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

/** Server render has no DOM; the init script corrects the markup before paint. */
function getServerSnapshot(): Theme {
  return "light";
}

function applyTheme(next: Theme) {
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    /* storage unavailable — the toggle still works for this session */
  }
  listeners.forEach((l) => l());
}

/**
 * Inlined in <head> so the stored theme is applied before first paint.
 * Keep the storage key in sync with STORAGE_KEY above.
 */
export const themeInitScript = `try{var t=localStorage.getItem("${STORAGE_KEY}");if(t!=="dark"&&t!=="light"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme="light";}`;

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const toggleTheme = useCallback(
    () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"),
    [],
  );
  return { theme, toggleTheme };
}

/** The canvas's 30×16 pill switch, as a shadcn Switch. */
export function ThemeSwitch({
  theme,
  onToggle,
}: {
  theme: Theme;
  onToggle?: () => void;
}) {
  return (
    <Switch
      checked={theme === "dark"}
      onCheckedChange={onToggle}
      aria-label="Dark mode"
      className="ml-auto h-4 w-[30px] shrink-0 p-0.5 data-unchecked:bg-[var(--s300)]"
      thumbClassName="size-3 group-data-[size=default]/switch:size-3 group-data-[size=default]/switch:data-checked:translate-x-[14px]"
    />
  );
}
