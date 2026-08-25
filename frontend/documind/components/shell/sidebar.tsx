"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { DOCUMENTS } from "@/lib/mock/data";
import { setOverlayOpen, useSidebar } from "@/components/shell/sidebar-state";
import { Logo, Wordmark } from "@/components/shell/logo";
import { Badge } from "@/components/ui/badge";
import { ChatIcon, FileIcon, GridIcon, UploadIcon } from "@/components/ui/icons";
import { AnimatePresence, Anim, Stagger, motion } from "@/components/motion";
import { EASED, PRESETS, SPRING } from "@/lib/motion";

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

  // Navigating away closes a floating rail — otherwise it covers the new page.
  useEffect(() => {
    setOverlayOpen(false);
  }, [pathname]);

  const width = collapsed ? COLLAPSED : EXPANDED;

  return (
    <>
      {/* Narrow screens: the rail floats, so a spacer holds its slot in flow. */}
      {narrow && <div className="flex-none" style={{ width: COLLAPSED }} aria-hidden />}

      <AnimatePresence>
        {overlay && (
          <motion.div
            variants={PRESETS.overlay}
            initial="hidden"
            animate="show"
            exit="exit"
            className="fixed inset-0 z-30 bg-[rgb(11_18_32/42%)]"
            onClick={() => setOverlayOpen(false)}
            aria-hidden
          />
        )}
      </AnimatePresence>

      <motion.div
        data-collapsed={collapsed || undefined}
        // `initial={false}` adopts the stored width on first paint instead of
        // animating open from nothing on every page load.
        initial={false}
        animate={{ width, paddingInline: collapsed ? 10 : 12 }}
        transition={SPRING.layout}
        className={
          "flex flex-none flex-col border-r border-border bg-[var(--surface)] py-4 " +
          (narrow ? "fixed inset-y-0 left-0 z-40 shadow-[0_0_40px_rgb(11_18_32/24%)]" : "relative")
        }
      >
        {/* Brand ----------------------------------------------------------- */}
        <div
          className="flex items-center gap-2.5 pt-1 pb-5"
          style={{ paddingInline: collapsed ? 0 : 8, justifyContent: collapsed ? "center" : undefined }}
        >
          <Logo size={30} />
          <AnimatePresence initial={false}>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                transition={EASED.fast}
                style={{ whiteSpace: "nowrap" }}
              >
                <Wordmark />
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Nav ------------------------------------------------------------- */}
        <Stagger
          as="nav"
          gap={0.05}
          className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto overflow-x-hidden"
        >
          {NAV.map(({ href, label, icon: Icon, badge, badgeAccent, alsoMatches }) => {
            const active =
              pathname.startsWith(href) || (alsoMatches ?? []).some((p) => pathname.startsWith(p));
            return (
              <Anim
                key={href}
                as={Link}
                preset="left"
                href={href}
                aria-current={active ? "page" : undefined}
                title={collapsed ? label : undefined}
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.97 }}
                style={{ justifyContent: collapsed ? "center" : undefined }}
                className={
                  "relative flex items-center gap-2.5 rounded-[10px] border border-transparent px-2.5 py-[9px] transition-colors duration-150 " +
                  (active ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-2)]")
                }
              >
                {/* One indicator shared across items: `layoutId` makes Motion
                    slide it from the old item to the new one on navigation,
                    instead of one fading out while another fades in. */}
                {active && (
                  <motion.span
                    layoutId="nav-indicator"
                    aria-hidden
                    transition={SPRING.layout}
                    className="absolute left-0 h-[18px] w-[3px] rounded-full bg-primary"
                    style={{ top: "calc(50% - 9px)" }}
                  />
                )}
                <Icon size={16} color={active ? "var(--accent)" : "var(--s400)"} />

                <AnimatePresence initial={false}>
                  {!collapsed && (
                    <motion.span
                      key="label"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={EASED.instant}
                      className={
                        "truncate text-[13px] " +
                        (active ? "font-semibold text-primary" : "font-[450] text-[var(--text-2)]")
                      }
                    >
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>

                {!collapsed &&
                  badge !== undefined &&
                  (badgeAccent ? (
                    <Anim
                      as={Badge}
                      preset="pop"
                      variant="pill"
                      className="ml-auto bg-[var(--accent-soft)] px-[7px] py-0.5 font-semibold text-primary"
                    >
                      {badge}
                    </Anim>
                  ) : (
                    <Anim
                      as="span"
                      preset="fade"
                      className={
                        "ml-auto text-[11px] " + (active ? "text-primary" : "text-[var(--text-3)]")
                      }
                    >
                      {badge}
                    </Anim>
                  ))}

                {/* Collapsed: the count becomes a dot so it still reads as unread. */}
                {collapsed && badge !== undefined && badgeAccent && (
                  <Anim
                    as="span"
                    preset="pop"
                    className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-primary"
                  />
                )}
              </Anim>
            );
          })}
        </Stagger>
      </motion.div>
    </>
  );
}
