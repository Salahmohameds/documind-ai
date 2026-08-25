"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type CSSProperties, type FormEvent } from "react";
import { signIn } from "@/lib/api";
import { DEMO_CREDENTIALS } from "@/lib/mock/data";
import { ThemeSwitch, useTheme } from "@/components/theme-provider";
import { Logo } from "@/components/shell/logo";
import { Spinner } from "@/components/documind/feedback";
import { MoonIcon, WarningIcon } from "@/components/ui/icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/**
 * A working sign-in form. `signIn()` is the only thing to swap for the real
 * auth endpoint — every state below is driven by its return value.
 */

const cardStyle: CSSProperties = {
  width: 400,
  maxWidth: "100%",
  display: "flex",
  flexDirection: "column",
  gap: 22,
  padding: 30,
  border: "1px solid var(--border)",
  borderRadius: 16,
  boxShadow: "0 8px 26px rgba(16,24,40,.06)",
  background: "var(--surface)",
};

const labelStyle: CSSProperties = { fontSize: 12, fontWeight: 500, color: "var(--text-2)" };

type Status = "idle" | "submitting" | "error" | "locked" | "success";

function isEmail(v: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
}

export function LoginCard() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [shown, setShown] = useState(false);
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});
  const [status, setStatus] = useState<Status>("idle");
  const [authError, setAuthError] = useState<{ title: string; detail: string } | null>(null);

  /** Editing after a rejection clears the banner and re-enables the button. */
  function clearAuthState() {
    setAuthError(null);
    setStatus((s) => (s === "error" || s === "locked" ? "idle" : s));
  }

  const emailError = touched.email && !isEmail(email) ? "Enter a valid email address, e.g. ops@meridian.com" : null;
  const passwordError = touched.password && password.length < 8 ? "Passwords are at least 8 characters." : null;
  const canSubmit = isEmail(email) && password.length >= 8 && status !== "submitting" && status !== "locked";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched({ email: true, password: true });
    if (!canSubmit) return;

    setStatus("submitting");
    setAuthError(null);
    const result = await signIn(email, password);

    if (result.ok) {
      setStatus("success");
      router.push("/dashboard");
      return;
    }
    setAuthError({ title: result.title, detail: result.detail });
    setStatus(result.lockedOut ? "locked" : "error");
  }

  return (
    <div
      style={{
        minHeight: "100dvh",
        background: "var(--canvas)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        padding: "48px clamp(14px, 4vw, 24px)",
      }}
    >
      <form className="anim-up" style={cardStyle} onSubmit={onSubmit} noValidate>
        {/* Brand ------------------------------------------------------- */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Logo size={34} />
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-.02em", color: "var(--text)" }}>
              DocuMind
            </span>
            <span style={{ fontSize: 11, color: "var(--text-3)" }}>Sign in to your workspace</span>
          </div>
        </div>

        {authError && (
          <div
            role="alert"
            className="anim-down"
            style={{
              display: "flex",
              gap: 10,
              padding: "10px 12px",
              border: `1px solid var(${status === "locked" ? "--warn" : "--bad"}-border)`,
              borderRadius: 10,
              background: `var(${status === "locked" ? "--warn" : "--bad"}-soft)`,
            }}
          >
            <span style={{ display: "flex", alignItems: "flex-start", paddingTop: 1 }}>
              <WarningIcon size={14} color={`var(${status === "locked" ? "--warn" : "--bad"})`} />
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span style={{ fontSize: 12, fontWeight: 500, color: `var(${status === "locked" ? "--warn" : "--bad"})` }}>
                {authError.title}
              </span>
              <span style={{ fontSize: 11, lineHeight: 1.5, color: "var(--text-2)" }}>{authError.detail}</span>
            </div>
          </div>
        )}

        {status === "success" && (
          <div
            role="status"
            className="anim-down"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 12px",
              border: "1px solid var(--ok-border)",
              borderRadius: 10,
              background: "var(--ok-soft)",
            }}
          >
            <span style={{ fontSize: 12, color: "var(--ok)" }}>✓</span>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ok)" }}>
              Signed in — opening your workspace…
            </span>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label htmlFor="email" style={labelStyle}>
              Email
            </label>
            <Input
              id="email"
              className="h-[42px] rounded-[10px] border-border bg-[var(--surface)] px-3 text-[13px] text-[var(--text)] md:text-[13px] dark:bg-[var(--surface)]"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                clearAuthState();
              }}
              onBlur={() => setTouched((t) => ({ ...t, email: true }))}
              placeholder="you@company.com"
              aria-invalid={!!emailError}
              disabled={status === "submitting" || status === "success"}
              style={emailError ? { borderColor: "var(--bad)" } : undefined}
            />
            {emailError && (
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--bad)" }}>
                <WarningIcon size={12} />
                {emailError}
              </span>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "baseline" }}>
              <label htmlFor="password" style={labelStyle}>
                Password
              </label>
              <a href="#" style={{ marginLeft: "auto", fontSize: 11 }}>
                Forgot?
              </a>
            </div>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <Input
                id="password"
                className="h-[42px] rounded-[10px] border-border bg-[var(--surface)] px-3 text-[13px] text-[var(--text)] md:text-[13px] dark:bg-[var(--surface)]"
                type={shown ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  clearAuthState();
                }}
                onBlur={() => setTouched((t) => ({ ...t, password: true }))}
                placeholder="••••••••"
                aria-invalid={!!passwordError}
                disabled={status === "submitting" || status === "success"}
                style={{ flex: 1, padding: "0 58px 0 12px", ...(passwordError ? { borderColor: "var(--bad)" } : null) }}
              />
              <button
                type="button"
                onClick={() => setShown((s) => !s)}
                style={{
                  position: "absolute",
                  right: 8,
                  fontSize: 11,
                  fontWeight: 500,
                  color: "var(--text-3)",
                  cursor: "pointer",
                  padding: "2px 4px",
                  background: "transparent",
                  border: "none",
                }}
              >
                {shown ? "Hide" : "Show"}
              </button>
            </div>
            {passwordError && (
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--bad)" }}>
                <WarningIcon size={12} />
                {passwordError}
              </span>
            )}
          </div>
        </div>

        <Button size="dm"
          type="submit"
          disabled={!canSubmit}
          style={{
            height: 44,
            fontSize: 14,
            ...(canSubmit
              ? null
              : {
                  color: "var(--text-3)",
                  background: "var(--surface-2)",
                  border: "1px solid var(--border)",
                  cursor: "not-allowed",
                }),
          }}
        >
          {status === "submitting" && <Spinner size={13} color="#fff" track="rgba(255,255,255,.4)" />}
          {status === "submitting" ? "Signing in…" : status === "locked" ? "Locked" : "Sign in"}
        </Button>

        <span style={{ fontSize: 12, color: "var(--text-3)", textAlign: "center" }}>
          No account? <Link href="/register">Create one</Link>
        </span>
      </form>

      {/* Demo credentials — remove with the mock auth. ----------------- */}
      <div
        className="card anim-up"
        style={{
          ["--i" as string]: 1,
          width: 400,
          maxWidth: "100%",
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 12px",
          borderRadius: 10,
        }}
      >
        <span className="eyebrow" style={{ flex: "none" }}>
          Demo
        </span>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-2)", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>
          {DEMO_CREDENTIALS.email} / {DEMO_CREDENTIALS.password}
        </span>
        <Button variant="outlineStrong" size="dmSm"
          type="button"
          onClick={() => {
            setEmail(DEMO_CREDENTIALS.email);
            setPassword(DEMO_CREDENTIALS.password);
            setTouched({});
            setAuthError(null);
            setStatus("idle");
          }}
          style={{ marginLeft: "auto", flex: "none" }}
        >
          Fill
        </Button>
      </div>

      <div
        onClick={toggleTheme}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          height: 32,
          padding: "0 10px",
          borderRadius: 10,
          border: "1px solid var(--border)",
          background: "var(--surface-2)",
          cursor: "pointer",
        }}
      >
        <MoonIcon size={14} color="var(--text-3)" />
        <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-2)" }}>Dark mode</span>
        <ThemeSwitch theme={theme} />
      </div>
    </div>
  );
}

export function LoginView() {
  return <LoginCard />;
}
