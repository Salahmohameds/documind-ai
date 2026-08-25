"use client";

import { useState, type CSSProperties, type ReactNode } from "react";
import { RISK_CATEGORIES } from "@/lib/data";
import { STATUS, confidenceTone, riskTone, tonedPill, v } from "@/lib/design";
import { ThemeSwitch, useTheme } from "@/components/theme-provider";
import { MoonIcon, SearchIcon } from "@/components/ui/icons";
import type { DocStatus } from "@/lib/design";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/* -- Sheet fixtures ------------------------------------------------------ */

const SKELETON_WIDTHS = [58, 44, 66, 39, 52];

const MOBILE_DOCS: {
  name: string;
  id: string;
  type: string;
  status: DocStatus;
  risk: number;
  pages: number;
  time: string;
}[] = [
  { name: "ACME_Q3_MSA_countersigned.pdf", id: "doc_8f2a41c9", type: "Contract", status: "completed", risk: 18, pages: 42, time: "2m ago" },
  { name: "INV-2026-04417_Northwind.pdf", id: "doc_b1c7d02e", type: "Invoice", status: "processing", risk: 52, pages: 3, time: "14m ago" },
  { name: "INV-2026-04416_Halcyon.pdf", id: "doc_c34d88a7", type: "Invoice", status: "failed", risk: 81, pages: 5, time: "38m ago" },
  { name: "Global_MSA_Amendment_2.pdf", id: "doc_71e0b5cc", type: "Contract", status: "completed", risk: 64, pages: 28, time: "1h ago" },
];

const MOBILE_FIELDS: [string, string, number][] = [
  ["Parties", "Meridian Logistics LLC · Acme Freight Holdings Inc.", 97],
  ["Start date", "2026-09-01", 99],
  ["Payment terms", "Net 45 from invoice receipt", 91],
  ["Total value", "4,820,000.00 USD", 96],
];

/* -- Shared bits --------------------------------------------------------- */

const caption: CSSProperties = {
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: ".06em",
  textTransform: "uppercase",
  color: "var(--text-3)",
};

const centeredCard: CSSProperties = {
  minHeight: 212,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: 14,
  padding: 24,
  textAlign: "center",
};

const phoneFrame: CSSProperties = {
  width: 375,
  height: 720,
  background: "var(--canvas)",
  border: "1px solid var(--border)",
  borderRadius: 14,
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
};

function Panel({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <span className="mono" style={caption}>
        {label}
      </span>
      {children}
    </div>
  );
}

function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span
        className="mono"
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: ".08em",
          textTransform: "uppercase",
          color: "var(--text-2)",
        }}
      >
        {children}
      </span>
      <span style={{ flex: 1, height: 1, background: "var(--border)" }} />
    </div>
  );
}

function mobileTabStyle(active: boolean): CSSProperties {
  return {
    height: 38,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 13,
    fontWeight: active ? 600 : 400,
    cursor: "pointer",
    color: active ? "var(--accent)" : "var(--text-3)",
    borderBottom: `2px solid ${active ? "var(--accent)" : "transparent"}`,
  };
}

/* -- Sheet --------------------------------------------------------------- */

export function StatesView() {
  const { theme, toggleTheme } = useTheme();
  const [tab, setTab] = useState<"chat" | "source">("chat");

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--canvas)",
        padding: "32px 32px 64px",
        display: "flex",
        flexDirection: "column",
        gap: 32,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-end", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-.02em", color: "var(--text)" }}>
            States &amp; responsive sheet
          </span>
          <span style={{ fontSize: 12, color: "var(--text-3)" }}>
            DocuMind AI · shared component states and 375px layouts
          </span>
        </div>
        <div
          onClick={toggleTheme}
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 8,
            height: 32,
            padding: "0 10px",
            borderRadius: 10,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            cursor: "pointer",
          }}
        >
          <MoonIcon size={14} color="var(--text-3)" />
          <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-2)" }}>Dark mode</span>
          <ThemeSwitch theme={theme} />
        </div>
      </div>

      {/* Part A --------------------------------------------------------- */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <SectionHeading>Part A — shared states</SectionHeading>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 16, alignItems: "start" }}>
          {/* A1 */}
          <Panel label="A1 · Table loading skeleton">
            <div className="card" style={{ overflow: "hidden" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(0,1fr) 84px 64px",
                  gap: 12,
                  padding: "0 14px",
                  height: 30,
                  alignItems: "center",
                  background: "var(--surface-2)",
                  borderBottom: "1px solid var(--border)",
                }}
              >
                {["Filename", "Status", "Risk"].map((h, i) => (
                  <span
                    key={h}
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      letterSpacing: ".07em",
                      textTransform: "uppercase",
                      color: "var(--text-3)",
                      textAlign: i === 2 ? "right" : "left",
                    }}
                  >
                    {h}
                  </span>
                ))}
              </div>
              {SKELETON_WIDTHS.map((w, i) => (
                <div
                  key={i}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0,1fr) 84px 64px",
                    gap: 12,
                    padding: "0 14px",
                    height: 42,
                    alignItems: "center",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span className="skeleton" style={{ width: 20, height: 20, flex: "none" }} />
                    <span className="skeleton" style={{ width: `${w}%`, height: 11 }} />
                  </div>
                  <span className="skeleton" style={{ width: 66, height: 14 }} />
                  <span className="skeleton" style={{ justifySelf: "end", width: 34, height: 14 }} />
                </div>
              ))}
            </div>
          </Panel>

          {/* A2 */}
          <Panel label="A2 · Card loading skeleton">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[
                [64, 52, 78],
                [58, 44, 70],
              ].map((widths, i) => (
                <div
                  key={i}
                  className="card"
                  style={{ padding: 14, display: "flex", flexDirection: "column", gap: 12 }}
                >
                  <span className="skeleton" style={{ width: `${widths[0]}%`, height: 10 }} />
                  <span className="skeleton" style={{ width: `${widths[1]}%`, height: 24 }} />
                  <span className="skeleton" style={{ width: `${widths[2]}%`, height: 9 }} />
                </div>
              ))}
              <div
                className="card"
                style={{ gridColumn: "span 2", padding: 14, display: "flex", alignItems: "center", gap: 16 }}
              >
                <span
                  className="skeleton"
                  style={{ width: 76, height: 76, borderRadius: "50%", flex: "none" }}
                />
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                  {[80, 62, 71].map((w) => (
                    <span key={w} className="skeleton" style={{ width: `${w}%`, height: 9 }} />
                  ))}
                </div>
              </div>
            </div>
          </Panel>

          {/* A3 */}
          <Panel label="A3 · Empty — no documents yet">
            <div className="card" style={centeredCard}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  border: "1px dashed var(--border-strong)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--s400)",
                  fontSize: 15,
                }}
              >
                ↑
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 280 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
                  No documents yet
                </span>
                <span style={{ fontSize: 12, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
                  Upload invoices or contracts to start classification, extraction and risk scoring.
                </span>
              </div>
              <Button size="dm" style={{ padding: "0 16px" }}>
                Upload documents
              </Button>
              <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                PDF · max 200 MB
              </span>
            </div>
          </Panel>

          {/* A4 */}
          <Panel label="A4 · Empty — no search results">
            <div className="card" style={centeredCard}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  border: "1px solid var(--border)",
                  background: "var(--surface-2)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <SearchIcon size={18} color="var(--text-3)" />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 300 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
                  No results for “net 15 termination”
                </span>
                <span style={{ fontSize: 12, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
                  No documents matched this query with the current filters.
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Button variant="outlineStrong" size="dmQuiet" style={{ height: 30, padding: "0 12px" }}>
                  Clear filters
                </Button>
                <Button variant="ghost" size="dm"
                  style={{
                    height: 30,
                    padding: "0 12px",
                    fontSize: 12,
                    fontWeight: 500,
                    color: "var(--accent)",
                    background: "var(--accent-soft)",
                    border: "1px solid var(--accent-border)",
                  }}
                >
                  Search all documents
                </Button>
              </div>
            </div>
          </Panel>

          {/* A5 */}
          <Panel label="A5 · Inline error + retry">
            <div className="card" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>Status breakdown</span>
              <div
                style={{
                  display: "flex",
                  gap: 10,
                  padding: 12,
                  border: "1px solid var(--bad-border)",
                  borderRadius: 14,
                  background: "var(--bad-soft)",
                }}
              >
                <span style={{ fontSize: 11, color: "var(--bad)", lineHeight: 1.5, flex: "none" }}>✕</span>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "var(--bad)" }}>
                    Couldn’t load status metrics
                  </span>
                  <span style={{ fontSize: 12, lineHeight: 1.5, color: "var(--text-2)", textWrap: "pretty" }}>
                    The metrics service timed out after 10s. Other panels are unaffected.
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                    ERR_UPSTREAM_TIMEOUT · req_9a41ce
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, paddingTop: 2 }}>
                    <Button size="dmSm">Retry</Button>
                    <Button variant="outlineStrong" size="dmSm" style={{ padding: "0 10px" }}>
                      Details
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          {/* A6 */}
          <Panel label="A6 · Full-page error (500)">
            <div className="card" style={centeredCard}>
              <span
                className="mono"
                style={{ fontSize: 34, fontWeight: 600, letterSpacing: "-.03em", color: "var(--bad)", lineHeight: 1 }}
              >
                500
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 300 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
                  Something went wrong on our side
                </span>
                <span style={{ fontSize: 12, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
                  Your documents are safe. The processing pipeline is unaffected — only this page failed to
                  render.
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Button size="dm" style={{ padding: "0 16px" }}>
                  Reload page
                </Button>
                <a href="#" style={{ fontSize: 12, fontWeight: 500 }}>
                  Status page →
                </a>
              </div>
              <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                trace 4f8e21c9 · 14:22 UTC
              </span>
            </div>
          </Panel>

          {/* A7 */}
          <Panel label="A7 · 404">
            <div className="card" style={centeredCard}>
              <span
                className="mono"
                style={{ fontSize: 34, fontWeight: 600, letterSpacing: "-.03em", color: "var(--text-3)", lineHeight: 1 }}
              >
                404
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 300 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
                  Document not found
                </span>
                <span style={{ fontSize: 12, lineHeight: 1.6, color: "var(--text-2)", textWrap: "pretty" }}>
                  It may have been deleted, or you may not have access to this workspace.
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Button size="dm" style={{ padding: "0 16px" }}>
                  Back to documents
                </Button>
                <a href="#" style={{ fontSize: 12, fontWeight: 500 }}>
                  Request access
                </a>
              </div>
            </div>
          </Panel>

          {/* A8 */}
          <Panel label="A8 · Toasts — success / error / info">
            <div
              style={{
                minHeight: 212,
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: 14,
                padding: 14,
                display: "flex",
                flexDirection: "column",
                gap: 10,
                justifyContent: "center",
              }}
            >
              <Toast tone="--ok" glyph="✓" title="3 documents processed" body="Fields extracted and indexed." action="View" />
              <Toast tone="--bad" glyph="✕" title="Extraction failed — 1 file" body="Vendor_NDA_Kestrel_v4.pdf has no text layer." action="Retry" rounded />
              <Toast tone="--accent" glyph="i" title="Reprocessing queued" body="42 documents will re-run overnight." rounded neutralBorder />
            </div>
          </Panel>

          {/* A9 */}
          <Panel label="A9 · Confirm dialog — delete document">
            <div
              style={{
                minHeight: 212,
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "var(--s900)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 20,
              }}
            >
              <div
                className="card"
                style={{
                  width: "100%",
                  maxWidth: 340,
                  padding: 18,
                  display: "flex",
                  flexDirection: "column",
                  gap: 14,
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <span
                    style={{
                      width: 26,
                      height: 26,
                      flex: "none",
                      borderRadius: 10,
                      background: "var(--bad-soft)",
                      border: "1px solid var(--bad-border)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 11,
                      color: "var(--bad)",
                    }}
                  >
                    !
                  </span>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
                      Delete this document?
                    </span>
                    <span style={{ fontSize: 12, lineHeight: 1.55, color: "var(--text-2)", textWrap: "pretty" }}>
                      Global_MSA_Amendment_2.pdf, its extracted fields, PII findings and risk score will be
                      permanently removed. This cannot be undone.
                    </span>
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "9px 10px",
                    borderRadius: 10,
                    background: "var(--surface-2)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <span
                    style={{
                      width: 13,
                      height: 13,
                      borderRadius: 4,
                      border: "1px solid var(--border-strong)",
                      flex: "none",
                    }}
                  />
                  <span style={{ fontSize: 11, color: "var(--text-2)" }}>
                    Also delete the original file from Object Storage
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
                  <Button variant="surface" size="dmQuiet" style={{ borderRadius: 14 }}>
                    Cancel
                  </Button>
                  <Button variant="ghost" size="dm"
                    style={{
                      height: 32,
                      fontWeight: 500,
                      color: "#fff",
                      background: "var(--bad)",
                      border: "1px solid var(--bad)",
                    }}
                  >
                    Delete document
                  </Button>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      {/* Part B --------------------------------------------------------- */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <SectionHeading>Part B — responsive at 375px</SectionHeading>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start" }}>
          {/* B1 */}
          <Panel label="B1 · Documents list — stacked cards, filters behind a button, bottom nav">
            <div style={phoneFrame}>
              <div
                style={{
                  flex: "none",
                  padding: "12px 14px",
                  background: "var(--surface)",
                  borderBottom: "1px solid var(--border)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span
                    style={{
                      width: 44,
                      height: 44,
                      margin: -8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 15,
                      color: "var(--text-2)",
                      cursor: "pointer",
                    }}
                  >
                    ☰
                  </span>
                  <span style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>Documents</span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
                    12.8k
                  </span>
                  <span
                    style={{
                      marginLeft: "auto",
                      width: 44,
                      height: 44,
                      marginRight: -10,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      cursor: "pointer",
                    }}
                  >
                    <SearchIcon size={17} color="var(--text-2)" />
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Button variant="ghost" size="dm"
                    style={{
                      flex: 1,
                      fontWeight: 500,
                      color: "var(--accent)",
                      background: "var(--accent-soft)",
                      border: "1px solid var(--accent-border)",
                    }}
                  >
                    Filters · 2
                  </Button>
                  <Button variant="outlineStrong" size="dmQuiet" style={{ flex: 1, height: 36, fontSize: 13 }}>
                    Sort · Newest
                  </Button>
                </div>
              </div>

              <div
                style={{
                  flex: 1,
                  minHeight: 0,
                  overflow: "auto",
                  padding: 12,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
              >
                {MOBILE_DOCS.map((m) => {
                  const st = STATUS[m.status];
                  const rt = riskTone(m.risk);
                  return (
                    <div
                      key={m.id}
                      className="card"
                      style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}
                    >
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                        <span
                          className="mono"
                          style={{
                            width: 26,
                            height: 26,
                            flex: "none",
                            borderRadius: 10,
                            border: "1px solid var(--border)",
                            background: "var(--surface-2)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 8,
                            fontWeight: 600,
                            color: "var(--text-3)",
                          }}
                        >
                          PDF
                        </span>
                        <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
                          <span
                            style={{
                              fontSize: 13,
                              fontWeight: 500,
                              color: "var(--text)",
                              lineHeight: 1.35,
                              textWrap: "pretty",
                            }}
                          >
                            {m.name}
                          </span>
                          <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                            {m.id} · {m.pages} pages
                          </span>
                        </div>
                        <span
                          style={{
                            marginLeft: "auto",
                            width: 32,
                            height: 32,
                            margin: "-4px -6px 0 0",
                            flex: "none",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 14,
                            color: "var(--text-3)",
                            cursor: "pointer",
                          }}
                        >
                          ⋯
                        </span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                        <span className="pill pill-neutral">{m.type}</span>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 5,
                            fontSize: 11,
                            fontWeight: 500,
                            padding: "2px 8px",
                            borderRadius: 10,
                            ...tonedPill(st.tone),
                          }}
                        >
                          <span className="dot" style={{ background: v(st.tone) }} />
                          {st.label}
                        </span>
                        <span
                          className="mono"
                          style={{
                            fontSize: 11,
                            fontWeight: 500,
                            padding: "2px 8px",
                            borderRadius: 10,
                            ...tonedPill(rt),
                          }}
                        >
                          Risk {m.risk}
                        </span>
                        <span
                          className="mono"
                          style={{ marginLeft: "auto", fontSize: 10, color: "var(--text-3)" }}
                        >
                          {m.time}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div
                style={{
                  flex: "none",
                  height: 60,
                  background: "var(--surface)",
                  borderTop: "1px solid var(--border)",
                  display: "grid",
                  gridTemplateColumns: "repeat(5,1fr)",
                  alignItems: "center",
                }}
              >
                {[
                  ["Dashboard", false],
                  ["Upload", false],
                  ["Docs", true],
                  ["Search", false],
                  ["Jobs", false],
                ].map(([label, active]) => (
                  <div
                    key={label as string}
                    style={{
                      height: 60,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 4,
                      cursor: "pointer",
                    }}
                  >
                    <span
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: 4,
                        border: `1.5px solid ${active ? "var(--accent)" : "var(--s400)"}`,
                      }}
                    />
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: active ? 500 : 400,
                        color: active ? "var(--accent)" : "var(--text-3)",
                      }}
                    >
                      {label as string}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          {/* B2 */}
          <Panel label="B2 · Document detail — stacked, risk first">
            <div style={phoneFrame}>
              <div
                style={{
                  flex: "none",
                  padding: "12px 14px",
                  background: "var(--surface)",
                  borderBottom: "1px solid var(--border)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      width: 44,
                      height: 44,
                      margin: -8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 15,
                      color: "var(--text-2)",
                      cursor: "pointer",
                    }}
                  >
                    ←
                  </span>
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--text)",
                      minWidth: 0,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Global_MSA_Amendment_2.pdf
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span className="pill pill-neutral">Contract</span>
                  <span className="pill" style={{ gap: 5, ...tonedPill("--ok") }}>
                    <span className="dot" style={{ background: "var(--ok)" }} />
                    Completed
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                    28 pages
                  </span>
                </div>
              </div>

              <div
                style={{
                  flex: 1,
                  minHeight: 0,
                  overflow: "auto",
                  padding: 12,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--bad-border)",
                    borderRadius: 14,
                    overflow: "hidden",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", padding: "10px 14px", background: "var(--bad)" }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#fff" }}>Risk Analysis</span>
                    <span style={{ marginLeft: "auto", fontSize: 10, color: "#fff", opacity: 0.85 }}>
                      2m ago
                    </span>
                  </div>
                  <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                      <div
                        style={{
                          position: "relative",
                          width: 104,
                          height: 104,
                          flex: "none",
                          borderRadius: "50%",
                          background:
                            "conic-gradient(var(--bad) 0deg 259.2deg, var(--border) 259.2deg 360deg)",
                        }}
                      >
                        <div
                          style={{
                            position: "absolute",
                            inset: 12,
                            borderRadius: "50%",
                            background: "var(--surface)",
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <span
                            className="mono"
                            style={{
                              fontSize: 30,
                              fontWeight: 600,
                              letterSpacing: "-.03em",
                              lineHeight: 1,
                              color: "var(--bad)",
                            }}
                          >
                            72
                          </span>
                          <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>
                            / 100
                          </span>
                        </div>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
                        <span
                          style={{
                            alignSelf: "flex-start",
                            fontSize: 11,
                            fontWeight: 600,
                            letterSpacing: ".04em",
                            textTransform: "uppercase",
                            borderRadius: 999,
                            padding: "4px 10px",
                            ...tonedPill("--bad"),
                          }}
                        >
                          High risk
                        </span>
                        <span style={{ fontSize: 11, lineHeight: 1.5, color: "var(--text-2)", textWrap: "pretty" }}>
                          Legal sign-off required. 3 findings driving score.
                        </span>
                      </div>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {RISK_CATEGORIES.map(([name, sc, level, cv]) => (
                        <div key={name} style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)" }}>{name}</span>
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 600,
                                letterSpacing: ".04em",
                                textTransform: "uppercase",
                                borderRadius: 10,
                                padding: "1px 6px",
                                ...tonedPill(cv),
                              }}
                            >
                              {level}
                            </span>
                            <span
                              className="mono"
                              style={{ marginLeft: "auto", fontSize: 11, color: "var(--text)" }}
                            >
                              {sc}
                            </span>
                          </div>
                          <div style={{ height: 6, borderRadius: 10, background: "var(--border)", overflow: "hidden" }}>
                            <div
                              style={{ width: `${sc}%`, height: "100%", borderRadius: 10, background: `var(${cv})` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="card" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>Classification</span>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                    <span className="mono" style={{ fontSize: 18, fontWeight: 600, color: "var(--text)" }}>
                      CONTRACT
                    </span>
                    <span
                      className="mono"
                      style={{ marginLeft: "auto", fontSize: 11, fontWeight: 500, color: "var(--ok)" }}
                    >
                      98.2%
                    </span>
                  </div>
                  <div style={{ height: 5, borderRadius: 10, background: "var(--border)", overflow: "hidden" }}>
                    <div style={{ width: "98.2%", height: "100%", background: "var(--ok)" }} />
                  </div>
                </div>

                <div className="card" style={{ overflow: "hidden" }}>
                  <span
                    style={{
                      display: "block",
                      padding: "14px 14px 10px",
                      fontSize: 12,
                      fontWeight: 600,
                      color: "var(--text)",
                    }}
                  >
                    Extracted fields
                  </span>
                  {MOBILE_FIELDS.map(([key, value, conf]) => (
                    <div
                      key={key}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 3,
                        padding: "10px 14px",
                        borderTop: "1px solid var(--border)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                        <span style={{ fontSize: 11, color: "var(--text-3)" }}>{key}</span>
                        <span
                          className="mono"
                          style={{
                            marginLeft: "auto",
                            fontSize: 10,
                            fontWeight: 500,
                            color: v(confidenceTone(conf)),
                          }}
                        >
                          {conf}%
                        </span>
                      </div>
                      <span className="mono" style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.45 }}>
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div
                style={{
                  flex: "none",
                  padding: "10px 12px",
                  background: "var(--surface)",
                  borderTop: "1px solid var(--border)",
                }}
              >
                <Button size="dm" style={{ width: "100%", height: 44, fontSize: 14, fontWeight: 500 }}>
                  Ask questions
                </Button>
              </div>
            </div>
          </Panel>

          {/* B3 */}
          <Panel label="B3 · Q&A — chat and source as tabs">
            <div style={phoneFrame}>
              <div
                style={{
                  flex: "none",
                  padding: "12px 14px 0",
                  background: "var(--surface)",
                  borderBottom: "1px solid var(--border)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      width: 44,
                      height: 44,
                      margin: -8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 15,
                      color: "var(--text-2)",
                      cursor: "pointer",
                    }}
                  >
                    ←
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                    Ask this document
                  </span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
                  <span style={mobileTabStyle(tab === "chat")} onClick={() => setTab("chat")}>
                    Chat
                  </span>
                  <span style={mobileTabStyle(tab === "source")} onClick={() => setTab("source")}>
                    Source · p4
                  </span>
                </div>
              </div>

              {tab === "chat" ? (
                <>
                  <div
                    style={{
                      flex: 1,
                      minHeight: 0,
                      overflow: "auto",
                      padding: 14,
                      display: "flex",
                      flexDirection: "column",
                      gap: 16,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "flex-end" }}>
                      <span
                        style={{
                          maxWidth: "82%",
                          fontSize: 13,
                          lineHeight: 1.55,
                          color: "#fff",
                          background: "var(--accent)",
                          borderRadius: 14,
                          padding: "10px 13px",
                        }}
                      >
                        Are there any auto-renewal clauses?
                      </span>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text)", textWrap: "pretty" }}>
                        Yes — Section 4.2 renews the term automatically for successive{" "}
                        <strong style={{ fontWeight: 600 }}>36-month periods</strong> unless written notice
                        is given at least 90 days before expiry.
                      </span>
                      <button
                        className="mono"
                        onClick={() => setTab("source")}
                        style={{
                          alignSelf: "flex-start",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          fontSize: 11,
                          fontWeight: 500,
                          color: "#fff",
                          background: "var(--accent)",
                          border: "1px solid var(--accent)",
                          borderRadius: 10,
                          padding: "5px 10px",
                          cursor: "pointer",
                        }}
                      >
                        <span className="dot" style={{ background: "#fff" }} />
                        contract.pdf · page 4
                      </button>
                    </div>
                  </div>
                  <div
                    style={{
                      flex: "none",
                      padding: "10px 12px 12px",
                      background: "var(--surface)",
                      borderTop: "1px solid var(--border)",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <Input className="h-[42px] rounded-[10px] border-border bg-[var(--surface)] px-3 text-[13px] text-[var(--text)] md:text-[13px] dark:bg-[var(--surface)]" style={{ flex: 1, minWidth: 0, height: 44, borderColor: "var(--border-strong)" }} placeholder="Ask a question…" />
                    <Button size="dm" style={{ width: 44, height: 44, flex: "none", fontSize: 15, padding: 0 }}
                    >
                      ↑
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <div
                    style={{
                      flex: "none",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "10px 12px",
                      background: "var(--surface)",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    <span
                      className="mono"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: 11,
                        fontWeight: 500,
                        color: "#fff",
                        background: "var(--accent)",
                        borderRadius: 10,
                        padding: "4px 9px",
                      }}
                    >
                      <span className="dot" style={{ background: "#fff" }} />
                      page 4
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        color: "var(--text-3)",
                        minWidth: 0,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Section 4.2 — Term and renewal
                    </span>
                    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 2, flex: "none" }}>
                      <span style={phoneNav}>‹</span>
                      <span className="mono" style={{ fontSize: 11, color: "var(--text)", padding: "0 4px" }}>
                        4/12
                      </span>
                      <span style={phoneNav}>›</span>
                    </div>
                  </div>
                  <div
                    style={{
                      flex: 1,
                      minHeight: 0,
                      overflow: "auto",
                      padding: 14,
                      display: "flex",
                      flexDirection: "column",
                      gap: 12,
                    }}
                  >
                    <MobileClause
                      heading="4.1 Initial term"
                      text="The initial term commences on the Effective Date and continues for thirty-six (36) months, unless terminated earlier under Section 9."
                    />
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                        padding: 12,
                        borderRadius: 10,
                        background: "var(--accent-soft)",
                        border: "1px solid var(--accent-border)",
                        borderLeft: "3px solid var(--accent)",
                      }}
                    >
                      <span
                        className="mono"
                        style={{
                          alignSelf: "flex-start",
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
                        Cited in answer
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 600,
                          letterSpacing: ".04em",
                          textTransform: "uppercase",
                          color: "var(--accent)",
                        }}
                      >
                        4.2 Automatic renewal
                      </span>
                      <span
                        style={{
                          fontSize: 12,
                          lineHeight: 1.7,
                          color: "var(--text)",
                          fontWeight: 450,
                          textWrap: "pretty",
                        }}
                      >
                        Upon expiry of the initial term, this Agreement renews automatically for successive
                        periods of thirty-six (36) months unless either party gives written notice of
                        non-renewal no later than ninety (90) days prior to the end of the then-current term.
                      </span>
                    </div>
                    <MobileClause
                      heading="4.3 Notice of non-renewal"
                      text="Notice must be delivered to the addresses in Schedule A and is effective on receipt. Late notice applies to the following renewal term only."
                    />
                  </div>
                </>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

const phoneNav: CSSProperties = {
  width: 32,
  height: 32,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  border: "1px solid var(--border)",
  borderRadius: 14,
  fontSize: 13,
  color: "var(--text-2)",
};

function MobileClause({ heading, text }: { heading: string; text: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, padding: "10px 12px" }}>
      <span
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: ".04em",
          textTransform: "uppercase",
          color: "var(--text-3)",
        }}
      >
        {heading}
      </span>
      <span style={{ fontSize: 12, lineHeight: 1.7, color: "var(--text-2)", textWrap: "pretty" }}>
        {text}
      </span>
    </div>
  );
}

function Toast({
  tone,
  glyph,
  title,
  body,
  action,
  rounded,
  neutralBorder,
}: {
  tone: "--ok" | "--bad" | "--accent";
  glyph: string;
  title: string;
  body: string;
  action?: string;
  rounded?: boolean;
  neutralBorder?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        padding: "11px 12px",
        border: `1px solid ${neutralBorder ? "var(--border)" : `var(${tone}-border)`}`,
        borderRadius: rounded ? 14 : 10,
        background: "var(--surface)",
        borderLeft: `3px solid var(${tone})`,
      }}
    >
      <span style={{ fontSize: 11, color: `var(${tone})`, lineHeight: 1.4, flex: "none" }}>{glyph}</span>
      <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{title}</span>
        <span style={{ fontSize: 11, color: "var(--text-2)" }}>{body}</span>
      </div>
      {action && (
        <a href="#" style={{ marginLeft: "auto", fontSize: 11, fontWeight: 500, flex: "none" }}>
          {action}
        </a>
      )}
      <span
        style={{
          marginLeft: action ? undefined : "auto",
          fontSize: 11,
          color: "var(--text-3)",
          cursor: "pointer",
          flex: "none",
        }}
      >
        ✕
      </span>
    </div>
  );
}
