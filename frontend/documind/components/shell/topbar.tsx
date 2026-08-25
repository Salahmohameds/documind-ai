"use client";

import { AccountMenu } from "@/components/shell/account-menu";
import { ChevronsLeftIcon, useSidebar } from "@/components/shell/sidebar-state";
import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { BellIcon, MoonIcon, SunIcon } from "@/components/ui/icons";
import { SearchTrigger, SearchTriggerCompact } from "@/components/search/search-trigger";
import { AnimatePresence, motion } from "@/components/motion";
import { SPRING } from "@/lib/motion";

export function Topbar() {
  const { theme, toggleTheme } = useTheme();
  const { collapsed, toggle } = useSidebar();

  return (
    <div className="flex flex-none items-center gap-2 border-b border-border bg-[var(--surface)] px-4 py-2.5 sm:gap-3 sm:px-6">
      <Button
        variant="ghost"
        size="icon-lg"
        className="-ml-2 rounded-full"
        onClick={toggle}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-expanded={!collapsed}
        title={`${collapsed ? "Expand" : "Collapse"} sidebar  [`}
      >
        <motion.span
          className="flex"
          animate={{ rotate: collapsed ? 180 : 0 }}
          transition={SPRING.snappy}
        >
          <ChevronsLeftIcon size={16} color="var(--text-2)" />
        </motion.span>
      </Button>

      {/* Full search bar where there's room; an icon button where there isn't.
          Both open the global palette — see components/search/. */}
      <SearchTrigger />
      <SearchTriggerCompact />

      <div className="ml-auto flex flex-none items-center gap-1.5">
        <Button
          variant="ghost"
          size="icon-lg"
          className="rounded-full"
          onClick={toggleTheme}
          aria-label={
            theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
          }
        >
          {/* The glyph rotates as it swaps, so the toggle reads as one
              control turning over rather than two icons trading places. */}
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={theme}
              className="flex"
              initial={{ opacity: 0, rotate: -90, scale: 0.6 }}
              animate={{ opacity: 1, rotate: 0, scale: 1 }}
              exit={{ opacity: 0, rotate: 90, scale: 0.6 }}
              transition={SPRING.snappy}
            >
              {theme === "dark" ? (
                <MoonIcon size={17} color="var(--text-2)" />
              ) : (
                <SunIcon size={17} color="var(--text-2)" />
              )}
            </motion.span>
          </AnimatePresence>
        </Button>

        <Button
          variant="ghost"
          size="icon-lg"
          className="relative rounded-full"
          aria-label="Notifications"
        >
          <BellIcon size={17} color="var(--text-2)" />
          <motion.span
            className="absolute top-1.5 right-1.5 size-1.5 rounded-full border-[1.5px] border-[var(--surface)] bg-[var(--bad)]"
            animate={{ scale: [1, 1.25, 1] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          />
        </Button>

        <span className="mx-1 hidden h-6 w-px flex-none bg-[var(--border)] sm:block" />

        <AccountMenu />
      </div>
    </div>
  );
}
