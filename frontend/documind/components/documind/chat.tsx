"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { InlineError } from "@/components/documind/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EASED } from "@/lib/motion";
import { Anim, AnimatePresence, Stagger, TypingDots, motion } from "@/components/motion";

/**
 * The grounded-answer surface, shared by the workspace-wide Ask page and the
 * per-document Q&A. Both pages differ only in what they retrieve — the thread,
 * streaming, citation cards and composer are identical, so they live here once.
 */

const STREAM_MS = 22;

/* -- Types --------------------------------------------------------------- */

/** A citation, flattened to what the UI needs to render and link it. */
export type Cite = {
  id: string;
  /** Primary chip text — a document name, or "page 11". */
  label: string;
  /** Trailing chip detail, e.g. "p.4". */
  badge?: string;
  /** Clause heading shown above the passage. */
  context: string;
  /** The verbatim passage the answer drew on. */
  snippet: string;
  /** Where the passage lives, shown under it. */
  meta: string;
  /** Links out of the source card. */
  actions?: ReactNode;
};

export type ChatStatus = "thinking" | "streaming" | "done" | "error" | "no-answer";

export type Msg =
  | { id: string; role: "user"; text: string; at: number; note?: string }
  | {
      id: string;
      role: "assistant";
      at: number;
      status: ChatStatus;
      text: string;
      full: string;
      thinkingLabel: string;
      citations: Cite[];
      /** Provenance line above the source chips. */
      footnote?: string;
      error?: { title: string; detail: string };
      question: string;
    };

export type AskResult = {
  text: string;
  thinking: string;
  citations: Cite[];
  footnote?: string;
} | null;

/* -- Engine -------------------------------------------------------------- */

/**
 * Owns the thread and its streaming lifecycle. `ask` is the only thing a page
 * supplies — swap it for a real streaming endpoint and the states still hold.
 */
export function useChatEngine(config: {
  ask: (question: string) => Promise<AskResult>;
  /** Copy for the grounded "I don't know" state. */
  noAnswer: () => string;
  /** Label shown while retrieving, before the backend reports its own. */
  thinkingLabel: () => string;
  /** Note attached to the user's bubble, e.g. the active scope. */
  userNote?: () => string | undefined;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const cfg = useRef(config);

  // Kept current in an effect so `send` can stay referentially stable.
  useEffect(() => {
    cfg.current = config;
  });

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
    },
    [],
  );

  const busy = messages.some(
    (m) => m.role === "assistant" && (m.status === "thinking" || m.status === "streaming"),
  );

  const patch = useCallback((id: string, updater: (m: Extract<Msg, { role: "assistant" }>) => Msg) => {
    setMessages((prev) => prev.map((m) => (m.id === id && m.role === "assistant" ? updater(m) : m)));
  }, []);

  const stream = useCallback(
    (id: string, full: string) => {
      let i = 0;
      if (timer.current) clearInterval(timer.current);
      timer.current = setInterval(() => {
        i = Math.min(full.length, i + 3);
        const done = i >= full.length;
        patch(id, (m) => ({ ...m, text: full.slice(0, i), status: done ? "done" : "streaming" }));
        if (done && timer.current) {
          clearInterval(timer.current);
          timer.current = null;
        }
      }, STREAM_MS);
    },
    [patch],
  );

  const send = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q) return;

      const answerId = `a${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: `u${Date.now()}`, role: "user", text: q, at: Date.now(), note: cfg.current.userNote?.() },
        {
          id: answerId,
          role: "assistant",
          at: Date.now(),
          status: "thinking",
          text: "",
          full: "",
          thinkingLabel: cfg.current.thinkingLabel(),
          citations: [],
          question: q,
        },
      ]);

      try {
        const answer = await cfg.current.ask(q);
        if (!answer) {
          patch(answerId, (m) => ({ ...m, status: "no-answer", text: cfg.current.noAnswer(), citations: [] }));
          return;
        }
        patch(answerId, (m) => ({
          ...m,
          status: "streaming",
          thinkingLabel: answer.thinking,
          full: answer.text,
          citations: answer.citations,
          footnote: answer.footnote,
        }));
        stream(answerId, answer.text);
      } catch (e) {
        const err = e as { title?: string; detail?: string };
        patch(answerId, (m) => ({
          ...m,
          status: "error",
          error: {
            title: err.title ?? "Answer generation failed",
            detail: err.detail ?? "The retrieval service did not respond. Retry the question.",
          },
        }));
      }
    },
    [patch, stream],
  );

  const stop = useCallback(() => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setMessages((prev) =>
      prev.map((m) =>
        m.role === "assistant" && (m.status === "streaming" || m.status === "thinking")
          ? { ...m, status: "done", text: m.text || "Generation stopped before an answer was produced." }
          : m,
      ),
    );
  }, []);

  /** Drops the failed exchange and re-asks the same question. */
  const retry = useCallback(
    (id: string) => {
      setMessages((prev) => {
        const index = prev.findIndex((m) => m.id === id);
        const msg = prev[index];
        if (!msg || msg.role !== "assistant") return prev;
        queueMicrotask(() => send(msg.question));
        return prev.filter((_, i) => i !== index && i !== index - 1);
      });
    },
    [send],
  );

  const clear = useCallback(() => {
    stop();
    setMessages([]);
  }, [stop]);

  return { messages, busy, send, stop, retry, clear };
}

/* -- Presentation -------------------------------------------------------- */

export function chipStyle(active: boolean): CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    maxWidth: "100%",
    fontSize: 11,
    fontWeight: 500,
    padding: "4px 9px",
    borderRadius: 10,
    cursor: "pointer",
    color: active ? "#fff" : "var(--accent)",
    background: active ? "var(--accent)" : "var(--accent-soft)",
    border: `1px solid ${active ? "var(--accent)" : "var(--accent-border)"}`,
  };
}

export const suggestionStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "10px 12px",
  border: "1px solid var(--border-strong)",
  borderRadius: 10,
  background: "var(--surface)",
  fontSize: 13,
  color: "var(--text)",
  cursor: "pointer",
  textAlign: "left",
};

/** Renders **bold** spans without pulling in a markdown dependency. */
export function RichText({ text }: { text: string }) {
  // While streaming the closing ** may not have arrived — hide the dangling marker.
  const safe =
    (text.match(/\*\*/g)?.length ?? 0) % 2 === 0 ? text : text.replace(/\*\*(?![\s\S]*\*\*)/, "");
  return (
    <>
      {safe.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={i} style={{ fontWeight: 600 }}>
            {part.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

/** The expanded passage behind a citation chip — the verification step. */
export function SourceCard({ cite, onClose }: { cite: Cite; onClose: () => void }) {
  return (
    <Anim
      preset="down"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        padding: "12px 14px",
        borderRadius: 10,
        background: "var(--accent-soft)",
        border: "1px solid var(--accent-border)",
        borderLeft: "3px solid var(--accent)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span
          className="mono"
          style={{
            fontSize: 9,
            fontWeight: 600,
            letterSpacing: ".08em",
            textTransform: "uppercase",
            color: "#fff",
            background: "var(--accent)",
            borderRadius: 10,
            padding: "2px 7px",
          }}
        >
          Cited passage
        </span>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)" }}>{cite.context}</span>
        <button
          onClick={onClose}
          aria-label="Collapse source"
          style={{
            marginLeft: "auto",
            flex: "none",
            fontSize: 11,
            color: "var(--text-3)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
          }}
        >
          ✕
        </button>
      </div>

      <span style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text)", textWrap: "pretty" }}>
        “{cite.snippet}”
      </span>

      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: "var(--text-3)",
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {cite.meta}
        </span>
        {cite.actions && (
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12, flex: "none" }}>
            {cite.actions}
          </div>
        )}
      </div>
    </Anim>
  );
}

/** The scrolling transcript. */
export function ChatThread({
  messages,
  openCite,
  onToggleCite,
  onRetry,
  recovery,
  inlineSources = true,
}: {
  messages: Msg[];
  openCite: string | null;
  onToggleCite: (id: string) => void;
  onRetry: (id: string) => void;
  /** Chips offered under a grounded "no answer" reply. */
  recovery?: (question: string) => ReactNode;
  /** False when a chip drives a separate reader pane rather than an inline card. */
  inlineSources?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div
      ref={ref}
      style={{
        flex: 1,
        minHeight: 0,
        overflow: "auto",
        padding: "20px clamp(14px, 2vw, 22px)",
        display: "flex",
        flexDirection: "column",
        gap: 22,
      }}
    >
      {messages.map((m) =>
        m.role === "user" ? (
          <Anim key={m.id} preset="right" style={{ display: "flex", justifyContent: "flex-end" }}>
            <div
              style={{
                maxWidth: "78%",
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
                gap: 4,
              }}
            >
              <span
                style={{
                  fontSize: 13,
                  lineHeight: 1.55,
                  color: "#fff",
                  background: "var(--accent)",
                  borderRadius: 14,
                  padding: "12px 14px",
                  textWrap: "pretty",
                }}
              >
                {m.text}
              </span>
              {m.note && (
                <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                  {m.note}
                </span>
              )}
            </div>
          </Anim>
        ) : (
          <Anim key={m.id} preset="left" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {m.status === "error" && m.error ? (
              <InlineError
                title={m.error.title}
                detail={m.error.detail}
                code="ERR_RAG_UPSTREAM"
                onRetry={() => onRetry(m.id)}
              />
            ) : (
              <>
                {m.text && (
                  <span
                    style={{
                      fontSize: 13,
                      lineHeight: 1.7,
                      color: m.status === "no-answer" ? "var(--text-2)" : "var(--text)",
                      maxWidth: 760,
                      textWrap: "pretty",
                    }}
                  >
                    <RichText text={m.text} />
                    {m.status === "streaming" && (
                      <motion.span
                        animate={{ opacity: [1, 1, 0.15, 0.15, 1] }}
                        transition={{ duration: 1.05, repeat: Infinity, times: [0, 0.42, 0.5, 0.92, 1] }}
                        style={{
                          display: "inline-block",
                          width: 6,
                          height: 13,
                          marginLeft: 2,
                          verticalAlign: "-2px",
                          background: "var(--accent)",
                        }}
                      />
                    )}
                  </span>
                )}

                {(m.status === "thinking" || m.status === "streaming") && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <TypingDots />
                    <AnimatePresence mode="wait" initial={false}>
                      <motion.span
                        key={m.thinkingLabel}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={EASED.fast}
                        style={{ fontSize: 12, color: "var(--text-3)" }}
                      >
                        {m.thinkingLabel}
                      </motion.span>
                    </AnimatePresence>
                  </div>
                )}

                {m.status === "no-answer" && recovery && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{recovery(m.question)}</div>
                )}

                {m.citations.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 760 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span className="eyebrow" style={{ flex: "none" }}>
                        Sources
                      </span>
                      {m.footnote && (
                        <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                          {m.footnote}
                        </span>
                      )}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {m.citations.map((c) => (
                        <button
                          key={c.id}
                          className="mono"
                          style={chipStyle(openCite === c.id)}
                          onClick={() => onToggleCite(c.id)}
                          title={c.meta}
                        >
                          <span
                            className="dot"
                            style={{ background: openCite === c.id ? "#fff" : "var(--accent)" }}
                          />
                          <span
                            style={{
                              minWidth: 0,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {c.label}
                          </span>
                          {c.badge && <span style={{ flex: "none", opacity: 0.75 }}>{c.badge}</span>}
                        </button>
                      ))}
                    </div>
                    {inlineSources &&
                      m.citations
                        .filter((c) => c.id === openCite)
                        .map((c) => (
                          <SourceCard key={c.id} cite={c} onClose={() => onToggleCite(c.id)} />
                        ))}
                  </div>
                )}
              </>
            )}
          </Anim>
        ),
      )}
    </div>
  );
}

/** The bottom bar: input, send/stop, and the grounding note. */
export function ChatComposer({
  value,
  onChange,
  onSubmit,
  busy,
  onStop,
  disabled,
  placeholder,
  hint,
  sendLabel = "Ask ↑",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  busy: boolean;
  onStop: () => void;
  disabled?: boolean;
  placeholder: string;
  hint: ReactNode;
  sendLabel?: string;
}) {
  const blocked = disabled || value.trim().length === 0;
  return (
    <div
      style={{
        flex: "none",
        padding: "12px clamp(14px, 2vw, 20px) 14px",
        borderTop: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: 8,
          padding: "8px 8px 8px 12px",
          border: "1px solid var(--border-strong)",
          borderRadius: 10,
          background: "var(--surface)",
        }}
      >
        <Input
          className="h-auto min-w-0 flex-1 rounded-none border-0 bg-transparent p-0 text-xs text-[var(--text)] shadow-none md:text-xs focus-visible:border-0 focus-visible:ring-0 disabled:bg-transparent dark:bg-transparent dark:disabled:bg-transparent"
          style={{ height: 30, fontSize: 13 }}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          disabled={busy || disabled}
        />
        {busy ? (
          <Button variant="outlineStrong" size="dmQuiet"
            type="button"
            onClick={onStop}
            style={{ height: 30, fontSize: 12, padding: "0 12px" }}
          >
            Stop
          </Button>
        ) : (
          <Button size="dm"
            type="submit"
            disabled={blocked}
            style={{
              height: 30,
              fontSize: 12,
              fontWeight: 500,
              padding: "0 12px",
              opacity: blocked ? 0.5 : 1,
              cursor: blocked ? "not-allowed" : "pointer",
            }}
          >
            {sendLabel}
          </Button>
        )}
      </form>
      <span style={{ fontSize: 11, color: "var(--text-3)" }}>{hint}</span>
    </div>
  );
}

/** The card the thread and composer sit in — identical on both pages. */
export function ChatPanel({ children }: { children: ReactNode }) {
  return (
    <Anim
      className="card"
      style={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {children}
    </Anim>
  );
}

/** The page wrapper — full-height column with the shell's padding. */
export function ChatPage({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        padding: "20px clamp(14px, 2vw, 24px)",
        gap: 14,
      }}
    >
      {children}
    </div>
  );
}

/** The centred hero shown before the first question. */
export function ChatEmpty({
  icon,
  title,
  body,
  suggestions,
  onPick,
}: {
  icon: ReactNode;
  title: string;
  body: string;
  suggestions: string[];
  onPick: (q: string) => void;
}) {
  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflow: "auto",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 18,
        padding: 32,
      }}
    >
      <Anim
        preset="pop"
        style={{
          width: 42,
          height: 42,
          borderRadius: 12,
          border: "1px solid var(--accent-border)",
          background: "var(--accent-soft)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {icon}
      </Anim>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6,
          maxWidth: 460,
          textAlign: "center",
        }}
      >
        <span style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>{title}</span>
        <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
          {body}
        </span>
      </div>
      <Stagger
        delay={0.12}
        style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 460 }}
      >
        {suggestions.map((q) => (
          <Anim
            as="button"
            key={q}
            className="hover-surface"
            whileHover={{ x: 3 }}
            whileTap={{ scale: 0.99 }}
            style={suggestionStyle}
            onClick={() => onPick(q)}
          >
            {q}
          </Anim>
        ))}
      </Stagger>
    </div>
  );
}
