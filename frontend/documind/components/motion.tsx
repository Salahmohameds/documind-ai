"use client";

import {
  AnimatePresence,
  MotionConfig,
  animate,
  motion,
  useInView,
  useMotionValue,
  useReducedMotion,
  useTransform,
  type HTMLMotionProps,
  type Variants,
} from "motion/react";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ComponentPropsWithoutRef,
  type ComponentType,
  type CSSProperties,
  type ElementType,
  type ReactNode,
} from "react";
import {
  DURATION,
  EASE_OUT,
  EASED,
  IN_VIEW,
  LIFT,
  PRESETS,
  SPRING,
  STAGGER_GAP,
  TAP,
  staggerVariants,
  type PresetName,
} from "@/lib/motion";

/**
 * The animation layer. Screens compose these; they never reach for `motion.*`
 * or write `initial`/`animate` by hand, so the vocabulary in `lib/motion.ts`
 * stays the only place a duration or curve is decided.
 *
 * Everything here respects `prefers-reduced-motion` through `<Motion>` at the
 * root, which switches Motion into a mode where transforms and opacity are
 * skipped but state still lands.
 */

export { AnimatePresence, motion, useReducedMotion };

/* -- Root provider ------------------------------------------------------ */

/**
 * Wraps the app once. `reducedMotion="user"` is what makes every component
 * below honour the OS setting without a single media query.
 */
export function Motion({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user" transition={SPRING.soft}>
      {children}
    </MotionConfig>
  );
}

/* -- Polymorphic host --------------------------------------------------- */

/**
 * `motion.create()` builds a new component type, so calling it during render
 * would remount the subtree on every pass. Cached per source component.
 */
const motionCache = new Map<ElementType, ElementType>();

function motionHost(as: ElementType): ElementType {
  if (typeof as === "string") {
    const tag = (motion as unknown as Record<string, ElementType>)[as];
    if (tag) return tag;
  }
  const hit = motionCache.get(as);
  if (hit) return hit;
  const made = motion.create(as as ComponentType<Record<string, unknown>>) as ElementType;
  motionCache.set(as, made);
  return made;
}

/* -- Anim --------------------------------------------------------------- */

/**
 * Motion only propagates a variant to a child that declares no `animate` of
 * its own. `<Stagger>` flips this on so its `<Anim>` descendants stand down
 * and let the sequence drive them.
 */
const InStagger = createContext(false);

type AnimOwn = {
  /** Which entrance from the shared vocabulary. */
  preset?: PresetName;
  /** Seconds to hold before starting. Prefer `<Stagger>` for lists. */
  delay?: number;
  /**
   * Hold the entrance until the element scrolls into view. Use below the
   * fold; above it the animation would just never be seen to start.
   */
  inView?: boolean;
  /** Opt this instance out of animating without changing the markup. */
  still?: boolean;
  /** Add the pointer lift — for cards that navigate somewhere. */
  hover?: boolean;
};

/** Motion props every host accepts, minus the ones `<Anim>` decides itself. */
type MotionExtras = Omit<
  HTMLMotionProps<"div">,
  "variants" | "children" | "style" | "className" | "onDrag" | "onDragEnd" | "onDragStart" | "onAnimationStart"
>;

/**
 * Generic over `as`, so `<Anim as={Link} href=…>` and `<Anim as={Badge}
 * variant=…>` both typecheck against the real component's props.
 */
export type AnimProps<T extends ElementType = "div"> = AnimOwn &
  MotionExtras & { as?: T } & Omit<ComponentPropsWithoutRef<T>, keyof AnimOwn | keyof MotionExtras>;

/**
 * One element entering. Inside a `<Stagger>` it drops its own `initial`/
 * `animate` and inherits the parent's sequence instead — which is what lets
 * the same component serve both a lone panel and the 30th row of a table.
 */
export function Anim<T extends ElementType = "div">({
  as,
  preset = "up",
  delay,
  inView,
  still,
  hover,
  ...rest
}: AnimProps<T>) {
  const Host = motionHost((as ?? "div") as ElementType) as ElementType;
  const nested = useContext(InStagger);
  const ref = useRef<HTMLElement>(null);
  const seen = useInView(ref, IN_VIEW);

  const variants = useMemo(
    () => withDelay(hover ? { ...PRESETS[preset], ...LIFT } : PRESETS[preset], delay),
    [preset, delay, hover],
  );

  if (still) return <Host ref={ref} {...rest} />;

  // A nested Anim declares no `animate`, so the parent's sequence reaches it.
  const driven = nested
    ? {}
    : { initial: "hidden", animate: inView && !seen ? "hidden" : "show" };

  return (
    <Host
      ref={ref}
      variants={variants}
      {...driven}
      exit="exit"
      whileHover={hover ? "hover" : undefined}
      whileTap={hover ? "press" : undefined}
      {...rest}
    />
  );
}

/** Folds a start delay into a preset's `show` state so stagger can still own it. */
function withDelay(base: Variants, delay?: number): Variants {
  if (!delay) return base;
  const show = base.show as Record<string, unknown>;
  return { ...base, show: { ...show, transition: { ...(show.transition as object), delay } } };
}

/* -- Stagger ------------------------------------------------------------ */

export type StaggerProps<T extends ElementType = "div"> = MotionExtras & {
  as?: T;
  /** Seconds between siblings. */
  gap?: number;
  /** Seconds before the first child starts. */
  delay?: number;
  inView?: boolean;
} & Omit<ComponentPropsWithoutRef<T>, "gap" | "delay" | "inView" | keyof MotionExtras>;

/**
 * Sequences its `<Anim>` children. The children carry no delay maths — this
 * is the whole reason the old `--i` index prop could go away.
 */
export function Stagger<T extends ElementType = "div">({
  as,
  gap = STAGGER_GAP,
  delay = 0,
  inView,
  ...rest
}: StaggerProps<T>) {
  const Host = motionHost((as ?? "div") as ElementType) as ElementType;
  const ref = useRef<HTMLElement>(null);
  const seen = useInView(ref, IN_VIEW);
  const nested = useContext(InStagger);
  const variants = useMemo(() => staggerVariants(gap, delay), [gap, delay]);

  // A Stagger inside a Stagger sequences its own children off the outer beat.
  const driven = nested
    ? {}
    : { initial: "hidden", animate: inView && !seen ? "hidden" : "show" };

  return (
    <InStagger.Provider value={true}>
      <Host ref={ref} variants={variants} {...driven} exit="exit" {...rest} />
    </InStagger.Provider>
  );
}

/* -- Interaction wrappers ----------------------------------------------- */

/**
 * A card that rises to meet the pointer. The transform springs on the
 * compositor; the shadow and border stay a CSS transition (see `.lift` in
 * globals.css), since neither is cheap to animate per-frame.
 */
export function Lift<T extends ElementType = "div">({ className, ...rest }: AnimProps<T>) {
  return (
    <Anim
      hover
      className={["lift", className].filter(Boolean).join(" ")}
      {...(rest as AnimProps<T>)}
    />
  );
}

/** Press/hover feedback for a control. Wrap the interactive element itself. */
export function Tappable<T extends ElementType = "div">({
  as,
  ...rest
}: { as?: T } & Omit<ComponentPropsWithoutRef<T>, "ref"> & MotionExtras) {
  const Host = motionHost((as ?? "div") as ElementType) as ElementType;
  return <Host whileHover={TAP.hover} whileTap={TAP.press} {...rest} />;
}

/* -- Loading ------------------------------------------------------------ */

/** The indeterminate spinner. One rotation, 750ms, forever. */
export function Spinner({
  size = 16,
  color = "var(--accent)",
  track = "var(--accent-border)",
  style,
}: {
  size?: number;
  color?: string;
  track?: string;
  style?: CSSProperties;
}) {
  return (
    <motion.span
      aria-hidden
      animate={{ rotate: 360 }}
      transition={{ duration: 0.75, ease: "linear", repeat: Infinity }}
      style={{
        width: size,
        height: size,
        flex: "none",
        borderRadius: "50%",
        border: `${Math.max(1.5, size / 9)}px solid ${track}`,
        borderTopColor: color,
        display: "inline-block",
        ...style,
      }}
    />
  );
}

/**
 * A loading placeholder. The old version pulsed its opacity, which made a
 * screenful of them throb in unison; this sweeps a highlight across each one
 * instead. Pass a `delay` that grows with the row index and a stack reads as
 * a wave rather than a single flash.
 */
export function Shimmer({
  className,
  style,
  delay = 0,
  ...rest
}: HTMLMotionProps<"span"> & { delay?: number }) {
  return (
    <motion.span
      aria-hidden
      className={["dm-skeleton", className].filter(Boolean).join(" ")}
      initial={{ backgroundPosition: "160% 0" }}
      animate={{ backgroundPosition: "-60% 0" }}
      transition={{ duration: 1.35, ease: "linear", repeat: Infinity, delay }}
      style={style}
      {...rest}
    />
  );
}

/** The three-dot "thinking" indicator on a streaming answer. */
export function TypingDots({
  size = 5,
  color = "var(--accent)",
  gap = 4,
}: {
  size?: number;
  color?: string;
  gap?: number;
}) {
  return (
    <span aria-hidden style={{ display: "inline-flex", alignItems: "center", gap }}>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          animate={{ opacity: [0.25, 1, 0.25], y: [0, -2, 0] }}
          transition={{
            duration: 1.1,
            ease: "easeInOut",
            repeat: Infinity,
            delay: i * 0.16,
          }}
          style={{ width: size, height: size, borderRadius: "50%", background: color, flex: "none" }}
        />
      ))}
    </span>
  );
}

/** A light sweeping across an indeterminate progress track. */
export function Sweep({
  children,
  style,
  className,
}: {
  children?: ReactNode;
  style?: CSSProperties;
  className?: string;
}) {
  return (
    <div className={className} style={{ position: "relative", overflow: "hidden", ...style }}>
      {children}
      <motion.span
        aria-hidden
        initial={{ x: "-120%" }}
        animate={{ x: "320%" }}
        transition={{ duration: 1.15, ease: "linear", repeat: Infinity }}
        className="dm-sweep-bar"
      />
    </div>
  );
}

/* -- Numbers ------------------------------------------------------------ */

/**
 * Counts to `value` instead of snapping to it. A stat that ticks up reads as
 * measured rather than merely rendered — worth it for the handful of headline
 * figures, not for every number on the page.
 */
export function Counter({
  value,
  decimals = 0,
  prefix = "",
  suffix = "",
  duration = 0.9,
  delay = 0,
  className,
  style,
}: {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
  delay?: number;
  className?: string;
  style?: CSSProperties;
}) {
  const reduced = useReducedMotion();
  const mv = useMotionValue(reduced ? value : 0);
  const text = useTransform(mv, (n) => `${prefix}${n.toFixed(decimals)}${suffix}`);

  useEffect(() => {
    if (reduced) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, { duration, delay, ease: EASE_OUT });
    return () => controls.stop();
  }, [value, duration, delay, reduced, mv]);

  return (
    <motion.span className={className} style={style}>
      {text}
    </motion.span>
  );
}

/* -- Reveals ------------------------------------------------------------ */

/**
 * Wipes a chart in from the left. A stroke-dashoffset draw-in would clobber
 * the dash patterns the series use, so this clips instead.
 */
export function DrawIn({
  children,
  duration = 0.8,
  delay = 0,
  className,
  style,
}: {
  children: ReactNode;
  duration?: number;
  delay?: number;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <motion.div
      className={className}
      style={style}
      initial={{ clipPath: "inset(0 100% 0 0)", opacity: 0 }}
      animate={{ clipPath: "inset(0 0% 0 0)", opacity: 1 }}
      transition={{ duration, delay, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Animates between "no height" and "whatever the content measures", which
 * plain CSS can't do without a hardcoded max-height.
 */
export function Collapse({
  open,
  children,
  style,
}: {
  open: boolean;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.div
          key="collapse"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ height: SPRING.layout, opacity: EASED.fast }}
          style={{ overflow: "hidden", ...style }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * Cross-fades whatever `key` currently identifies. Used for route content and
 * for panels that swap in place (a tab body, a simulated state).
 */
export function Swap({
  swapKey,
  children,
  preset = "fade",
  className,
  style,
}: {
  swapKey: string;
  children: ReactNode;
  preset?: PresetName;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={swapKey}
        variants={PRESETS[preset]}
        initial="hidden"
        animate="show"
        exit="exit"
        className={className}
        style={style}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/* -- Bars --------------------------------------------------------------- */

/** A determinate bar that grows to `pct` rather than jumping there. */
export function GrowBar({
  pct,
  color,
  delay = 0,
  style,
}: {
  pct: number;
  color: string;
  delay?: number;
  style?: CSSProperties;
}) {
  return (
    <motion.div
      initial={{ width: 0 }}
      animate={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
      transition={{ duration: DURATION.slow, delay, ease: EASE_OUT }}
      style={{ height: "100%", background: color, borderRadius: "inherit", ...style }}
    />
  );
}

/* -- Highlight ---------------------------------------------------------- */

/**
 * Flashes an element's background once — for a row that just changed, or a
 * citation the user jumped to.
 */
export function Flash({
  trigger,
  color = "var(--accent-soft)",
  children,
  className,
  style,
}: {
  /** Changing this replays the flash — pass the id or version that changed. */
  trigger: string | number;
  color?: string;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <motion.div
      // Remounting on `trigger` is what replays the keyframes; no effect needed.
      key={trigger}
      animate={{ backgroundColor: ["rgba(0,0,0,0)", color, "rgba(0,0,0,0)"] }}
      transition={{ duration: 1.1, ease: "easeOut", times: [0, 0.15, 1] }}
      className={className}
      style={style}
    >
      {children}
    </motion.div>
  );
}

export { LIFT, TAP, PRESETS, SPRING, EASED };
