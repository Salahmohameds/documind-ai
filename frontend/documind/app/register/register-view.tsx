"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { resendVerification, signUp } from "@/lib/api";
import { ThemeSwitch, useTheme } from "@/components/theme-provider";
import { Logo } from "@/components/shell/logo";
import { Spinner } from "@/components/documind/feedback";
import { MoonIcon, WarningIcon } from "@/components/ui/icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/**
 * Account creation. `signUp()` is the only thing to swap for the real endpoint;
 * every state below — per-field validation, the server-side conflict, the
 * strength meter and the verification screen — is driven by its return value.
 */

const cardStyle: CSSProperties = {
  width: 440,
  maxWidth: "100%",
  display: "flex",
  flexDirection: "column",
  gap: 20,
  padding: 30,
  border: "1px solid var(--border)",
  borderRadius: 16,
  boxShadow: "0 8px 26px rgba(16,24,40,.06)",
  background: "var(--surface)",
};

const labelStyle: CSSProperties = { fontSize: 12, fontWeight: 500, color: "var(--text-2)" };

type Field = "name" | "email" | "org" | "password" | "confirm";
type Status = "idle" | "submitting" | "error" | "success";

function isEmail(v: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
}

/** 0–4, with the rule the user has yet to satisfy. */
function scorePassword(pw: string): { score: number; label: string; tone: string; next: string | null } {
  const rules: [boolean, string][] = [
    [pw.length >= 10, "at least 10 characters"],
    [/[a-z]/.test(pw) && /[A-Z]/.test(pw), "an upper and a lower case letter"],
    [/\d/.test(pw), "a number"],
    [/[^A-Za-z0-9]/.test(pw), "a symbol"],
  ];
  const score = rules.filter(([ok]) => ok).length;
  const next = rules.find(([ok]) => !ok)?.[1] ?? null;
  const label = ["Too weak", "Weak", "Fair", "Good", "Strong"][score];
  const tone = score <= 1 ? "--bad" : score <= 2 ? "--warn" : score === 3 ? "--warn" : "--ok";
  return { score, label, tone, next };
}

export function RegisterView() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const [values, setValues] = useState({ name: "", email: "", org: "", password: "", confirm: "" });
  const [touched, setTouched] = useState<Partial<Record<Field, boolean>>>({});
  const [shown, setShown] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [formError, setFormError] = useState<{ title: string; detail: string; field: Field | null } | null>(null);
  const [resend, setResend] = useState<"idle" | "sending" | "sent" | "failed">("idle");

  const strength = scorePassword(values.password);

  const set = (field: Field, value: string) => {
    setValues((v) => ({ ...v, [field]: value }));
    // Editing the field the server rejected clears that rejection.
    if (formError && (formError.field === field || formError.field === null)) setFormError(null);
    if (status === "error") setStatus("idle");
  };

  const errors: Partial<Record<Field, string>> = {
    name: values.name.trim().length < 2 ? "Enter your full name." : undefined,
    email: !isEmail(values.email) ? "Enter a valid work email, e.g. you@company.com" : undefined,
    org: values.org.trim().length < 2 ? "Give your workspace a name." : undefined,
    password: strength.score < 3 ? `Add ${strength.next} to make this password strong enough.` : undefined,
    confirm: values.confirm !== values.password ? "Both passwords must match." : undefined,
  };

  const serverError = formError?.field ? { [formError.field]: formError.title } : {};
  const shownError = (field: Field): string | undefined =>
    (serverError as Partial<Record<Field, string>>)[field] ?? (touched[field] ? errors[field] : undefined);

  const valid = Object.values(errors).every((e) => !e);
  const canSubmit = valid && accepted && status !== "submitting";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched({ name: true, email: true, org: true, password: true, confirm: true });
    if (!canSubmit) return;

    setStatus("submitting");
    setFormError(null);
    const result = await signUp({
      name: values.name,
      email: values.email,
      org: values.org,
      password: values.password,
    });

    if (result.ok) {
      setStatus("success");
      return;
    }
    setFormError({ title: result.title, detail: result.detail, field: result.field as Field | null });
    setStatus("error");
  }

  async function onResend() {
    setResend("sending");
    const r = await resendVerification(values.email);
    setResend(r.ok ? "sent" : "failed");
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
      {status === "success" ? (
        /* Verification screen ------------------------------------------- */
        <div className="anim-up" style={{ ...cardStyle, alignItems: "center", textAlign: "center", gap: 18 }}>
          <span
            className="anim-pop"
            style={{
              width: 46,
              height: 46,
              borderRadius: 14,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 19,
              color: "var(--ok)",
              background: "var(--ok-soft)",
              border: "1px solid var(--ok-border)",
            }}
          >
            ✓
          </span>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-.02em", color: "var(--text)" }}>
              Check your inbox
            </span>
            <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
              We sent a verification link to{" "}
              <span className="mono" style={{ color: "var(--text)" }}>
                {values.email}
              </span>
              . It expires in 24 hours. Your workspace{" "}
              <strong style={{ fontWeight: 600 }}>{values.org.trim()}</strong> is reserved until then.
            </span>
          </div>

          {resend === "sent" && (
            <span
              className="anim-up"
              style={{ fontSize: 12, color: "var(--ok)", background: "var(--ok-soft)", borderRadius: 10, padding: "8px 12px" }}
            >
              Sent again — it can take a minute to arrive.
            </span>
          )}
          {resend === "failed" && (
            <span
              className="anim-up"
              style={{ fontSize: 12, color: "var(--bad)", background: "var(--bad-soft)", borderRadius: 10, padding: "8px 12px" }}
            >
              We could not reach that address. Check the spelling and try again.
            </span>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Button size="dm"
              onClick={() => router.push("/dashboard")}
              style={{ padding: "0 16px" }}
            >
              Continue to workspace
            </Button>
            <Button variant="surface" size="dmQuiet"
              onClick={onResend}
              disabled={resend === "sending"}
            >
              {resend === "sending" && <Spinner size={12} color="var(--text-2)" track="var(--border)" />}
              {resend === "sending" ? "Sending…" : "Resend email"}
            </Button>
          </div>

          <button
            onClick={() => {
              setStatus("idle");
              setResend("idle");
            }}
            style={{ fontSize: 12, color: "var(--text-3)", background: "transparent", border: "none", cursor: "pointer" }}
          >
            Wrong address? Go back
          </button>
        </div>
      ) : (
        /* Form ----------------------------------------------------------- */
        <form className="anim-up" style={cardStyle} onSubmit={onSubmit} noValidate>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Logo size={34} />
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-.02em", color: "var(--text)" }}>
                Create your workspace
              </span>
              <span style={{ fontSize: 11, color: "var(--text-3)" }}>
                Free for 14 days · no card required
              </span>
            </div>
          </div>

          {formError && (
            <div
              className="anim-down"
              role="alert"
              style={{
                display: "flex",
                gap: 10,
                padding: "10px 12px",
                border: "1px solid var(--bad-border)",
                borderRadius: 10,
                background: "var(--bad-soft)",
              }}
            >
              <span style={{ display: "flex", alignItems: "flex-start", paddingTop: 1 }}>
                <WarningIcon size={14} color="var(--bad)" />
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: 12, fontWeight: 500, color: "var(--bad)" }}>{formError.title}</span>
                <span style={{ fontSize: 11, lineHeight: 1.5, color: "var(--text-2)" }}>{formError.detail}</span>
              </div>
              {formError.field === "email" && (
                <Link href="/login" style={{ marginLeft: "auto", fontSize: 11, fontWeight: 500, flex: "none" }}>
                  Sign in
                </Link>
              )}
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12 }}>
              <Field
                id="name"
                label="Full name"
                value={values.name}
                onChange={(v) => set("name", v)}
                onBlur={() => setTouched((t) => ({ ...t, name: true }))}
                error={shownError("name")}
                placeholder="Rowan Nakamura"
                autoComplete="name"
                disabled={status === "submitting"}
              />
              <Field
                id="org"
                label="Workspace"
                value={values.org}
                onChange={(v) => set("org", v)}
                onBlur={() => setTouched((t) => ({ ...t, org: true }))}
                error={shownError("org")}
                placeholder="Meridian Logistics"
                autoComplete="organization"
                disabled={status === "submitting"}
              />
            </div>

            <Field
              id="email"
              label="Work email"
              type="email"
              value={values.email}
              onChange={(v) => set("email", v)}
              onBlur={() => setTouched((t) => ({ ...t, email: true }))}
              error={shownError("email")}
              placeholder="you@company.com"
              autoComplete="email"
              disabled={status === "submitting"}
            />

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label htmlFor="password" style={labelStyle}>
                Password
              </label>
              <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                <Input
                  id="password"
                  className="h-[42px] rounded-[10px] border-border bg-[var(--surface)] px-3 text-[13px] text-[var(--text)] md:text-[13px] dark:bg-[var(--surface)]"
                  type={shown ? "text" : "password"}
                  autoComplete="new-password"
                  value={values.password}
                  onChange={(e) => set("password", e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, password: true }))}
                  placeholder="At least 10 characters"
                  aria-invalid={!!shownError("password")}
                  disabled={status === "submitting"}
                  style={{
                    flex: 1,
                    padding: "0 58px 0 12px",
                    ...(shownError("password") ? { borderColor: "var(--bad)" } : null),
                  }}
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

              {/* Strength meter — four segments that fill as rules are met. */}
              {values.password.length > 0 && (
                <div className="anim-fade" style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  <div style={{ display: "flex", gap: 4 }}>
                    {[0, 1, 2, 3].map((i) => (
                      <span
                        key={i}
                        style={{
                          flex: 1,
                          height: 3,
                          borderRadius: 999,
                          background: i < strength.score ? `var(${strength.tone})` : "var(--border)",
                          transition: "background .28s var(--ease-out)",
                        }}
                      />
                    ))}
                  </div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                    <span style={{ fontSize: 11, fontWeight: 500, color: `var(${strength.tone})` }}>
                      {strength.label}
                    </span>
                    {strength.next && (
                      <span style={{ fontSize: 11, color: "var(--text-3)" }}>Add {strength.next}</span>
                    )}
                  </div>
                </div>
              )}

              {shownError("password") && values.password.length === 0 && (
                <ErrorLine>{shownError("password")}</ErrorLine>
              )}
            </div>

            <Field
              id="confirm"
              label="Confirm password"
              type={shown ? "text" : "password"}
              value={values.confirm}
              onChange={(v) => set("confirm", v)}
              onBlur={() => setTouched((t) => ({ ...t, confirm: true }))}
              error={shownError("confirm")}
              placeholder="Re-enter your password"
              autoComplete="new-password"
              disabled={status === "submitting"}
              hint={
                values.confirm.length > 0 && values.confirm === values.password
                  ? "Passwords match"
                  : undefined
              }
            />
          </div>

          <label style={{ display: "flex", alignItems: "flex-start", gap: 9, cursor: "pointer" }}>
            <span
              onClick={() => setAccepted((a) => !a)}
              role="checkbox"
              aria-checked={accepted}
              style={{
                width: 15,
                height: 15,
                flex: "none",
                marginTop: 1,
                borderRadius: 5,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 9,
                color: "#fff",
                background: accepted ? "var(--accent)" : "transparent",
                border: `1px solid ${accepted ? "var(--accent)" : "var(--border-strong)"}`,
                transition: "background .16s ease, border-color .16s ease",
              }}
            >
              {accepted ? "✓" : ""}
            </span>
            <span style={{ fontSize: 12, lineHeight: 1.5, color: "var(--text-2)" }}>
              I agree to the <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>, including
              processing of documents uploaded to this workspace.
            </span>
          </label>

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
            {status === "submitting" ? "Creating workspace…" : "Create workspace"}
          </Button>

          {!accepted && valid && (
            <span className="anim-fade" style={{ fontSize: 11, color: "var(--text-3)", textAlign: "center" }}>
              Accept the terms to continue.
            </span>
          )}

          <span style={{ fontSize: 12, color: "var(--text-3)", textAlign: "center" }}>
            Already have an account? <Link href="/login">Sign in</Link>
          </span>
        </form>
      )}

      <div
        onClick={toggleTheme}
        className="anim-fade"
        style={{
          ["--i" as string]: 2,
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

function ErrorLine({ children }: { children: ReactNode }) {
  return (
    <span
      className="anim-down"
      style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--bad)" }}
    >
      <WarningIcon size={12} />
      {children}
    </span>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  onBlur,
  error,
  hint,
  type = "text",
  placeholder,
  autoComplete,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  onBlur: () => void;
  error?: string;
  hint?: string;
  type?: string;
  placeholder?: string;
  autoComplete?: string;
  disabled?: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
      <label htmlFor={id} style={labelStyle}>
        {label}
      </label>
      <Input
        id={id}
        className="h-[42px] rounded-[10px] border-border bg-[var(--surface)] px-3 text-[13px] text-[var(--text)] md:text-[13px] dark:bg-[var(--surface)]"
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        autoComplete={autoComplete}
        aria-invalid={!!error}
        disabled={disabled}
        style={{ minWidth: 0, ...(error ? { borderColor: "var(--bad)" } : null) }}
      />
      {error && <ErrorLine>{error}</ErrorLine>}
      {!error && hint && (
        <span className="anim-fade" style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--ok)" }}>
          ✓ {hint}
        </span>
      )}
    </div>
  );
}
