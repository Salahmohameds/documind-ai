"use client";

import { AccountMenu } from "@/components/shell/account-menu";
import { ChevronsLeftIcon, useSidebar } from "@/components/shell/sidebar-state";
import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { BellIcon, MoonIcon, SearchIcon, SunIcon } from "@/components/ui/icons";

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
        <span
          className="flex transition-transform duration-300"
          style={{ transform: collapsed ? "rotate(180deg)" : undefined }}
        >
          <ChevronsLeftIcon size={16} color="var(--text-2)" />
        </span>
      </Button>

      {/* Full search bar where there's room; an icon button where there isn't. */}
      <div className="hidden h-9 w-full max-w-[340px] min-w-0 cursor-text items-center gap-[9px] rounded-lg border border-border bg-[var(--surface-2)] px-3.5 transition-colors duration-150 hover:border-[var(--border-strong)] sm:flex">
        <SearchIcon size={14} color="var(--text-3)" />
        <span className="min-w-0 flex-1 truncate text-[13px] text-[var(--text-3)]">
          Search anything…
        </span>
        <span className="hidden font-mono text-[10px] text-[var(--text-3)] md:inline">
          ⌘K
        </span>
      </div>
      <Button
        variant="ghost"
        size="icon-lg"
        className="rounded-full sm:hidden"
        aria-label="Search"
      >
        <SearchIcon size={17} color="var(--text-2)" />
      </Button>

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
          <span key={theme} className="anim-pop flex">
            {theme === "dark" ? (
              <MoonIcon size={17} color="var(--text-2)" />
            ) : (
              <SunIcon size={17} color="var(--text-2)" />
            )}
          </span>
        </Button>

        <Button
          variant="ghost"
          size="icon-lg"
          className="relative rounded-full"
          aria-label="Notifications"
        >
          <BellIcon size={17} color="var(--text-2)" />
          <span className="absolute top-1.5 right-1.5 size-1.5 rounded-full border-[1.5px] border-[var(--surface)] bg-[var(--bad)]" />
        </Button>

        <span className="mx-1 hidden h-6 w-px flex-none bg-[var(--border)] sm:block" />

        <AccountMenu />
      </div>
    </div>
  );
}
