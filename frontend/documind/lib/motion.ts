import type { Transition, Variants } from "motion/react";

/**
 * DocuMind's motion vocabulary — the single source of truth for every
 * animation in the product.
 *
 * The rules that keep it coherent:
 *
 *  1. **Entrances travel, exits fade.** Something arriving earns 8–14px of
 *     movement; something leaving just gets out of the way, faster than it
 *     came in. Reversing an entrance on exit reads as indecision.
 *  2. **Springs for anything the pointer touches**, eased curves for content
 *     that simply appears. A spring under a click feels like a response; a
 *     spring under a paragraph feels unserious.
 *  3. **Nothing is slower than 420ms.** Perceived speed is a feature.
 *  4. **Lists orchestrate, items don't.** A parent staggers its children via
 *     variant propagation — no per-item delay arithmetic.
 *
 * Consume these through the components in `components/motion.tsx` rather than
 * hand-rolling `initial`/`animate` at the call site.
 */

/* -- Curves & timings --------------------------------------------------- */

/** The house easing curve — a decisive start that settles rather than stops. */
export const EASE_OUT = [0.22, 0.8, 0.3, 1] as const;
export const EASE_IN = [0.5, 0, 0.85, 0.35] as const;
export const EASE_IN_OUT = [0.65, 0, 0.35, 1] as const;

export const DURATION = {
  /** Hover washes, colour changes — below the threshold of feeling animated. */
  instant: 0.15,
  /** Popovers, tooltips, anything anchored to a click. */
  fast: 0.2,
  /** The default for content entering. */
  base: 0.3,
  /** Panels, dialogs, first-paint hero content. */
  slow: 0.42,
} as const;

/* -- Springs ------------------------------------------------------------ */

/**
 * `visualDuration` is how long the spring *looks* like it takes to arrive
 * (not how long it settles), so these stay comparable to the eased durations
 * above. `bounce: 0` is a critically-damped spring — smooth, no overshoot.
 */
export const SPRING = {
  /** Cards, panels, page content. Settles clean, no wobble. */
  soft: { type: "spring", visualDuration: 0.34, bounce: 0.16 },
  /** Buttons, toggles, pills — reacts under the finger. */
  snappy: { type: "spring", visualDuration: 0.22, bounce: 0.22 },
  /** Badges, counters, success glyphs. The only place overshoot is welcome. */
  bouncy: { type: "spring", visualDuration: 0.4, bounce: 0.42 },
  /** Layout reflow — rows reordering, a rail resizing. */
  layout: { type: "spring", visualDuration: 0.28, bounce: 0 },
} satisfies Record<string, Transition>;

export const EASED = {
  instant: { duration: DURATION.instant, ease: EASE_OUT },
  fast: { duration: DURATION.fast, ease: EASE_OUT },
  base: { duration: DURATION.base, ease: EASE_OUT },
  slow: { duration: DURATION.slow, ease: EASE_OUT },
  exit: { duration: DURATION.instant, ease: EASE_IN },
} satisfies Record<string, Transition>;

/* -- Presets ------------------------------------------------------------ */

/**
 * Every preset speaks the same three states, so `<Anim>` can swap between
 * them without the call site knowing which one it got, and so any of them can
 * sit inside a `<Stagger>` and inherit its orchestration.
 */
export type PresetName =
  | "fade"
  | "up"
  | "down"
  | "left"
  | "right"
  | "scale"
  | "row"
  | "pop"
  | "blur"
  | "overlay"
  | "dialog"
  | "popover"
  | "toast";

export const PRESETS: Record<PresetName, Variants> = {
  /** No travel — for text swaps and things that shouldn't draw the eye. */
  fade: {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: EASED.base },
    exit: { opacity: 0, transition: EASED.exit },
  },

  /** The workhorse: page sections, cards, form panels. */
  up: {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: SPRING.soft },
    exit: { opacity: 0, y: -6, transition: EASED.exit },
  },

  /** Things that descend from something above — inline errors, banners. */
  down: {
    hidden: { opacity: 0, y: -10 },
    show: { opacity: 1, y: 0, transition: SPRING.soft },
    exit: { opacity: 0, y: -6, transition: EASED.exit },
  },

  left: {
    hidden: { opacity: 0, x: -14 },
    show: { opacity: 1, x: 0, transition: SPRING.soft },
    exit: { opacity: 0, x: -8, transition: EASED.exit },
  },

  right: {
    hidden: { opacity: 0, x: 14 },
    show: { opacity: 1, x: 0, transition: SPRING.soft },
    exit: { opacity: 0, x: 8, transition: EASED.exit },
  },

  /** Anchored surfaces that grow out of their trigger. */
  scale: {
    hidden: { opacity: 0, scale: 0.96 },
    show: { opacity: 1, scale: 1, transition: SPRING.snappy },
    exit: { opacity: 0, scale: 0.97, transition: EASED.exit },
  },

  /** Table and list rows — a shorter throw, because there are many of them. */
  row: {
    hidden: { opacity: 0, y: 6 },
    show: { opacity: 1, y: 0, transition: EASED.base },
    exit: { opacity: 0, transition: EASED.exit },
  },

  /** Numbers, badges, confirmation glyphs. The one preset that overshoots. */
  pop: {
    hidden: { opacity: 0, scale: 0.7 },
    show: { opacity: 1, scale: 1, transition: SPRING.bouncy },
    exit: { opacity: 0, scale: 0.8, transition: EASED.exit },
  },

  /**
   * Hero content on a page's first paint. The blur is what makes it read as
   * "resolving into focus" rather than "sliding in" — reserve it for one
   * element per screen or it turns to soup.
   */
  blur: {
    hidden: { opacity: 0, y: 10, filter: "blur(6px)" },
    show: { opacity: 1, y: 0, filter: "blur(0px)", transition: EASED.slow },
    exit: { opacity: 0, filter: "blur(4px)", transition: EASED.exit },
  },

  /** Modal scrims. */
  overlay: {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: EASED.fast },
    exit: { opacity: 0, transition: EASED.fast },
  },

  /** Dialog bodies — rise slightly as they scale, so they feel lifted. */
  dialog: {
    hidden: { opacity: 0, scale: 0.94, y: 12 },
    show: { opacity: 1, scale: 1, y: 0, transition: SPRING.soft },
    exit: { opacity: 0, scale: 0.97, y: 6, transition: EASED.exit },
  },

  /** Dropdowns and menus. Pair with a `transformOrigin` at the trigger edge. */
  popover: {
    hidden: { opacity: 0, scale: 0.95, y: -6 },
    show: { opacity: 1, scale: 1, y: 0, transition: SPRING.snappy },
    exit: { opacity: 0, scale: 0.97, y: -4, transition: EASED.exit },
  },

  /** Toasts slide in from the edge they're docked to and collapse on the way out. */
  toast: {
    hidden: { opacity: 0, x: 28, scale: 0.96 },
    show: { opacity: 1, x: 0, scale: 1, transition: SPRING.soft },
    exit: {
      opacity: 0,
      x: 20,
      scale: 0.96,
      transition: { duration: DURATION.fast, ease: EASE_IN },
    },
  },
};

/* -- Orchestration ------------------------------------------------------ */

/** The gap between siblings in a staggered list. */
export const STAGGER_GAP = 0.045;

/**
 * Container variants for a staggered group. Children need no delay of their
 * own — they inherit `show` from here in sequence.
 *
 * Exits run in reverse so a list unwinds from the bottom, which reads as the
 * mirror of how it arrived.
 */
export function staggerVariants(
  gap = STAGGER_GAP,
  delay = 0,
): Variants {
  return {
    hidden: {},
    show: {
      transition: { staggerChildren: gap, delayChildren: delay },
    },
    exit: {
      transition: { staggerChildren: gap / 2, staggerDirection: -1 },
    },
  };
}

/* -- Interaction -------------------------------------------------------- */

/** Hover/press feedback for cards that navigate somewhere. */
export const LIFT = {
  rest: { y: 0, scale: 1 },
  hover: { y: -3, scale: 1.004, transition: SPRING.snappy },
  press: { y: -1, scale: 0.998, transition: { duration: 0.08 } },
} as const;

/** Hover/press feedback for buttons and icon targets. */
export const TAP = {
  hover: { scale: 1.03, transition: SPRING.snappy },
  press: { scale: 0.96, transition: { duration: 0.08 } },
} as const;

/** Viewport config for scroll-triggered reveals — fires a little early, once. */
export const IN_VIEW = { once: true, amount: 0.2, margin: "0px 0px -12% 0px" } as const;

/* -- Intro curtain ------------------------------------------------------ */

/**
 * How long the splash holds before it lifts, measured from the moment the
 * curtain mounts — never from anything to do with data or route readiness, so
 * a fast load can't cut it short. The curtain runs once per browser session
 * (see `components/shell/intro.tsx`), which is what buys it this much time.
 *
 * This is a floor, not a target: the panel is painted server-side, so it is on
 * screen from first paint and only starts counting once React takes over.
 */
export const INTRO_HOLD_MS = 3000;

/** Seconds the curtain takes to clear the viewport. */
export const CURTAIN_EXIT = 0.85;

/**
 * The splash panel itself. It leaves by sliding off the top, rounding its
 * bottom corners on the way — so it reads as a solid card being lifted away
 * from the app, not a layer being faded out.
 *
 * The radius finishes well before the travel does; corners that were still
 * rounding at the halfway mark looked like a rendering glitch.
 */
export const CURTAIN: Variants = {
  show: {
    y: 0,
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 0,
  },
  exit: {
    y: "-100%",
    borderBottomLeftRadius: 56,
    borderBottomRightRadius: 56,
    transition: {
      default: { duration: CURTAIN_EXIT, ease: [0.76, 0, 0.24, 1] },
      borderBottomLeftRadius: { duration: 0.3, ease: EASE_OUT },
      borderBottomRightRadius: { duration: 0.3, ease: EASE_OUT },
    },
  },
};

/**
 * The mark, wordmark and spinner inside the curtain. They enter in sequence
 * and leave together a beat *before* the panel moves, so the panel is empty
 * by the time it starts travelling.
 */
export const CURTAIN_CONTENT: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.11, delayChildren: 0.06 } },
  exit: { opacity: 0, y: -14, transition: { duration: 0.22, ease: EASE_IN } },
};

export const CURTAIN_MARK: Variants = {
  hidden: { opacity: 0, scale: 0.72, filter: "blur(8px)" },
  show: {
    opacity: 1,
    scale: 1,
    filter: "blur(0px)",
    transition: { type: "spring", visualDuration: 0.55, bounce: 0.34 },
  },
};

export const CURTAIN_LINE: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: EASE_OUT } },
};

/* -- Command palette ----------------------------------------------------- */

/**
 * The global search palette. Opening is the one interaction in the product
 * that has to feel *instantaneous* — it sits between the user and a thought
 * they have already had — so the panel uses a short, barely-bouncing spring
 * and the scrim a plain fade. Anything slower reads as the app thinking.
 */
export const PALETTE_SCRIM: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.14, ease: EASE_OUT } },
  exit: { opacity: 0, transition: { duration: 0.11, ease: EASE_IN } },
};

export const PALETTE_PANEL: Variants = {
  hidden: { opacity: 0, y: -8, scale: 0.985 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", visualDuration: 0.17, bounce: 0.1 },
  },
  exit: {
    opacity: 0,
    y: -4,
    scale: 0.99,
    transition: { duration: 0.11, ease: EASE_IN },
  },
};

/**
 * The result list crossfades as the query changes. Deliberately *not* a
 * per-row stagger: staggering on every keystroke turns a fast index into
 * something that looks like it is struggling.
 */
export const PALETTE_RESULTS: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.12, ease: EASE_OUT } },
  exit: { opacity: 0, transition: { duration: 0.06, ease: EASE_IN } },
};

/** The sliding selection highlight behind the active row. */
export const PALETTE_CURSOR: Transition = {
  type: "spring",
  visualDuration: 0.15,
  bounce: 0,
};
