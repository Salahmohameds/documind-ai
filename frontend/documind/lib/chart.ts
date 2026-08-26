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

export type GaugeTick = {
  angle: number;
  on: boolean;
  height: number;
  offset: number;
  opacity: number;
};

/** 41 radial ticks sweeping -90°→+90°; the first `pct`% are filled. */
export function buildGaugeTicks(pct: number): GaugeTick[] {
  const count = 41;
  const filled = Math.round((pct / 100) * count);
  return Array.from({ length: count }, (_, i) => {
    const on = i < filled;
    return {
      angle: -90 + (180 * i) / (count - 1),
      on,
      height: on ? 20 : 14,
      offset: on ? 104 : 107,
      opacity: on ? Number((0.35 + 0.65 * (i / filled)).toFixed(2)) : 1,
    };
  });
}
