"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { exportReport, getDashboard } from "@/lib/api";
import { useAction, useAsync } from "@/lib/use-async";
import { RANGE_LABEL, WORKSPACE, rangeDates } from "@/lib/mock/data";
import { downloadCsv } from "@/lib/download";
import type { DateRange } from "@/lib/types";
import { riskTone, v } from "@/lib/design";
import { buildChart, buildGaugeTicks } from "@/lib/chart";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RiskBadge, StatusBadge } from "@/components/documind/badges";
import {
  Anim,
  Counter,
  DrawIn,
  Lift,
  Shimmer,
  Stagger,
  motion,
} from "@/components/motion";
import {
  EmptyPanel,
  ErrorPanel,
  InlineError,
  Spinner,
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

const KPI_ICONS = {
  bars: BarsIcon,
  warning: WarningIcon,
  shield: ShieldIcon,
  clock: ClockIcon,
} as const;
const TH =
  "h-auto px-0 pb-2 text-[10px] font-semibold tracking-[.08em] uppercase text-[var(--text-3)]";
const RANGES: DateRange[] = ["7d", "30d", "90d"];

export function DashboardView() {
  const [range, setRange] = useState<DateRange>("30d");
  const { toasts, push, update, dismiss } = useToasts();

  const dash = useAsync((signal) => getDashboard(range, { signal }), [range]);
  const exportAction = useAction(exportReport);

  // Anything mid-pipeline means the numbers are still moving, so the dashboard
  // re-reads itself until the queue drains.
  const { data: dashData, reload: reloadDash } = dash;
  useEffect(() => {
    const live = dashData?.flagged.some(
      (d) => d.status === "processing" || d.status === "queued",
    );
    if (!live) return;
    const t = setInterval(reloadDash, 4000);
    return () => clearInterval(t);
  }, [dashData, reloadDash]);

  async function runExport() {
    const id = push(
      {
        tone: "--accent",
        glyph: "",
        pending: true,
        title: "Building report…",
        body: `${RANGE_LABEL[range]} · all panels included.`,
      },
      0,
    );
    const result = await exportAction.run(range);
    if (result) {
      downloadCsv(result);
      update(id, {
        pending: false,
        tone: "--ok",
        glyph: "✓",
        title: "Report downloaded",
        body: `${result.filename} · ${result.rows} metrics.`,
      });
    } else {
      update(id, {
        pending: false,
        tone: "--bad",
        glyph: "✕",
        title: "Export failed",
        body:
          exportAction.error?.detail ??
          "The report could not be built. Try again.",
      });
    }
  }

  const data = dash.data;
  const chart = buildChart(data?.series ?? []);
  const ticks = buildGaugeTicks(data?.gauge.legend ?? []);
  const loading = dash.status === "loading";

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto px-4 pt-5 pb-20 sm:px-6">
      {/* Page header --------------------------------------------------- */}
      <Anim
        preset="blur"
        className="flex flex-none flex-wrap items-center gap-2.5"
      >
        <div className="flex flex-col gap-[3px]">
          <h1 className="text-2xl font-bold tracking-[-.025em] text-[var(--text)]">
            Dashboard
          </h1>
          <span className="flex items-center gap-2 text-xs text-[var(--text-3)]">
            {WORKSPACE.orgFull} — operations overview · {WORKSPACE.region}
            {data && dash.status === "ready" && (
              <span>· updated {data.generatedAt}</span>
            )}
            {(dash.status === "reloading" || loading) && <Spinner size={11} />}
          </span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="surface"
            size="dm"
            className="hidden font-medium text-[var(--text)] xl:inline-flex"
          >
            <CalendarIcon size={14} color="var(--text-3)" />
            {rangeDates(range)}
          </Button>

          {/* Portaled, so the panel can't be trapped behind the KPI cards the
              way an inline absolute menu was. */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="surface"
                size="dm"
                className="group/range font-medium text-[var(--text)]"
              >
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
              className="rounded-xl p-1.5 shadow-[0_14px_34px_rgba(11,18,32,.16)]"
            >
              {RANGES.map((r) => (
                <DropdownMenuItem
                  key={r}
                  onSelect={() => setRange(r)}
                  className="rounded-[9px] px-2.5 py-[7px] text-xs text-[var(--text-2)]"
                >
                  <span className="min-w-0 flex-1 truncate">
                    {RANGE_LABEL[r]}
                  </span>
                  {range === r && (
                    <span className="flex-none text-[10px] text-primary">
                      ✓
                    </span>
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* The corpus-wide chat is one hop from the metrics it explains. */}
          <Button variant="soft" size="dm" asChild>
            <Link href="/chat">
              <ChatIcon size={15} color="var(--accent)" />
              Ask
            </Link>
          </Button>
          <Button
            size="dm"
            onClick={runExport}
            disabled={
              exportAction.pending || loading || dash.status === "error"
            }
          >
            {exportAction.pending ? (
              <Spinner size={13} color="#fff" track="rgba(255,255,255,.4)" />
            ) : (
              <DownloadIcon size={15} color="#fff" />
            )}
            {exportAction.pending ? "Exporting…" : "Export"}
          </Button>
        </div>
      </Anim>

      {dash.status === "error" && dash.error && (
        <ErrorPanel
          title={dash.error.title}
          detail={dash.error.detail}
          code={dash.error.code}
          onRetry={dash.retry}
          actions={
            <Button asChild variant="surface" size="dmQuiet">
              <Link href="/documents">Go to documents</Link>
            </Button>
          }
        />
      )}

      {loading && <DashboardSkeleton />}

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
          <Stagger className="grid flex-none grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {data.kpis.map((kpi) => {
              const Icon = KPI_ICONS[kpi.icon];
              const Trend =
                kpi.direction === "up" ? TrendUpIcon : TrendDownIcon;
              // A KPI with no delta is a live gauge, not a period total —
              // there is nothing to compare it against, so no pill is shown.
              const showDelta = kpi.delta !== undefined && kpi.value !== "0";
              const deltaTone = kpi.deltaTone ?? "--idle";
              return (
                <Lift
                  key={kpi.key}
                  as={Card}
                  className="gap-3 rounded-[14px] p-[18px]"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-[13px] font-medium text-[var(--text-2)]">
                      {kpi.label}
                    </span>
                    <span
                      className="ml-auto flex size-[30px] items-center justify-center rounded-full"
                      style={{ background: v(kpi.iconTone, "-soft") }}
                    >
                      <Icon size={15} color={v(kpi.iconTone)} />
                    </span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <Anim
                      as="span"
                      preset="pop"
                      key={kpi.value}
                      className="text-[28px] leading-none font-bold tracking-[-.03em] text-[var(--text)]"
                    >
                      {kpi.value}
                      {kpi.unit && (
                        <span className="text-[15px] font-semibold text-[var(--text-3)]">
                          {kpi.unit}
                        </span>
                      )}
                    </Anim>
                    {showDelta && (
                      <span
                        className="inline-flex items-center gap-[3px] rounded-full px-2 py-1 text-[11px] font-semibold"
                        style={{
                          color: v(deltaTone),
                          background: v(deltaTone, "-soft"),
                        }}
                      >
                        <Trend size={11} color={v(deltaTone)} />
                        {kpi.delta}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-[var(--text-3)]">
                    {kpi.footnote}
                  </span>
                </Lift>
              );
            })}
          </Stagger>

          {/* Volume chart + gauge ------------------------------------- */}
          <Stagger className="grid flex-none grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
            <Lift as={Card} className="gap-3 rounded-[14px] p-4">
              <div className="flex items-start">
                <div className="flex flex-col gap-0.5">
                  <CardTitle className="text-sm font-semibold">
                    Document volume — {RANGE_LABEL[range].toLowerCase()}
                  </CardTitle>
                  <CardDescription className="text-[11px]">
                    Daily ingestion across document types
                  </CardDescription>
                </div>
                <div className="ml-auto flex items-center gap-3.5">
                  {chart.paths.map((s) => (
                    <span
                      key={s.name}
                      className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-2)]"
                    >
                      <span
                        className="h-0.5 w-3.5 flex-none rounded-full"
                        style={{ background: s.swatch }}
                      />
                      {s.name}
                    </span>
                  ))}
                </div>
              </div>

              {data.volume === 0 ? (
                <div className="flex h-36 flex-col items-center justify-center gap-2 rounded-[10px] border border-dashed border-[var(--border-strong)]">
                  <span className="text-[13px] font-medium text-[var(--text)]">
                    No ingestion in this period
                  </span>
                  <span className="text-[12px] text-[var(--text-2)]">
                    Upload documents to start charting daily volume.
                  </span>
                </div>
              ) : (
                <div className="flex gap-2">
                  <div className="flex h-36 w-[22px] flex-none flex-col items-end justify-between pt-[3.5px] pb-[1.5px] font-mono text-[9px] leading-none text-[var(--text-3)]">
                    {chart.ticks.map((n, i) => (
                      <span key={i}>{n}</span>
                    ))}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <DrawIn key={range}>
                      <svg
                        viewBox="0 0 600 144"
                        preserveAspectRatio="none"
                        className="h-36 w-full"
                      >
                        {chart.grid.map((g, i) => (
                          <line
                            key={i}
                            x1={0}
                            y1={g.y}
                            x2={g.x2}
                            y2={g.y}
                            stroke="var(--border)"
                            strokeWidth={1}
                            vectorEffect="non-scaling-stroke"
                          />
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
                    </DrawIn>
                    <div className="flex justify-between font-mono text-[9px] text-[var(--text-3)]">
                      {/* From the API, which derives them from the same window
                          the buckets came from. These used to be seven literal
                          dates in July, so the axis read identically whether
                          the range was 7 days or 90. */}
                      {data.axis.map((d) => (
                        <span key={d}>{d}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </Lift>

            <Lift
              as={Card}
              className="gap-2.5 rounded-[14px] px-[18px] pt-4 pb-[18px]"
            >
              <div className="flex items-start">
                <div className="flex flex-col gap-0.5">
                  <CardTitle className="text-sm font-semibold">
                    Low-risk rate
                  </CardTitle>
                  <CardDescription className="text-[11px]">
                    {/* The number and the dial answer different questions, so
                        the caption names both rather than only the number. */}
                    Share scoring under 34 · dial shows the full distribution
                  </CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="ml-auto text-[var(--text-3)]"
                >
                  <KebabIcon />
                </Button>
              </div>

              <div className="relative h-[132px] w-[250px] max-w-full self-center">
                {/* The ticks light up in dial order, so the gauge reads as
                    sweeping to its value rather than appearing at it. Each
                    tick carries its own band's colour: the dial is the risk
                    distribution, and the number below it is the low-risk
                    share of that distribution. */}
                {ticks.map((t, i) => (
                  <motion.span
                    key={i}
                    className="absolute bottom-0 left-[calc(50%-2px)] w-1 origin-[50%_100%] rounded-[3px]"
                    initial={{ opacity: 0 }}
                    animate={{
                      opacity: t.opacity,
                      // Coloured by the band it represents, so the arc shows
                      // the whole distribution rather than one share of it.
                      backgroundColor: t.on ? v(t.tone) : "var(--border)",
                    }}
                    transition={{ duration: 0.24, delay: 0.1 + i * 0.012 }}
                    style={{
                      height: t.height,
                      transform: `rotate(${t.angle.toFixed(1)}deg) translateY(-${t.offset}px)`,
                    }}
                  />
                ))}
                <div className="absolute inset-x-0 bottom-0.5 flex flex-col items-center gap-0.5">
                  {/* Counts up in step with the dial sweep above it. */}
                  <Counter
                    key={data.gauge.pct}
                    value={data.gauge.pct}
                    suffix="%"
                    delay={0.1}
                    duration={0.7}
                    className="text-[34px] leading-none font-bold tracking-[-.03em] text-[var(--text)]"
                  />
                  <span className="text-[11px] text-[var(--text-3)]">
                    {data.gauge.target}
                  </span>
                </div>
              </div>

              <Button
                variant="surface"
                size="dmMd"
                className="h-[34px] self-center px-4 font-semibold"
                asChild
              >
                <Link href="/documents">Show details</Link>
              </Button>

              <div className="flex items-center justify-center gap-4 pt-0.5">
                {data.gauge.legend.map((l) => (
                  <span
                    key={l.label}
                    className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-2)]"
                  >
                    <span
                      className="size-[7px] rounded-full"
                      style={{ background: v(l.tone) }}
                    />
                    {l.label} {l.value.toLocaleString()}
                  </span>
                ))}
              </div>
            </Lift>
          </Stagger>

          {/* Flagged + exceptions ------------------------------------- */}
          <Stagger
            inView
            className="grid min-h-fit flex-[1_0_auto] grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]"
          >
            <Anim
              as={Card}
              className="min-h-[412px] gap-0 overflow-hidden rounded-[14px] p-0"
            >
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
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-[var(--text-3)]"
                  >
                    <KebabIcon />
                  </Button>
                </div>
              </CardHeader>

              {data.flagged.length === 0 ? (
                <div className="flex flex-1 flex-col items-center justify-center gap-3 px-8 pb-8 text-center">
                  <span className="flex size-11 items-center justify-center rounded-[10px] border border-[var(--ok-border)] bg-[var(--ok-soft)] text-[17px] text-[var(--ok)]">
                    ✓
                  </span>
                  <span className="text-[15px] font-semibold text-[var(--text)]">
                    Nothing flagged
                  </span>
                  <span className="max-w-[380px] text-[13px] leading-relaxed text-[var(--text-2)] text-pretty">
                    {/* 34 is the elevated threshold the risk gauge and the
                        document detail both band on. The copy used to say 60,
                        which matched nothing. */}
                    Every document in this period was auto-approved. Flagged
                    items appear here as soon as a document scores 34 or above,
                    or fails mid-pipeline.
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
                        <TableHead className={`${TH} w-[100px]`}>
                          Type
                        </TableHead>
                        <TableHead className={`${TH} w-[180px]`}>
                          Counterparty
                        </TableHead>
                        <TableHead className={`${TH} w-[60px]`}>Risk</TableHead>
                        <TableHead className={`${TH} w-[48px]`}>
                          Flags
                        </TableHead>
                        <TableHead className={`${TH} w-[124px]`}>
                          Status
                        </TableHead>
                        <TableHead className={`${TH} w-[70px] text-right`}>
                          Action
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <Stagger as={TableBody} gap={0.03} delay={0.1}>
                      {data.flagged.map((f) => (
                        <Anim
                          as={TableRow}
                          preset="row"
                          key={f.id}
                          className="h-14 border-border transition-colors hover:bg-[var(--surface-2)] [&>td]:first:pl-[18px] [&>td]:last:pr-[18px]"
                        >
                          <TableCell className="px-0">
                            <span className="flex size-[30px] items-center justify-center rounded-[10px] border border-border bg-[var(--surface-2)]">
                              <FileIcon size={15} color="var(--text-3)" />
                            </span>
                          </TableCell>
                          <TableCell
                            className="truncate px-0 font-mono text-xs font-medium text-[var(--text)]"
                            title={f.name}
                          >
                            {f.name}
                          </TableCell>
                          <TableCell className="truncate px-0 text-xs text-[var(--text-2)]">
                            {f.type}
                          </TableCell>
                          <TableCell className="truncate px-0 text-xs font-medium text-[var(--text)]">
                            {f.counterparty}
                          </TableCell>
                          <TableCell className="px-0">
                            {f.risk === null ? (
                              <RiskBadge tone="--idle">—</RiskBadge>
                            ) : (
                              <RiskBadge
                                score={f.risk}
                                tone={riskTone(f.risk)}
                              />
                            )}
                          </TableCell>
                          <TableCell className="px-0 font-mono text-xs text-[var(--text-2)]">
                            {f.flags}
                          </TableCell>
                          <TableCell className="px-0">
                            <StatusBadge
                              status={f.status}
                              label={
                                f.status === "completed" ? f.verdict : undefined
                              }
                            />
                          </TableCell>
                          <TableCell className="px-0 text-right">
                            <Link
                              href={`/documents/${f.id}`}
                              className="text-xs font-semibold"
                            >
                              Review
                            </Link>
                          </TableCell>
                        </Anim>
                      ))}
                    </Stagger>
                  </Table>
                </div>
              )}
            </Anim>

            <Anim as={Card} className="gap-3.5 rounded-[14px] p-4">
              <div className="flex flex-col gap-0.5">
                <CardTitle className="text-sm font-semibold">
                  Top exception types
                </CardTitle>
                <CardDescription className="text-[11px]">
                  Frequency across flagged documents
                </CardDescription>
              </div>
              <CardContent className="flex flex-col gap-3 p-0">
                {data.exceptions.length === 0 ? (
                  <span className="text-[12px] leading-relaxed text-[var(--text-2)] text-pretty">
                    {data.degraded
                      ? "This panel could not be computed for the selected period. Every other panel is current."
                      : "Nothing needed attention in this period — no document failed or scored above the low-risk band."}
                  </span>
                ) : (
                  data.exceptions.map(([label, pct], i) => (
                    <Anim
                      key={label}
                      delay={0.18 + i * 0.05}
                      className="flex flex-col gap-1.5"
                    >
                      <div className="flex items-baseline">
                        <span className="text-xs text-[var(--text-2)]">
                          {label}
                        </span>
                        <span className="ml-auto font-mono text-[11px] text-[var(--text-3)]">
                          {pct}
                        </span>
                      </div>
                      <Progress
                        value={pct}
                        className="h-1"
                        indicatorClassName="rounded-full"
                        indicatorStyle={{ background: "var(--c2)" }}
                      />
                    </Anim>
                  ))
                )}
              </CardContent>
            </Anim>
          </Stagger>

          {data.volume === 0 && (
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
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i} className="gap-3 rounded-[14px] p-[18px]">
            <div className="flex items-center gap-2.5">
              <Shimmer className="h-3 w-[120px]" />
              <Shimmer className="ml-auto size-[30px] rounded-full" />
            </div>
            <Shimmer className="h-7 w-[90px]" />
            <Shimmer className="h-2.5 w-[140px]" />
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="gap-3 rounded-[14px] p-4">
          <Shimmer className="h-3.5 w-[220px]" />
          <Shimmer className="h-36 w-full" />
        </Card>
        <Card className="items-center gap-3 rounded-[14px] p-4">
          <Shimmer className="h-3.5 w-[140px] self-start" />
          <Shimmer className="h-[132px] w-[230px] rounded-t-full" />
          <Shimmer className="h-8 w-[120px]" />
        </Card>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="min-h-[412px] gap-3 rounded-[14px] p-[18px]">
          <Shimmer className="h-4 w-[240px]" />
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Shimmer key={i} delay={i * 0.08} className="h-10 w-full" />
          ))}
        </Card>
        <Card className="gap-3.5 rounded-[14px] p-4">
          <Shimmer className="h-3.5 w-[160px]" />
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Shimmer key={i} delay={i * 0.08} className="h-6 w-full" />
          ))}
        </Card>
      </div>
      <div className="flex items-center justify-center gap-2.5 pt-1">
        <Spinner size={12} />
        <span className="text-xs text-[var(--text-3)]">
          Loading operations metrics…
        </span>
      </div>
    </div>
  );
}
