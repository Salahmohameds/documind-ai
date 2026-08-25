"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";
import { DOCUMENTS } from "@/lib/mock/data";
import { setOverlayOpen, useSidebar } from "@/components/shell/sidebar-state";
import { Logo, Wordmark } from "@/components/shell/logo";
import { Badge } from "@/components/ui/badge";
import { ChatIcon, FileIcon, GridIcon, UploadIcon } from "@/components/ui/icons";

type NavItem = {
  href: string;
  label: string;
  icon: (props: { size?: number; color?: string }) => ReactNode;
  badge?: ReactNode;
  badgeAccent?: boolean;
  /** Extra path prefixes that should also light this item up. */
  alsoMatches?: string[];
};

/** Badges read the mock store directly — swap for a counts endpoint later. */
const inFlight = DOCUMENTS.filter((d) => d.status === "processing" || d.status === "queued").length;

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: GridIcon },
  { href: "/chat", label: "Ask", icon: ChatIcon },
  {
    href: "/upload",
    label: "Upload",
    icon: UploadIcon,
    badge: inFlight > 0 ? inFlight : undefined,
    badgeAccent: true,
  },
  {
    href: "/documents",
    label: "Documents",
    icon: FileIcon,
    badge: DOCUMENTS.length,
    alsoMatches: ["/qa"],
  },
];

const EXPANDED = 236;
const COLLAPSED = 68;

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, narrow, overlay } = useSidebar();
  const railRef = useRef<HTMLDivElement>(null);

  // Marking the rail "ready" after the first paint keeps a stored collapsed
  // state from visibly sliding shut on every page load.
  useEffect(() => {
    railRef.current?.setAttribute("data-ready", "");
  }, []);

  // Navigating away closes a floating rail — otherwise it covers the new page.
  useEffect(() => {
    setOverlayOpen(false);
  }, [pathname]);

  const width = collapsed ? COLLAPSED : EXPANDED;

  return (
    <>
      {/* Narrow screens: the rail floats, so a spacer holds its slot in flow. */}
      {narrow && <div className="dm-rail flex-none" style={{ width: COLLAPSED }} aria-hidden />}

      {overlay && (
        <div
          className="anim-fade fixed inset-0 z-30 bg-[rgb(11_18_32/42%)]"
          onClick={() => setOverlayOpen(false)}
          aria-hidden
        />
      )}

    <div
      ref={railRef}
      data-collapsed={collapsed || undefined}
      className={
        "dm-rail flex flex-none flex-col border-r border-border bg-[var(--surface)] py-4 " +
        (narrow ? "fixed inset-y-0 left-0 z-40 shadow-[0_0_40px_rgb(11_18_32/24%)]" : "relative")
      }
      style={{ width, paddingInline: collapsed ? 10 : 12 }}
    >
      {/* Brand ----------------------------------------------------------- */}
      <div
        className="flex items-center gap-2.5 pt-1 pb-5"
        style={{ paddingInline: collapsed ? 0 : 8, justifyContent: collapsed ? "center" : undefined }}
      >
        <Logo size={30} />
        {!collapsed && (
          <span className="anim-fade">
            <Wordmark />
          </span>
        )}
      </div>

      {/* Nav ------------------------------------------------------------- */}
      <nav className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto overflow-x-hidden">
        {NAV.map(({ href, label, icon: Icon, badge, badgeAccent, alsoMatches }, i) => {
          const active =
            pathname.startsWith(href) || (alsoMatches ?? []).some((p) => pathname.startsWith(p));
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              title={collapsed ? label : undefined}
              style={{ ["--i" as string]: i, justifyContent: collapsed ? "center" : undefined }}
              className={
                "anim-up relative flex items-center gap-2.5 rounded-[10px] border border-transparent px-2.5 py-[9px] transition-colors duration-150 " +
                (active ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-2)]")
              }
            >
              {/* Active rail — grows in from nothing on selection. */}
              <span
                aria-hidden
                className="absolute left-0 w-[3px] rounded-full bg-primary transition-all duration-300"
                style={{ height: active ? 18 : 0, opacity: active ? 1 : 0, top: "calc(50% - 9px)" }}
              />
              <Icon size={16} color={active ? "var(--accent)" : "var(--s400)"} />

              {!collapsed && (
                <>
                  <span
                    className={
                      "anim-fade truncate text-[13px] " +
                      (active ? "font-semibold text-primary" : "font-[450] text-[var(--text-2)]")
                    }
                  >
                    {label}
                  </span>
                  {badge !== undefined &&
                    (badgeAccent ? (
                      <Badge
                        variant="pill"
                        className="anim-fade ml-auto bg-[var(--accent-soft)] px-[7px] py-0.5 font-semibold text-primary"
                      >
                        {badge}
                      </Badge>
                    ) : (
                      <span
                        className={
                          "anim-fade ml-auto text-[11px] " +
                          (active ? "text-primary" : "text-[var(--text-3)]")
                        }
                      >
                        {badge}
                      </span>
                    ))}
                </>
              )}

              {/* Collapsed: the count becomes a dot so it still reads as unread. */}
              {collapsed && badge !== undefined && badgeAccent && (
                <span className="anim-pop absolute top-1.5 right-1.5 size-1.5 rounded-full bg-primary" />
              )}
            </Link>
          );
        })}
      </nav>
    </div>
    </>
  );
}
