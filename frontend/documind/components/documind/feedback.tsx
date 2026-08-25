"use client";

import { useCallback, useState, type CSSProperties, type ReactNode } from "react";
import type { Tone } from "@/lib/design";
import { Button } from "@/components/ui/button";

/**
 * The shared state surfaces — spinner, empty, error, toast, confirm. Every
 * screen renders its non-happy states through these so the visual language
 * stays identical across pages.
 */

/* -- Spinner ------------------------------------------------------------ */

export function Spinner({
  size = 16,
  color = "var(--accent)",
  track = "var(--accent-border)",
}: {
  size?: number;
  color?: string;
  track?: string;
}) {
  return (
    <span
      style={{
        width: size,
        height: size,
        flex: "none",
        borderRadius: "50%",
        border: `${Math.max(1.5, size / 9)}px solid ${track}`,
        borderTopColor: color,
        animation: "spin .8s linear infinite",
        display: "inline-block",
      }}
    />
  );
}

/* -- Empty / error panels ----------------------------------------------- */

const panelStyle: CSSProperties = {
  flex: "1 0 auto",
  minHeight: 380,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: 18,
  padding: 40,
  textAlign: "center",
};

export function EmptyPanel({
  glyph = "↑",
  title,
  body,
  actions,
  footnote,
  tone = "--idle",
  compact,
}: {
  glyph?: ReactNode;
  title: string;
  body: string;
  actions?: ReactNode;
  footnote?: ReactNode;
  tone?: Tone;
  compact?: boolean;
}) {
  return (
    <div className="card anim-up" style={{ ...panelStyle, minHeight: compact ? 220 : 380 }}>
      <div
        className="anim-pop"
        style={{
          width: 44,
          height: 44,
          borderRadius: 10,
          border: `1px dashed ${tone === "--idle" ? "var(--border-strong)" : `var(${tone}-border)`}`,
          background: tone === "--idle" ? "transparent" : `var(${tone}-soft)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: tone === "--idle" ? "var(--s400)" : `var(${tone})`,
          fontSize: 16,
        }}
      >
        {glyph}
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, maxWidth: 460 }}>
        <span style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>{title}</span>
        <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>{body}</span>
      </div>
      {actions && <div style={{ display: "flex", alignItems: "center", gap: 8 }}>{actions}</div>}
      {footnote && (
        <div style={{ display: "flex", alignItems: "center", gap: 16, paddingTop: 4 }}>{footnote}</div>
      )}
    </div>
  );
}

export function ErrorPanel({
  title,
  detail,
  code,
  onRetry,
  retrying,
  actions,
  compact,
}: {
  title: string;
  detail: string;
  code?: string;
  onRetry?: () => void;
  retrying?: boolean;
  actions?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div
      className="anim-up"
      style={{
        ...panelStyle,
        minHeight: compact ? 200 : 380,
        background: "var(--surface)",
        border: "1px solid var(--bad-border)",
        borderRadius: 14,
        boxShadow: "0 1px 2px rgb(16 24 40 / 5%)",
      }}
      role="alert"
    >
      <div
        className="anim-pop"
        style={{
          width: 44,
          height: 44,
          borderRadius: 10,
          border: "1px solid var(--bad-border)",
          background: "var(--bad-soft)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--bad)",
          fontSize: 17,
        }}
      >
        ✕
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, maxWidth: 480 }}>
        <span style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>{title}</span>
        <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>{detail}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {onRetry && (
          <Button size="dm" onClick={onRetry} disabled={retrying} style={{ padding: "0 16px" }}>
            {retrying && <Spinner size={13} color="#fff" track="rgba(255,255,255,.4)" />}
            {retrying ? "Retrying…" : "Try again"}
          </Button>
        )}
        {actions}
      </div>
      {code && (
        <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
          {code}
        </span>
      )}
    </div>
  );
}

/** The compact inline variant — used inside a card that partly loaded. */
export function InlineError({
  title,
  detail,
  code,
  onRetry,
  tone = "--bad",
}: {
  title: string;
  detail: string;
  code?: string;
  onRetry?: () => void;
  tone?: Tone;
}) {
  return (
    <div
      className="anim-down"
      style={{
        display: "flex",
        gap: 10,
        padding: "10px 12px",
        border: `1px solid var(${tone}-border)`,
        borderRadius: 10,
        background: `var(${tone}-soft)`,
      }}
      role="alert"
    >
      <span style={{ fontSize: 11, color: `var(${tone})`, lineHeight: 1.5, flex: "none" }}>
        {tone === "--bad" ? "✕" : "!"}
      </span>
      <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: `var(${tone})` }}>{title}</span>
        <span style={{ fontSize: 12, lineHeight: 1.5, color: "var(--text-2)", textWrap: "pretty" }}>{detail}</span>
        {code && (
          <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
            {code}
          </span>
        )}
      </div>
      {onRetry && (
        <Button variant="outlineStrong" size="dmSm" onClick={onRetry} style={{ marginLeft: "auto", flex: "none" }}>
          Retry
        </Button>
      )}
    </div>
  );
}

/* -- Toasts ------------------------------------------------------------- */

export type Toast = {
  id: number;
  tone: Tone;
  glyph: string;
  title: string;
  body: string;
  action?: { label: string; onClick: () => void };
  /** Shows a spinner instead of the glyph. */
  pending?: boolean;
};

let toastId = 0;

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  const push = useCallback(
    (toast: Omit<Toast, "id">, ttl = 5200) => {
      const id = ++toastId;
      setToasts((t) => [...t, { ...toast, id }]);
      if (ttl > 0) setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), ttl);
      return id;
    },
    [],
  );

  const update = useCallback((id: number, patch: Partial<Toast>, ttl = 4200) => {
    setToasts((t) => t.map((x) => (x.id === id ? { ...x, ...patch } : x)));
    if (ttl > 0) setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), ttl);
  }, []);

  return { toasts, push, update, dismiss };
}

export function Toaster({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div
      style={{
        position: "fixed",
        right: 20,
        bottom: 72,
        zIndex: 40,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        width: 340,
      }}
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className="anim-slide"
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
            padding: "11px 12px",
            border: "1px solid var(--border)",
            borderRadius: 10,
            background: "var(--surface)",
            borderLeft: `3px solid var(${t.tone})`,
            boxShadow: "0 10px 28px rgb(11 18 32 / 14%)",
          }}
        >
          <span style={{ fontSize: 11, color: `var(${t.tone})`, lineHeight: 1.4, flex: "none", paddingTop: 1 }}>
            {t.pending ? <Spinner size={11} color={`var(${t.tone})`} track={`var(${t.tone}-border)`} /> : t.glyph}
          </span>
          <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{t.title}</span>
            <span style={{ fontSize: 11, lineHeight: 1.5, color: "var(--text-2)", textWrap: "pretty" }}>{t.body}</span>
          </div>
          {t.action && (
            <button
              onClick={t.action.onClick}
              style={{
                marginLeft: "auto",
                fontSize: 11,
                fontWeight: 500,
                flex: "none",
                color: "var(--accent)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
              }}
            >
              {t.action.label}
            </button>
          )}
          <button
            onClick={() => onDismiss(t.id)}
            aria-label="Dismiss"
            style={{
              marginLeft: t.action ? undefined : "auto",
              fontSize: 11,
              color: "var(--text-3)",
              cursor: "pointer",
              flex: "none",
              background: "transparent",
              border: "none",
            }}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}

/* -- Confirm dialog ----------------------------------------------------- */

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  danger,
  pending,
  onConfirm,
  onCancel,
  children,
}: {
  open: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  danger?: boolean;
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: ReactNode;
}) {
  if (!open) return null;
  return (
    <div
      className="anim-fade"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        background: "rgb(11 18 32 / 42%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
      onClick={pending ? undefined : onCancel}
    >
      <div
        role="alertdialog"
        aria-modal
        className="anim-up"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 440,
          maxWidth: "100%",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          padding: 22,
          borderRadius: 16,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          boxShadow: "0 18px 48px rgb(11 18 32 / 24%)",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <span
            style={{
              width: 34,
              height: 34,
              flex: "none",
              borderRadius: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              color: danger ? "var(--bad)" : "var(--accent)",
              background: danger ? "var(--bad-soft)" : "var(--accent-soft)",
              border: `1px solid var(${danger ? "--bad" : "--accent"}-border)`,
            }}
          >
            {danger ? "!" : "?"}
          </span>
          <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 0 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>{title}</span>
            <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>{body}</span>
          </div>
        </div>

        {children}

        <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
          <Button variant="outlineStrong" size="dmQuiet" onClick={onCancel} disabled={pending} style={{ height: 34 }}>
            Cancel
          </Button>
          <Button
            variant={danger ? "destructiveSolid" : "default"}
            size="dm"
            onClick={onConfirm}
            disabled={pending}
            style={{ height: 34, padding: "0 14px" }}
          >
            {pending && <Spinner size={12} color="#fff" track="rgba(255,255,255,.4)" />}
            {pending ? "Working…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

/* -- Demo state switcher ------------------------------------------------ */

function switchTabStyle(active: boolean): CSSProperties {
  return {
    padding: "5px 10px",
    borderRadius: 10,
    fontSize: 11,
    fontWeight: 500,
    cursor: "pointer",
    background: active ? "var(--surface-2)" : "transparent",
    color: active ? "var(--text)" : "var(--text-3)",
    border: `1px solid ${active ? "var(--border)" : "transparent"}`,
  };
}

/**
 * Lets a reviewer walk every state of a page without a backend. It reads and
 * writes only the page's `simulate` flag, so deleting this component (and the
 * `simulate` option in `lib/api.ts`) removes the whole demo affordance.
 */
export function StateSwitcher<T extends string>({
  label = "State",
  value,
  options,
  onChange,
  floating = true,
}: {
  label?: string;
  value: T;
  options: readonly { value: T; label: string }[];
  onChange: (v: T) => void;
  floating?: boolean;
}) {
  return (
    <div
      className={floating ? "anim-up" : undefined}
      style={{
        ...(floating
          ? ({ position: "fixed", right: 20, bottom: 20, zIndex: 50 } as CSSProperties)
          : {}),
        display: "flex",
        alignItems: "center",
        gap: 2,
        padding: 3,
        border: "1px solid var(--border)",
        borderRadius: 10,
        background: "var(--surface)",
        boxShadow: floating ? "0 8px 22px rgb(11 18 32 / 12%)" : undefined,
      }}
    >
      <span
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: ".07em",
          textTransform: "uppercase",
          color: "var(--text-3)",
          padding: "0 8px",
        }}
      >
        {label}
      </span>
      {options.map((o) => (
        <span key={o.value} style={switchTabStyle(value === o.value)} onClick={() => onChange(o.value)}>
          {o.label}
        </span>
      ))}
    </div>
  );
}
