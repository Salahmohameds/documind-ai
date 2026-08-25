"use client";

import Link from "next/link";
import { WORKSPACE } from "@/lib/mock/data";
import { ChevronsLeftIcon, useSidebar } from "@/components/shell/sidebar-state";
import { ThemeSwitch, useTheme } from "@/components/theme-provider";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  CaretDownIcon,
  GearIcon,
  MoonIcon,
  SignOutIcon,
  TeamIcon,
} from "@/components/ui/icons";

/**
 * Workspace identity and account actions. Lives in the topbar so it stays put
 * whether the side rail is expanded or collapsed.
 */
export function AccountMenu() {
  const { theme, toggleTheme } = useTheme();
  const { collapsed, toggle } = useSidebar();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="group/account flex items-center gap-2.5 rounded-[10px] border border-transparent py-1 pr-2 pl-1 text-left outline-none transition-colors duration-150 hover:border-border hover:bg-[var(--surface-2)] focus-visible:ring-3 focus-visible:ring-ring/50 aria-expanded:border-border aria-expanded:bg-[var(--surface-2)]">
        <Avatar className="size-[34px] flex-none rounded-[10px]">
          <AvatarFallback className="rounded-[10px] bg-[var(--s700)] text-xs font-semibold text-white">
            {WORKSPACE.initials}
          </AvatarFallback>
        </Avatar>
        <div className="hidden min-w-0 flex-col lg:flex">
          <span className="truncate text-xs font-semibold text-[var(--text)]">
            {WORKSPACE.org}
          </span>
          <span className="truncate font-mono text-[10px] text-[var(--text-3)]">
            {WORKSPACE.email}
          </span>
        </div>
        <span className="hidden transition-transform duration-200 group-aria-expanded/account:rotate-180 lg:flex">
          <CaretDownIcon size={13} color="var(--text-3)" />
        </span>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        side="bottom"
        align="end"
        sideOffset={8}
        style={{ width: 236 }}
        className="rounded-xl p-1.5 shadow-[0_14px_34px_rgba(11,18,32,.16)]"
      >
        <DropdownMenuLabel className="flex min-w-0 flex-col gap-px px-2 pt-2 pb-2.5">
          <span className="truncate text-xs font-semibold text-[var(--text)]">
            {WORKSPACE.user}
          </span>
          <span className="truncate font-mono text-[10px] font-normal text-[var(--text-3)]">
            {WORKSPACE.email}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* <DropdownMenuItem
          className="gap-2.5 rounded-[10px] p-2"
          onSelect={(e) => {
            // Keep the menu open so the switch reads as a live toggle.
            e.preventDefault();
            toggleTheme();
          }}
        >
          <MoonIcon size={14} color="var(--text-3)" />
          <span className="min-w-0 flex-1 truncate text-xs font-medium text-[var(--text-2)]">Dark mode</span>
          <ThemeSwitch theme={theme} />
        </DropdownMenuItem>

        <DropdownMenuItem
          className="gap-2.5 rounded-[10px] p-2"
          onSelect={(e) => {
            e.preventDefault();
            toggle();
          }}
        >
          <span className="flex text-[var(--text-3)]">
            <ChevronsLeftIcon size={14} />
          </span>
          <span className="min-w-0 flex-1 truncate text-xs text-[var(--text-2)]">
            {collapsed ? "Expand sidebar" : "Collapse sidebar"}
          </span>
          <span className="flex-none font-mono text-[10px] text-[var(--text-3)]">[</span>
        </DropdownMenuItem> */}

        <DropdownMenuItem className="gap-2.5 rounded-[10px] p-2">
          <GearIcon size={14} color="var(--text-3)" />
          <span className="min-w-0 flex-1 truncate text-xs text-[var(--text-2)]">
            Account settings
          </span>
        </DropdownMenuItem>

        <DropdownMenuItem className="gap-2.5 rounded-[10px] p-2">
          <TeamIcon size={14} color="var(--text-3)" />
          <span className="min-w-0 flex-1 truncate text-xs text-[var(--text-2)]">
            Team &amp; billing
          </span>
          <span className="flex-none font-mono text-[10px] text-[var(--text-3)]">
            {WORKSPACE.plan}
          </span>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          asChild
          className="gap-2.5 rounded-[10px] p-2 focus:bg-[var(--bad-soft)]"
        >
          <Link href="/login">
            <SignOutIcon size={14} color="var(--bad)" />
            <span className="min-w-0 flex-1 truncate text-xs text-[var(--bad)]">
              Sign out
            </span>
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
