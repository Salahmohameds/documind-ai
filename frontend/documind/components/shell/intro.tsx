"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { Logo } from "@/components/shell/logo";
import { AnimatePresence, Spinner, motion } from "@/components/motion";
import {
  CURTAIN,
  CURTAIN_CONTENT,
  CURTAIN_LINE,
  CURTAIN_MARK,
  INTRO_HOLD_MS,
} from "@/lib/motion";

/**
 * The splash the app opens on: the mark and a spinner on a full-bleed panel,
 * which then lifts off the top of the viewport to reveal the product.
 *
 *  - **Once per browser session.** Only a genuine cold load plays it; a reload
 *    or a client-side navigation gets nothing. Append `?intro` to any URL
 *    (e.g. `/dashboard?intro`) to replay it on demand.
 *  - **Never on the auth pages.** `/login` and `/register` are excluded, so
 *    someone signing in isn't made to wait through a brand moment.
 *  - **It never gates the app.** The page renders underneath the whole time,
 *    so the curtain is decoration over ready content, not a loading gate.
 *
 * The hold is a fixed `INTRO_HOLD_MS` and is not coupled to loading in either
 * direction: a slow page cannot extend it, a fast one cannot cut it short.
 */

const SEEN_KEY = "documind-intro-seen";

/** Prefixes that never play the intro. Kept in sync with the script below. */
const EXCLUDED = ["/login", "/register"];

/**
 * Inlined in <head> so the play/skip decision lands **before first paint** —
 * the same trick `themeInitScript` uses for the theme, and for the same
 * reason. Deciding this in React instead meant the server always rendered the
 * curtain and hydration then tore it away, which flashed the splash for a
 * couple of hundred milliseconds on every already-seen load.
 *
 * `<html data-intro>` is the source of truth. The CSS in globals.css keeps
 * `.dm-intro` display:none until this stamps `play`, so a session that should
 * skip never paints a single frame of it — and a browser with JS disabled,
 * where nothing could ever lift the curtain, never shows it at all.
 *
 * Keep SEEN_KEY and EXCLUDED in sync with the constants above.
 */
export const introInitScript = `try{
var p=location.pathname,s=location.search,play=true;
if(p.indexOf("/login")===0||p.indexOf("/register")===0){play=false;}
else if(new URLSearchParams(s).has("intro")){play=true;}
else if(sessionStorage.getItem("${SEEN_KEY}")==="1"){play=false;}
document.documentElement.dataset.intro=play?"play":"skip";
if(play){sessionStorage.setItem("${SEEN_KEY}","1");}
}catch(e){document.documentElement.dataset.intro="skip";}`;

/* -- Reading the decision back ------------------------------------------ */

/** The attribute is stamped once, before paint, and never changes after. */
const subscribeNever = () => () => {};
const getPlay = () => document.documentElement.dataset.intro === "play";
/**
 * The server has no session and no URL bar, so it renders the curtain and lets
 * the script above decide. Anything else would put a flash of the *app* ahead
 * of the splash on a genuine cold load.
 */
const getPlayOnServer = () => true;

export function Intro() {
  const pathname = usePathname();
  // Same shape as `useTheme` in theme-provider.tsx.
  const play = useSyncExternalStore(subscribeNever, getPlay, getPlayOnServer);
  const [showing, setShowing] = useState(true);

  // The auth pages are excluded on the server too, so the curtain is never in
  // their markup at all — not rendered and then hidden.
  const excluded = EXCLUDED.some((p) => pathname.startsWith(p));

  useEffect(() => {
    if (!play || excluded) return;
    // A plain timer, deliberately: nothing here observes data, route readiness
    // or hydration progress, so however fast the app comes up the curtain is
    // still on screen for the full hold. Reduced motion gets the same hold —
    // it drops the *travel* (via the `<Motion>` provider), not the time on
    // screen, because the mark is content and cutting it would remove
    // information rather than motion.
    const t = setTimeout(() => setShowing(false), INTRO_HOLD_MS);
    return () => clearTimeout(t);
  }, [play, excluded]);

  // The page behind must not scroll under the curtain.
  useEffect(() => {
    if (!showing || !play || excluded) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [showing, play, excluded]);

  // Unmount the whole presence boundary rather than letting `showing` fall to
  // false — that would slide the curtain away for someone who never saw it
  // arrive. (It is already display:none by then; this just drops the nodes.)
  if (excluded || !play) return null;

  return (
    <AnimatePresence>
      {showing && (
        <motion.div
          key="intro"
          role="status"
          aria-label="Loading DocuMind"
          // Layout and paint live in `.dm-intro` so the pre-paint script can
          // suppress it with a class rule; an inline `display` would win over
          // that and reintroduce the flash.
          className="dm-intro"
          variants={CURTAIN}
          initial="show"
          animate="show"
          exit="exit"
        >
          <motion.div
            variants={CURTAIN_CONTENT}
            initial="hidden"
            animate="show"
            exit="exit"
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 22,
            }}
          >
            <motion.div
              variants={CURTAIN_MARK}
              style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
            >
              <Logo size={96} />
            </motion.div>

            <motion.div
              variants={CURTAIN_LINE}
              style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 7 }}
            >
              <span
                style={{
                  fontSize: 30,
                  fontWeight: 700,
                  letterSpacing: "-.03em",
                  color: "var(--text)",
                  lineHeight: 1,
                }}
              >
                DocuMind
              </span>
              <span
                style={{
                  fontSize: 12,
                  letterSpacing: ".14em",
                  textTransform: "uppercase",
                  color: "var(--text-3)",
                }}
              >
                Document intelligence
              </span>
            </motion.div>

            <motion.div variants={CURTAIN_LINE} style={{ paddingTop: 2 }}>
              <Spinner size={22} />
            </motion.div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
