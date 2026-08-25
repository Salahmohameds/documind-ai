"use client";

import { useSyncExternalStore } from "react";
import { motion } from "@/components/motion";
import { TAP } from "@/lib/motion";
import { Kbd } from "@/components/search/kbd";
import { useSearchPalette } from "@/components/search/search-provider";
import { Button } from "@/components/ui/button";
import { SearchIcon } from "@/components/ui/icons";

/**
 * The topbar entry point. Two shapes of the same control: a full bar where
 * there is room, and an icon button where there isn't.
 *
 * It advertises its own shortcut, which is the only reason anyone learns a
 * shortcut exists.
 */

/**
 * ⌘ on Apple hardware, Ctrl everywhere else. The server has no navigator, so
 * it renders "Ctrl" and the client corrects it after hydration — the same
 * pattern `useTheme` uses for a value only the browser knows.
 */
const subscribeNever = () => () => {};
const readCmdKey = () =>
  /mac|iphone|ipad|ipod/i.test(navigator.platform || navigator.userAgent) ? "⌘" : "Ctrl";
const readCmdKeyOnServer = () => "Ctrl";

function useCmdKey(): string {
  return useSyncExternalStore(subscribeNever, readCmdKey, readCmdKeyOnServer);
}

export function SearchTrigger() {
  const { openSearch } = useSearchPalette();
  const cmd = useCmdKey();

  return (
    <motion.button
      type="button"
      onClick={openSearch}
      whileHover={TAP.hover}
      whileTap={TAP.press}
      className="dm-search-trigger"
      aria-label="Search DocuMind"
      aria-keyshortcuts="Control+K Meta+K"
    >
      <SearchIcon size={14} color="var(--text-3)" />
      <span className="dm-search-trigger-label">Search anything…</span>
      <span className="dm-search-trigger-keys">
        <Kbd>{cmd}</Kbd>
        <Kbd>K</Kbd>
      </span>
    </motion.button>
  );
}

/** The narrow-screen form — same action, no room for the bar. */
export function SearchTriggerCompact() {
  const { openSearch } = useSearchPalette();
  return (
    <Button
      variant="ghost"
      size="icon-lg"
      className="rounded-full sm:hidden"
      aria-label="Search DocuMind"
      onClick={openSearch}
    >
      <SearchIcon size={17} color="var(--text-2)" />
    </Button>
  );
}
