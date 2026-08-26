"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { askDocument } from "@/lib/api";
import { CITATIONS, QA_SUGGESTIONS, qaSnippet } from "@/lib/mock/data";
import {
  ChatComposer,
  ChatEmpty,
  ChatPage,
  ChatPanel,
  ChatThread,
  chipStyle,
  useChatEngine,
  type Cite,
} from "@/components/documind/chat";
import { DocumentReader } from "@/components/documind/reader";
import { ArrowLeftIcon, ChatIcon } from "@/components/ui/icons";
import { Button } from "@/components/ui/button";
import { Anim } from "@/components/motion";

/**
 * Per-document Q&A. Identical surface to the workspace-wide Ask page — it only
 * swaps the retriever and scopes every citation to this one document.
 */
export function QaView({
  docId,
  docName,
  totalPages,
}: {
  docId: string;
  docName: string;
  totalPages: number;
}) {
  const [draft, setDraft] = useState("");
  const [activeCite, setActiveCite] = useState<string | null>(null);

  // Global search links straight at a clause (`/qa/[id]?page=11`), so the
  // reader has to be able to open somewhere other than page one. Only the
  // initial page is taken from the URL — paging around afterwards is local
  // state and shouldn't rewrite history.
  const params = useSearchParams();
  const [page, setPage] = useState(() => {
    const wanted = Number(params.get("page"));
    return Number.isFinite(wanted) && wanted >= 1 ? Math.min(wanted, totalPages) : 1;
  });

  const citation = CITATIONS.find((c) => c.id === activeCite) ?? null;

  /** A source chip drives the reader rather than expanding an inline card. */
  const pickCitation = (id: string) => {
    if (id === activeCite) {
      setActiveCite(null);
      return;
    }
    const c = CITATIONS.find((x) => x.id === id);
    setActiveCite(id);
    if (c) setPage(c.page);
  };

  const chat = useChatEngine({
    thinkingLabel: () => `Reading ${totalPages} pages…`,
    noAnswer: () =>
      "I could not find anything in this document that answers that. Answers here are grounded in this document alone — try the workspace-wide Ask page to search every document at once.",
    ask: async (question) => {
      const answer = await askDocument(question);
      if (!answer) return null;
      return {
        text: answer.text,
        thinking: answer.thinking,
        footnote: `${answer.citations.length} passage${answer.citations.length === 1 ? "" : "s"} from ${totalPages} pages`,
        citations: answer.citations.flatMap((id): Cite[] => {
          const c = CITATIONS.find((x) => x.id === id);
          if (!c) return [];
          return [
            {
              id: c.id,
              label: c.context,
              badge: `p.${c.page}`,
              context: c.context,
              snippet: qaSnippet(c.id),
              meta: `${docName} · page ${c.page}`,
            },
          ];
        }),
      };
    },
  });

  const send = (q: string) => {
    if (chat.busy) return;
    setDraft("");
    chat.send(q);
  };

  return (
    <ChatPage>
      {/* Header --------------------------------------------------------- */}
      <Anim
        style={{ flex: "none", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}
      >
        <Link
          href={`/documents/${docId}`}
          className="hover-surface"
          aria-label="Back to document"
          style={{
            width: 34,
            height: 34,
            flex: "none",
            borderRadius: 10,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-3)",
          }}
        >
          <ArrowLeftIcon size={15} />
        </Link>

        <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
          <span
            title={docName}
            style={{
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: "-.025em",
              color: "var(--text)",
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            Ask this document
          </span>
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
            {docName} · {totalPages} pages · {docId}
          </span>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <Button asChild variant="surface" size="dmQuiet">
            <Link href="/chat" style={{ height: 34 }}>
            Search all documents
            </Link>
          </Button>
          {chat.messages.length > 0 && (
            <Button variant="surface" size="dmQuiet" style={{ height: 34 }}
              onClick={() => {
                chat.clear();
                setActiveCite(null);
              }}
            >
              New thread
            </Button>
          )}
        </div>
      </Anim>

      <div className="dm-reader-grid">
      <ChatPanel>
        {chat.messages.length === 0 ? (
          <ChatEmpty
            icon={<ChatIcon size={19} color="var(--accent)" />}
            title="Ask anything about this document"
            body="Answers cite the exact page they came from, so you can verify every claim against the source before you act on it."
            suggestions={QA_SUGGESTIONS}
            onPick={send}
          />
        ) : (
          <ChatThread
            messages={chat.messages}
            openCite={activeCite}
            onToggleCite={pickCitation}
            onRetry={chat.retry}
            inlineSources={false}
            recovery={() => (
              <>
                <Link href="/chat" style={chipStyle(false)}>
                  Search all documents instead
                </Link>
                {QA_SUGGESTIONS.slice(0, 2).map((q) => (
                  <button key={q} style={chipStyle(false)} onClick={() => send(q)}>
                    Try: {q}
                  </button>
                ))}
              </>
            )}
          />
        )}

        <ChatComposer
          value={draft}
          onChange={setDraft}
          onSubmit={() => send(draft)}
          busy={chat.busy}
          onStop={chat.stop}
          placeholder="Ask a question about this document…"
          hint={`Grounded in this document only · ${totalPages} pages indexed · ⏎ to send`}
        />
      </ChatPanel>

      <DocumentReader
        docName={docName}
        totalPages={totalPages}
        page={page}
        onPageChange={setPage}
        citation={citation}
      />
      </div>
    </ChatPage>
  );
}
