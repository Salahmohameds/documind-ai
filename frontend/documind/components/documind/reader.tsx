"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { getPage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Anim } from "@/components/motion";

/**
 * The document reader beside the per-document thread. It is the verification
 * half of the Q&A page: a citation chip drives the page, and the cited passage
 * highlights in place so a claim can be checked against the source.
 */

const navBtn: CSSProperties = {
  width: 24,
  height: 24,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: 10,
  fontSize: 13,
  color: "var(--text-2)",
  cursor: "pointer",
  background: "transparent",
  border: "none",
};

function Stepper({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 2,
        padding: 2,
        border: "1px solid var(--border)",
        borderRadius: 10,
        background: "var(--surface-2)",
        flex: "none",
      }}
    >
      {children}
    </div>
  );
}

export type ReaderCitation = { id: string; page: number; context: string };

export function DocumentReader({
  docName,
  totalPages,
  page,
  onPageChange,
  citation,
}: {
  docName: string;
  totalPages: number;
  page: number;
  onPageChange: (page: number) => void;
  /** The citation currently being verified, if any. */
  citation: ReaderCitation | null;
}) {
  const [zoom, setZoom] = useState(100);
  const scrollRef = useRef<HTMLDivElement>(null);
  const citedRef = useRef<HTMLDivElement>(null);
  const blocks = getPage(page);
  const onCitedPage = !!citation && citation.page === page;

  // Bring the highlighted clause into view whenever the citation changes.
  useEffect(() => {
    if (!onCitedPage) return;
    citedRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [onCitedPage, citation?.id, page]);

  return (
    <Anim
      className="card"
      style={{
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Toolbar -------------------------------------------------------- */}
      <div
        style={{
          flex: "none",
          display: "flex",
          alignItems: "center",
          gap: 10,
          rowGap: 8,
          flexWrap: "wrap",
          padding: "10px clamp(12px, 1.6vw, 16px)",
          borderBottom: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        <span className="eyebrow" style={{ flex: "none" }}>
          Citation
        </span>

        {citation ? (
          <>
            <span
              className="mono"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                flex: "none",
                fontSize: 11,
                fontWeight: 500,
                padding: "4px 9px",
                borderRadius: 10,
                color: "#fff",
                background: "var(--accent)",
                border: "1px solid var(--accent)",
              }}
            >
              <span className="dot" style={{ background: "#fff" }} />
              page {citation.page}
            </span>
            <span
              style={{
                fontSize: 12,
                color: "var(--text-3)",
                flex: "1 1 auto",
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {onCitedPage ? citation.context : `${citation.context} — go to page ${citation.page}`}
            </span>
          </>
        ) : (
          <span
            style={{
              fontSize: 12,
              color: "var(--text-3)",
              flex: "1 1 auto",
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            Ask a question, then pick a source chip to jump to the passage.
          </span>
        )}

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flex: "none" }}>
          <Stepper>
            <button
              style={{ ...navBtn, opacity: page === 1 ? 0.4 : 1 }}
              onClick={() => onPageChange(Math.max(1, page - 1))}
              disabled={page === 1}
              aria-label="Previous page"
            >
              ‹
            </button>
            <span className="mono" style={{ fontSize: 12, color: "var(--text)", padding: "0 8px" }}>
              {page} of {totalPages}
            </span>
            <button
              style={{ ...navBtn, opacity: page === totalPages ? 0.4 : 1 }}
              onClick={() => onPageChange(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              aria-label="Next page"
            >
              ›
            </button>
          </Stepper>

          <Stepper>
            <button style={navBtn} onClick={() => setZoom((z) => Math.max(70, z - 10))} aria-label="Zoom out">
              −
            </button>
            <span className="mono" style={{ fontSize: 12, color: "var(--text)", padding: "0 6px" }}>
              {zoom}%
            </span>
            <button style={navBtn} onClick={() => setZoom((z) => Math.min(160, z + 10))} aria-label="Zoom in">
              +
            </button>
          </Stepper>

          <Button variant="outlineStrong" size="dmQuiet" style={{ height: 28, padding: "0 10px" }} onClick={() => setZoom(100)}>
            Fit width
          </Button>
        </div>
      </div>

      {/* Page ----------------------------------------------------------- */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          minHeight: 0,
          overflow: "auto",
          padding: "clamp(14px, 2vw, 24px)",
          display: "flex",
          justifyContent: "center",
          background: "var(--desk)",
        }}
      >
        <div
          style={{
            width: `${zoom}%`,
            maxWidth: Math.round(6.1 * zoom),
            flex: "none",
            height: "fit-content",
            background: "var(--paper)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            padding: "clamp(20px, 3vw, 36px) clamp(18px, 3vw, 40px)",
            display: "flex",
            flexDirection: "column",
            gap: 4,
            transition: "width .2s var(--ease-out)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 12,
              paddingBottom: 20,
              borderBottom: "1px solid var(--border)",
            }}
          >
            <span
              className="mono"
              title={docName}
              style={{
                fontSize: 10,
                letterSpacing: ".06em",
                textTransform: "uppercase",
                color: "var(--text-3)",
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {docName}
            </span>
            <span className="mono" style={{ marginLeft: "auto", fontSize: 10, color: "var(--text-3)", flex: "none" }}>
              Page {page} of {totalPages}
            </span>
          </div>

          {blocks.map((b) => {
            const cited = !!citation && b.cite === citation.id;
            return (
              <div
                key={b.heading}
                ref={cited ? citedRef : undefined}
                style={
                  cited
                    ? {
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                        padding: "12px 14px",
                        borderRadius: 10,
                        background: "var(--accent-soft)",
                        border: "1px solid var(--accent-border)",
                        borderLeft: "3px solid var(--accent)",
                        transition: "background .3s var(--ease-out)",
                      }
                    : { display: "flex", flexDirection: "column", gap: 6, padding: "12px 14px" }
                }
              >
                {cited && (
                  <Anim
                    as="span"
                    preset="pop"
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
                      marginBottom: 2,
                    }}
                  >
                    Cited in answer
                  </Anim>
                )}
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: ".04em",
                    textTransform: "uppercase",
                    color: cited ? "var(--accent)" : "var(--text-3)",
                  }}
                >
                  {b.heading}
                </span>
                <span
                  style={{
                    fontSize: 13,
                    lineHeight: 1.75,
                    color: cited ? "var(--text)" : "var(--text-2)",
                    fontWeight: cited ? 450 : 400,
                    textWrap: "pretty",
                  }}
                >
                  {b.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </Anim>
  );
}
