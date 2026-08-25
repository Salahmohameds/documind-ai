import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { STATUS, riskTone, tonedPill, v, type DocStatus, type Tone } from "@/lib/design";

/**
 * The canvas's three recurring pills, on top of shadcn's Badge. Tone colours
 * come from `tonedPill()` rather than a variant because the tone is data-driven
 * (a risk score or a pipeline status), not a design-time choice.
 */

export function TypeBadge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <Badge variant="neutral" className={className}>
      {children}
    </Badge>
  );
}

export function StatusBadge({
  status,
  className,
  label,
}: {
  status: DocStatus;
  className?: string;
  /** Overrides the status's own label — used for the dashboard's verdict column. */
  label?: string;
}) {
  const { tone, label: defaultLabel } = STATUS[status];
  return (
    <Badge variant="pill" className={cn("gap-1.5", className)} style={tonedPill(tone)}>
      <span className="size-[5px] flex-none rounded-full" style={{ background: v(tone) }} />
      {label ?? defaultLabel}
    </Badge>
  );
}

export function RiskBadge({
  score,
  tone,
  className,
  children,
}: {
  score?: number;
  /** Explicit tone wins — queued rows show a dash in the idle tone. */
  tone?: Tone;
  className?: string;
  children?: React.ReactNode;
}) {
  const resolved = tone ?? riskTone(score ?? 0);
  return (
    <Badge
      variant="pill"
      className={cn("px-3 font-mono text-xs", className)}
      style={tonedPill(resolved)}
    >
      {children ?? score}
    </Badge>
  );
}
