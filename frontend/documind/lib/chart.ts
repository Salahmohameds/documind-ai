/** name, stroke var, seed, dash pattern */
const SERIES: [string, string, number, string][] = [
  ["Invoice", "var(--c1)", 22, "0"],
  ["Contract", "var(--c2)", 71, "0"],
  ["Amendment", "var(--c3)", 137, "5 3"],
  ["Statement", "var(--c4)", 211, "1.5 3"],
];

const N = 30;
const W = 600;
const TOP = 8;
const H = 128;
const MAX = 60;

function smooth(pts: [number, number][]) {
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

/**
 * Deterministic synthetic ingestion curves, reproduced from the design canvas so
 * the chart looks identical until real volume data is wired in.
 */
export function buildChart(offset = 0): { paths: ChartSeries[]; grid: { y: number; x2: number }[] } {
  const paths = SERIES.map(([name, stroke, baseSeed, dash], si) => {
    const seed = baseSeed + offset;
    const pts: [number, number][] = [];
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1);
      const value =
        16 +
        si * 4 +
        11 * Math.sin(t * 6.1 + seed * 0.37) +
        7 * Math.sin(t * 13.3 + seed * 0.91) +
        4 * Math.cos(t * 21.7 + seed * 0.13);
      pts.push([t * W, TOP + H - (Math.max(2, Math.min(MAX, value)) / MAX) * H]);
    }
    return {
      name,
      stroke,
      dash,
      d: smooth(pts),
      swatch:
        dash === "0"
          ? stroke
          : `repeating-linear-gradient(to right,${stroke} 0 4px,transparent 4px 7px)`,
    };
  });

  const grid = [0, 15, 30, 45, 60].map((value) => ({
    y: TOP + H - (value / MAX) * H,
    x2: W,
  }));

  return { paths, grid };
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
