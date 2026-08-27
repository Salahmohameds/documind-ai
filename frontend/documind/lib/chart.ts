/** Stroke colour and dash pattern per document type, in legend order. */
const SERIES_STYLE: Record<string, { stroke: string; dash: string }> = {
  Invoice: { stroke: "var(--c1)", dash: "0" },
  Contract: { stroke: "var(--c2)", dash: "0" },
  Amendment: { stroke: "var(--c3)", dash: "5 3" },
  Statement: { stroke: "var(--c4)", dash: "1.5 3" },
  Unknown: { stroke: "var(--c5, var(--text-3))", dash: "2 2" },
};

const FALLBACK_STYLE = { stroke: "var(--text-3)", dash: "2 2" };

const W = 600;
const TOP = 8;
const H = 128;

function smooth(pts: [number, number][]) {
  if (pts.length === 1) return `M ${pts[0][0]} ${pts[0][1]}`;
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i];
    const [x1, y1] = pts[i + 1];
    const mx = (x0 + x1) / 2;
    d += ` C ${mx} ${y0}, ${mx} ${y1}, ${x1} ${y1}`;
  }
  return d;
}

export type ChartSeries = {
  name: string;
  stroke: string;
  dash: string;
  d: string;
  /** Legend swatch — solid rule for solid series, striped for dashed ones. */
  swatch: string;
};

export type Chart = {
  paths: ChartSeries[];
  grid: { y: number; x2: number }[];
  /** Y-axis labels, top value first. Derived from the data, not fixed. */
  ticks: number[];
};

/**
 * Plots real daily ingestion counts.
 *
 * The axis is scaled to the data rather than to a fixed ceiling, and rounded
 * up to a readable step, so a workspace with three uploads a day and one with
 * three hundred both produce a chart worth looking at.
 */
export function buildChart(series: { name: string; counts: number[] }[]): Chart {
  const peak = Math.max(1, ...series.flatMap((s) => s.counts));
  const max = axisMax(peak);
  const step = max / 4;

  const paths = series.map(({ name, counts }) => {
    const style = SERIES_STYLE[name] ?? FALLBACK_STYLE;
    const span = Math.max(1, counts.length - 1);
    const pts = counts.map(
      (value, i) => [(i / span) * W, TOP + H - (value / max) * H] as [number, number],
    );
    return {
      name,
      stroke: style.stroke,
      dash: style.dash,
      d: smooth(pts.length ? pts : [[0, TOP + H]]),
      swatch:
        style.dash === "0"
          ? style.stroke
          : `repeating-linear-gradient(to right,${style.stroke} 0 4px,transparent 4px 7px)`,
    };
  });

  const ticks = [4, 3, 2, 1, 0].map((n) => Math.round(n * step));

  return {
    paths,
    grid: ticks.map((value) => ({ y: TOP + H - (value / max) * H, x2: W })),
    ticks,
  };
}

/** Rounds a peak up to a tick-friendly ceiling divisible by four. */
function axisMax(peak: number): number {
  const magnitude = Math.pow(10, Math.floor(Math.log10(peak)));
  for (const multiple of [1, 2, 2.5, 5, 10]) {
    const candidate = multiple * magnitude;
    if (candidate >= peak) return Math.max(4, Math.ceil(candidate / 4) * 4);
  }
  return Math.max(4, Math.ceil(peak / 4) * 4);
}

import type { Tone } from "@/lib/design";

export type GaugeTick = {
  angle: number;
  /** False only when nothing has been scored — the dial is genuinely empty. */
  on: boolean;
  height: number;
  offset: number;
  opacity: number;
  /** The band this tick belongs to. Meaningless when `on` is false. */
  tone: Tone;
};

/** A band of the risk distribution, in dial order: safest first. */
export type GaugeBand = { value: number; tone: Tone };

const GAUGE_TICKS = 41;

/**
 * 41 radial ticks sweeping -90°→+90°, split across the risk bands.
 *
 * The dial used to fill only with the low-risk share, in one colour. That made
 * it useless in exactly the case worth looking at: a library where nothing is
 * low risk rendered as a uniformly grey arc reading 0%, while the legend
 * underneath reported six elevated and two high. All of the information was in
 * the caption and none of it in the picture.
 *
 * Now every scored document is on the dial and coloured by its band, so the
 * arc shows the shape of the library and the headline number stays the metric
 * the card is named for.
 */
export function buildGaugeTicks(bands: GaugeBand[]): GaugeTick[] {
  const allocation = allocate(bands, GAUGE_TICKS);

  return Array.from({ length: GAUGE_TICKS }, (_, i) => {
    const tone = allocation[i];
    const on = tone !== null;
    return {
      angle: -90 + (180 * i) / (GAUGE_TICKS - 1),
      on,
      height: on ? 20 : 14,
      offset: on ? 104 : 107,
      // A gentle ramp across the whole dial, so it still reads as sweeping to
      // its value rather than switching on all at once.
      opacity: on ? Number((0.55 + 0.45 * (i / (GAUGE_TICKS - 1))).toFixed(2)) : 1,
      tone: tone ?? "--idle",
    };
  });
}

/**
 * Spreads `count` ticks across the bands in proportion to their values.
 *
 * Largest-remainder rather than rounding each independently, so the ticks
 * always total exactly `count`. Any band with at least one document is
 * guaranteed at least one tick: a single high-risk document in a library of a
 * hundred rounds to zero, and that is the one nobody can afford to lose.
 */
function allocate(bands: GaugeBand[], count: number): (Tone | null)[] {
  const total = bands.reduce((sum, b) => sum + b.value, 0);
  if (total === 0) return new Array<Tone | null>(count).fill(null);

  const exact = bands.map((b) => (b.value / total) * count);
  const shares = exact.map(Math.floor);

  let left = count - shares.reduce((a, b) => a + b, 0);
  const byRemainder = exact
    .map((e, i) => ({ i, r: e - Math.floor(e) }))
    .sort((a, b) => b.r - a.r);

  for (let k = 0; left > 0; k += 1, left -= 1) {
    shares[byRemainder[k % byRemainder.length].i] += 1;
  }

  // Rescue any band that rounded away, taking from the largest.
  bands.forEach((band, i) => {
    if (band.value === 0 || shares[i] > 0) return;
    const biggest = shares.indexOf(Math.max(...shares));
    if (shares[biggest] > 1) {
      shares[biggest] -= 1;
      shares[i] += 1;
    }
  });

  return bands.flatMap((band, i) => new Array<Tone | null>(shares[i]).fill(band.tone));
}

