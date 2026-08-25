"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { exportReport, getDashboard, tickProcessing, type Simulate } from "@/lib/api";
import { useAction, useAsync } from "@/lib/use-async";
import { RANGE_DATES, RANGE_LABEL, WORKSPACE } from "@/lib/mock/data";
import type { DateRange } from "@/lib/types";
import { riskTone, v } from "@/lib/design";
import { buildChart, buildGaugeTicks } from "@/lib/chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { RiskBadge, StatusBadge } from "@/components/documind/badges";
import {
  EmptyPanel,
  ErrorPanel,
  InlineError,
  Spinner,
  StateSwitcher,
  Toaster,
  useToasts,
} from "@/components/documind/feedback";
import {
  BarsIcon,
  CalendarIcon,
  ChatIcon,
  CaretDownIcon,
  ClockIcon,
  DownloadIcon,
  FileIcon,
  KebabIcon,
  PlusIcon,
  ShieldIcon,
  TrendDownIcon,
  TrendUpIcon,
  WarningIcon,
} from "@/components/ui/icons";

const KPI_ICONS = { bars: BarsIcon, warning: WarningIcon, shield: ShieldIcon, clock: ClockIcon } as const;
const TH = "h-auto px-0 pb-2 text-[10px] font-semibold tracking-[.08em] uppercase text-[var(--text-3)]";
const RANGES: DateRange[] = ["7d", "30d", "90d"];

const SIMULATIONS = [
  { value: "ok" as const, label: "Default" },
  { value: "slow" as const, label: "Slow" },
  { value: "partial" as const, label: "Partial" },
  { value: "empty" as const, label: "Empty" },
  { value: "error" as const, label: "Error" },
];

export function DashboardView() {
  const [simulate, setSimulate] = useState<Simulate>("ok");
  const [range, setRange] = useState<DateRange>("30d");
  const { toasts, push, update, dismiss } = useToasts();

  const dash = useAsync((signal) => getDashboard(range, { simulate, signal }), [range, simulate]);
  const exportAction = useAction(exportReport);

  // Flagged rows that are mid-pipeline keep moving while the dashboard is open.
  const { data: dashData, reload: reloadDash } = dash;
  useEffect(() => {
    const live = dashData?.flagged.some((d) => d.status === "processing");
    if (!live || simulate !== "ok") return;
    const t = setInterval(() => {
      tickProcessing();
      reloadDash();
    }, 2600);
    return () => clearInterval(t);
  }, [dashData, reloadDash, simulate]);

  async function runExport() {
    const id = push({ tone: "--accent", glyph: "", pending: true, title: "Building report…", body: `${RANGE_LABEL[range]} · all panels included.` }, 0);
    const result = await exportAction.run(range);
    if (result) {
      update(id, { pending: false, tone: "--ok", glyph: "✓", title: "Report ready", body: `${result.filename} · ${result.rows.toLocaleString()} documents.` });
    } else {
      update(id, { pending: false, tone: "--bad", glyph: "✕", title: "Export failed", body: "The report service did not respond. Try again." });
    }
  }

  const data = dash.data;
  const chart = buildChart(data?.seriesSeed ?? 0);
  const ticks = buildGaugeTicks(data?.gauge.pct ?? 0);
  const loading = dash.status === "loading";

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto px-4 pt-5 pb-20 sm:px-6">
      {/* Page header --------------------------------------------------- */}
      <div className="anim-up flex flex-none flex-wrap items-center gap-2.5">
        <div className="flex flex-col gap-[3px]">
          <h1 className="text-2xl font-bold tracking-[-.025em] text-[var(--text)]">Dashboard</h1>
          <span className="flex items-center gap-2 text-xs text-[var(--text-3)]">
            {WORKSPACE.orgFull} — operations overview · {WORKSPACE.region}
            {data && dash.status === "ready" && <span>· updated {data.generatedAt}</span>}
            {(dash.status === "reloading" || loading) && <Spinner size={11} />}
          </span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="surface" size="dm" className="hidden font-medium text-[var(--text)] xl:inline-flex">
            <CalendarIcon size={14} color="var(--text-3)" />
            {RANGE_DATES[range]}
          </Button>

          {/* Portaled, so the panel can't be trapped behind the KPI cards the
              way an inline absolute menu was. */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="surface" size="dm" className="group/range font-medium text-[var(--text)]">
                {RANGE_LABEL[range]}
                <span className="flex transition-transform duration-200 group-aria-expanded/range:rotate-180">
                  <CaretDownIcon size={13} color="var(--text-3)" />
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              sideOffset={6}
              style={{ width: 160 }}
              className="anim-down rounded-xl p-1.5 shadow-[0_14px_34px_rgba(11,18,32,.16)]"
            >
              {RANGES.map((r) => (
                <DropdownMenuItem
                  key={r}
                  onSelect={() => setRange(r)}
                  className="rounded-[9px] px-2.5 py-[7px] text-xs text-[var(--text-2)]"
                >
                  <span className="min-w-0 flex-1 truncate">{RANGE_LABEL[r]}</span>
                  {range === r && <span className="flex-none text-[10px] text-primary">✓</span>}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <Button variant="surface" size="dm" className="hidden text-xs font-medium lg:inline-flex">
            <PlusIcon size={14} color="var(--text-2)" />
            Add widget
          </Button>
          {/* The corpus-wide chat is one hop from the metrics it explains. */}
          <Button variant="soft" size="dm" asChild>
            <Link href="/chat">
              <ChatIcon size={15} color="var(--accent)" />
              Ask
            </Link>
          </Button>
          <Button size="dm" onClick={runExport} disabled={exportAction.pending || loading || dash.status === "error"}>
            {exportAction.pending ? (
              <Spinner size={13} color="#fff" track="rgba(255,255,255,.4)" />
            ) : (
              <DownloadIcon size={15} color="#fff" />
            )}
            {exportAction.pending ? "Exporting…" : "Export"}
          </Button>
        </div>
      </div>

      {dash.status === "error" && dash.error && (
        <ErrorPanel
          title={dash.error.title}
          detail={dash.error.detail}
          code={dash.error.code}
          onRetry={dash.retry}
          actions={
            <Button asChild variant="surface" size="dmQuiet">
              <Link href="/documents">
              Go to documents
              </Link>
            </Button>
          }
        />
      )}

      {loading && <DashboardSkeleton slow={simulate === "slow"} />}

      {data && dash.status !== "error" && !loading && (
        <div
          className="flex flex-col gap-4 transition-opacity"
          style={{ opacity: dash.status === "reloading" ? 0.72 : 1 }}
        >
          {data.degraded && (
            <InlineError
              tone="--warn"
              title={`${data.degraded.panel} could not be computed`}
              detail={data.degraded.message}
              onRetry={dash.reload}
            />
          )}

          {/* KPI row -------------------------------------------------- */}
          <div className="grid flex-none grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {data.kpis.map((kpi, i) => {
              const Icon = KPI_ICONS[kpi.icon];
              const Trend = kpi.direction === "up" ? TrendUpIcon : TrendDownIcon;
              const zero = kpi.value === "0";
              return (
                <Card
                  key={kpi.key}
                  className="anim-up lift gap-3 rounded-[14px] p-[18px]"
                  style={{ ["--i" as string]: i }}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-[13px] font-medium text-[var(--text-2)]">{kpi.label}</span>
                    <span
                      className="ml-auto flex size-[30px] items-center justify-center rounded-full"
                      style={{ background: v(kpi.iconTone, "-soft") }}
                    >
                      <Icon size={15} color={v(kpi.iconTone)} />
                    </span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <span
                      key={kpi.value}
                      className="anim-pop text-[28px] leading-none font-bold tracking-[-.03em] text-[var(--text)]"
                    >
                      {kpi.value}
                      {kpi.unit && <span className="text-[15px] font-semibold text-[var(--text-3)]">{kpi.unit}</span>}
                    </span>
                    {!zero && (
                      <span
                        className="inline-flex items-center gap-[3px] rounded-full px-2 py-1 text-[11px] font-semibold"
                        style={{ color: v(kpi.deltaTone), background: v(kpi.deltaTone, "-soft") }}
                      >
                        <Trend size={11} color={v(kpi.deltaTone)} />
                        {kpi.delta}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-[var(--text-3)]">{kpi.footnote}</span>
                </Card>
              );
            })}
          </div>

          {/* Volume chart + gauge ------------------------------------- */}
          <div className="grid flex-none grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
            <Card className="anim-up lift gap-3 rounded-[14px] p-4" style={{ ["--i" as string]: 4 }}>
              <div className="flex items-start">
                <div className="flex flex-col gap-0.5">
                  <CardTitle className="text-sm font-semibold">Document volume — {RANGE_LABEL[range].toLowerCase()}</CardTitle>
                  <CardDescription className="text-[11px]">Daily ingestion across document types</CardDescription>
                </div>
                <div className="ml-auto flex items-center gap-3.5">
                  {chart.paths.map((s) => (
                    <span key={s.name} className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-2)]">
                      <span className="h-0.5 w-3.5 flex-none rounded-full" style={{ background: s.swatch }} />
                      {s.name}
                    </span>
                  ))}
                </div>
              </div>

              {data.seriesSeed < 0 ? (
                <div className="flex h-36 flex-col items-center justify-center gap-2 rounded-[10px] border border-dashed border-[var(--border-strong)]">
                  <span className="text-[13px] font-medium text-[var(--text)]">No ingestion in this period</span>
                  <span className="text-[12px] text-[var(--text-2)]">
                    Upload documents to start charting daily volume.
                  </span>
                </div>
              ) : (
                <div className="flex gap-2">
                  <div className="flex h-36 w-[22px] flex-none flex-col items-end justify-between pt-[3.5px] pb-[1.5px] font-mono text-[9px] leading-none text-[var(--text-3)]">
                    {[60, 45, 30, 15, 0].map((n) => (
                      <span key={n}>{n}</span>
                    ))}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <svg
                      key={range}
                      viewBox="0 0 600 144"
                      preserveAspectRatio="none"
                      className="dm-chart-in h-36 w-full"
                    >
                      {chart.grid.map((g, i) => (
                        <line key={i} x1={0} y1={g.y} x2={g.x2} y2={g.y} stroke="var(--border)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
                      ))}
                      {chart.paths.map((p) => (
                        <path
                          key={p.name}
                          d={p.d}
                          fill="none"
                          stroke={p.stroke}
                          strokeWidth={1.75}
                          strokeDasharray={p.dash}
                          strokeLinecap="round"
                          vectorEffect="non-scaling-stroke"
                        />
                      ))}
                    </svg>
                    <div className="flex justify-between font-mono text-[9px] text-[var(--text-3)]">
                      {["Jul 26", "Jul 31", "Aug 05", "Aug 10", "Aug 15", "Aug 20", "Aug 24"].map((d) => (
                        <span key={d}>{d}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </Card>

            <Card className="anim-up lift gap-2.5 rounded-[14px] px-[18px] pt-4 pb-[18px]" style={{ ["--i" as string]: 5 }}>
              <div className="flex items-start">
                <div className="flex flex-col gap-0.5">
                  <CardTitle className="text-sm font-semibold">Low-risk rate</CardTitle>
                  <CardDescription className="text-[11px]">Share of documents scoring under 34</CardDescription>
                </div>
                <Button variant="ghost" size="icon-sm" className="ml-auto text-[var(--text-3)]">
                  <KebabIcon />
                </Button>
              </div>

              <div className="relative h-[132px] w-[250px] max-w-full self-center">
                {ticks.map((t, i) => (
                  <span
                    key={i}
                    className="anim-fade absolute bottom-0 left-[calc(50%-2px)] w-1 origin-[50%_100%] rounded-[3px]"
                    style={{
                      height: t.height,
                      transform: `rotate(${t.angle.toFixed(1)}deg) translateY(-${t.offset}px)`,
                      background: t.on ? "var(--ok)" : "var(--border)",
                      opacity: t.opacity,
                      animationDuration: ".2s",
                      animationDelay: `${i * 14}ms`,
                      transition: "background .3s var(--ease-out), height .3s var(--ease-out)",
                    }}
                  />
                ))}
                <div className="absolute inset-x-0 bottom-0.5 flex flex-col items-center gap-0.5">
                  <span
                    key={data.gauge.pct}
                    className="anim-pop text-[34px] leading-none font-bold tracking-[-.03em] text-[var(--text)]"
                  >
                    {data.gauge.pct}%
                  </span>
                  <span className="text-[11px] text-[var(--text-3)]">{data.gauge.target}</span>
                </div>
              </div>

              <Button variant="surface" size="dmMd" className="h-[34px] self-center px-4 font-semibold" asChild>
                <Link href="/documents">Show details</Link>
              </Button>

              <div className="flex items-center justify-center gap-4 pt-0.5">
                {data.gauge.legend.map((l) => (
                  <span key={l.label} className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-2)]">
                    <span className="size-[7px] rounded-full" style={{ background: v(l.tone) }} />
                    {l.label} {l.value.toLocaleString()}
                  </span>
                ))}
              </div>
            </Card>
          </div>

          {/* Flagged + exceptions ------------------------------------- */}
          <div className="grid min-h-fit flex-[1_0_auto] grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
            <Card className="anim-up min-h-[412px] gap-0 overflow-hidden rounded-[14px] p-0" style={{ ["--i" as string]: 6 }}>
              <CardHeader className="flex-none items-start gap-0 px-[18px] pt-[18px] pb-3">
                <div className="flex flex-col gap-0.5">
                  <CardTitle className="text-[15px] font-semibold tracking-[-.01em]">
                    Recent flagged documents
                  </CardTitle>
                  <CardDescription className="text-[11px]">
                    Latest items needing operator attention
                  </CardDescription>
                </div>
                <div className="ml-auto flex items-center gap-3">
                  <Link href="/documents" className="text-xs font-medium">
                    View all
                  </Link>
                  <Button variant="ghost" size="icon-sm" className="text-[var(--text-3)]">
                    <KebabIcon />
                  </Button>
                </div>
              </CardHeader>

              {data.flagged.length === 0 ? (
                <div className="flex flex-1 flex-col items-center justify-center gap-3 px-8 pb-8 text-center">
                  <span className="flex size-11 items-center justify-center rounded-[10px] border border-[var(--ok-border)] bg-[var(--ok-soft)] text-[17px] text-[var(--ok)]">
                    ✓
                  </span>
                  <span className="text-[15px] font-semibold text-[var(--text)]">Nothing flagged</span>
                  <span className="max-w-[380px] text-[13px] leading-relaxed text-[var(--text-2)] text-pretty">
                    Every document in this period was auto-approved. Flagged items appear here as soon as a
                    document scores 60 or above, or fails mid-pipeline.
                  </span>
                </div>
              ) : (
                <div className="dm-scroll-x">
                <Table className="table-fixed min-w-[760px]">
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent [&>th]:first:pl-[18px] [&>th]:last:pr-[18px]">
                      {/* 18px row padding + 30px icon + gap — anything narrower
                          lets the icon run under the filename. */}
                      <TableHead className={`${TH} w-[62px]`} />
                      <TableHead className={TH}>Document</TableHead>
                      <TableHead className={`${TH} w-[100px]`}>Type</TableHead>
                      <TableHead className={`${TH} w-[180px]`}>Counterparty</TableHead>
                      <TableHead className={`${TH} w-[60px]`}>Risk</TableHead>
                      <TableHead className={`${TH} w-[48px]`}>Flags</TableHead>
                      <TableHead className={`${TH} w-[124px]`}>Status</TableHead>
                      <TableHead className={`${TH} w-[70px] text-right`}>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.flagged.map((f, i) => (
                      <TableRow
                        key={f.id}
                        className="anim-row h-14 border-border transition-colors hover:bg-[var(--surface-2)] [&>td]:first:pl-[18px] [&>td]:last:pr-[18px]"
                        style={{ ["--i" as string]: i, ["--stagger" as string]: "26ms" }}
                      >
                        <TableCell className="px-0">
                          <span className="flex size-[30px] items-center justify-center rounded-[10px] border border-border bg-[var(--surface-2)]">
                            <FileIcon size={15} color="var(--text-3)" />
                          </span>
                        </TableCell>
                        <TableCell className="truncate px-0 font-mono text-xs font-medium text-[var(--text)]" title={f.name}>
                          {f.name}
                        </TableCell>
                        <TableCell className="truncate px-0 text-xs text-[var(--text-2)]">{f.type}</TableCell>
                        <TableCell className="truncate px-0 text-xs font-medium text-[var(--text)]">
                          {f.counterparty}
                        </TableCell>
                        <TableCell className="px-0">
                          {f.risk === null ? (
                            <RiskBadge tone="--idle">—</RiskBadge>
                          ) : (
                            <RiskBadge score={f.risk} tone={riskTone(f.risk)} />
                          )}
                        </TableCell>
                        <TableCell className="px-0 font-mono text-xs text-[var(--text-2)]">{f.flags}</TableCell>
                        <TableCell className="px-0">
                          <StatusBadge status={f.status} label={f.status === "completed" ? f.verdict : undefined} />
                        </TableCell>
                        <TableCell className="px-0 text-right">
                          <Link href={`/documents/${f.id}`} className="text-xs font-semibold">
                            Review
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
              )}
            </Card>

            <Card className="anim-up gap-3.5 rounded-[14px] p-4" style={{ ["--i" as string]: 7 }}>
              <div className="flex flex-col gap-0.5">
                <CardTitle className="text-sm font-semibold">Top exception types</CardTitle>
                <CardDescription className="text-[11px]">Frequency across flagged documents</CardDescription>
              </div>
              <CardContent className="flex flex-col gap-3 p-0">
                {data.exceptions.length === 0 ? (
                  <span className="text-[12px] leading-relaxed text-[var(--text-2)] text-pretty">
                    {data.degraded
                      ? "This panel could not be computed for the selected period. Every other panel is current."
                      : "No exceptions were raised in this period."}
                  </span>
                ) : (
                  data.exceptions.map(([label, pct], i) => (
                    <div key={label} className="anim-up flex flex-col gap-1.5" style={{ ["--i" as string]: i }}>
                      <div className="flex items-baseline">
                        <span className="text-xs text-[var(--text-2)]">{label}</span>
                        <span className="ml-auto font-mono text-[11px] text-[var(--text-3)]">{pct}</span>
                      </div>
                      <Progress
                        value={pct}
                        className="h-1"
                        indicatorClassName="rounded-full transition-transform duration-700 ease-[cubic-bezier(.22,.8,.3,1)]"
                        indicatorStyle={{ background: "var(--c2)" }}
                      />
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          {data.seriesSeed < 0 && (
            <EmptyPanel
              compact
              title="This workspace has no processed documents yet"
              body="Every number above is zero because nothing has been ingested in the selected period. Upload a batch to populate the dashboard."
              actions={
                <Button asChild size="dm">
                  <Link href="/upload" style={{ padding: "0 16px" }}>
                  Upload documents
                  </Link>
                </Button>
              }
            />
          )}
        </div>
      )}

      <Toaster toasts={toasts} onDismiss={dismiss} />
      <StateSwitcher value={simulate} options={SIMULATIONS} onChange={setSimulate} />
    </div>
  );
}

function DashboardSkeleton({ slow }: { slow: boolean }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i} className="gap-3 rounded-[14px] p-[18px]">
            <div className="flex items-center gap-2.5">
              <span className="skeleton h-3 w-[120px]" />
              <span className="skeleton ml-auto size-[30px] rounded-full" />
            </div>
            <span className="skeleton h-7 w-[90px]" />
            <span className="skeleton h-2.5 w-[140px]" />
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="gap-3 rounded-[14px] p-4">
          <span className="skeleton h-3.5 w-[220px]" />
          <span className="skeleton h-36 w-full" />
        </Card>
        <Card className="items-center gap-3 rounded-[14px] p-4">
          <span className="skeleton h-3.5 w-[140px] self-start" />
          <span className="skeleton h-[132px] w-[230px] rounded-t-full" />
          <span className="skeleton h-8 w-[120px]" />
        </Card>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="min-h-[412px] gap-3 rounded-[14px] p-[18px]">
          <span className="skeleton h-4 w-[240px]" />
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <span key={i} className="skeleton h-10 w-full" />
          ))}
        </Card>
        <Card className="gap-3.5 rounded-[14px] p-4">
          <span className="skeleton h-3.5 w-[160px]" />
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <span key={i} className="skeleton h-6 w-full" />
          ))}
        </Card>
      </div>
      <div className="flex items-center justify-center gap-2.5 pt-1">
        <Spinner size={12} />
        <span className="text-xs text-[var(--text-3)]">
          {slow ? "Still aggregating — the warehouse is slow right now…" : "Loading operations metrics…"}
        </span>
      </div>
    </div>
  );
}
