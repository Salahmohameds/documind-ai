"use client";

import Link from "next/link";
import { useState } from "react";
import { askWorkspace, scopeSize, type Simulate } from "@/lib/api";
import { CHAT_SCOPES, CHAT_SUGGESTIONS } from "@/lib/mock/data";
import type { ChatScope } from "@/lib/types";
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
import { EmptyPanel, StateSwitcher } from "@/components/documind/feedback";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CaretDownIcon, ChatIcon, FileIcon, SearchIcon } from "@/components/ui/icons";
import { Button } from "@/components/ui/button";

const SIMULATIONS = [
  { value: "ok" as const, label: "Default" },
  { value: "slow" as const, label: "Slow" },
  { value: "error" as const, label: "Error" },
];

const SCOPE_LABEL: Record<ChatScope, string> = {
  All: "All documents",
  Contract: "Contracts",
  Amendment: "Amendments",
  Invoice: "Invoices",
  Statement: "Statements",
};

export function ChatView() {
  const [simulate, setSimulate] = useState<Simulate>("ok");
  const [scope, setScope] = useState<ChatScope>("All");
  const [draft, setDraft] = useState("");
  const [openCite, setOpenCite] = useState<string | null>(null);

  const inScope = scopeSize(scope);

  const chat = useChatEngine({
    thinkingLabel: () =>
      `Searching ${inScope} ${scope === "All" ? "documents" : SCOPE_LABEL[scope].toLowerCase()}…`,
    userNote: () => (scope === "All" ? undefined : `scoped to ${SCOPE_LABEL[scope].toLowerCase()}`),
    noAnswer: () =>
      scope === "All"
        ? "Nothing in the indexed corpus answers that. Answers here are grounded in your documents only — if the information lives in an email or a system of record, it will not be found here."
        : `Nothing in ${SCOPE_LABEL[scope].toLowerCase()} answers that. Widen the scope to all documents and ask again.`,
    ask: async (question) => {
      const answer = await askWorkspace(question, scope, { simulate });
      if (!answer) return null;
      return {
        text: answer.text,
        thinking: answer.thinking,
        footnote: `${answer.citations.length} of ${answer.searched} documents searched`,
        citations: answer.citations.map(
          (c): Cite => ({
            id: c.id,
            label: c.docName,
            badge: `p.${c.page}`,
            context: c.context,
            snippet: c.snippet,
            meta: `${c.docName} · page ${c.page}`,
            actions: (
              <>
                <Link href={`/documents/${c.docId}`} style={{ fontSize: 12, fontWeight: 500 }}>
                  Open document →
                </Link>
                <Link href={`/qa/${c.docId}`} style={{ fontSize: 12, fontWeight: 500 }}>
                  Ask this document →
                </Link>
              </>
            ),
          }),
        ),
      };
    },
  });

  const send = (q: string) => {
    if (inScope === 0 || chat.busy) return;
    setDraft("");
    chat.send(q);
  };

  return (
    <ChatPage>
      {/* Header --------------------------------------------------------- */}
      <div
        className="anim-up"
        style={{ flex: "none", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-.025em", color: "var(--text)" }}>
            Ask your documents
          </span>
          <span style={{ fontSize: 12, color: "var(--text-3)" }}>
            Grounded answers across the whole workspace · every claim cites its source
          </span>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="surface" size="dmQuiet" className="group/scope" style={{ height: 34 }}>
                <SearchIcon size={13} color="var(--text-3)" />
                {SCOPE_LABEL[scope]}
                <span className="mono" style={{ color: "var(--text-3)" }}>
                  {inScope}
                </span>
                <span className="flex transition-transform duration-200 group-aria-expanded/scope:rotate-180">
                  <CaretDownIcon size={12} color="var(--text-3)" />
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              sideOffset={6}
              style={{ width: 200 }}
              className="anim-down rounded-xl p-1.5 shadow-[0_14px_34px_rgba(11,18,32,.16)]"
            >
              {CHAT_SCOPES.map((s) => (
                <DropdownMenuItem
                  key={s}
                  onSelect={() => setScope(s)}
                  className="rounded-[9px] px-2.5 py-[7px] text-xs text-[var(--text-2)]"
                >
                  <span className="min-w-0 flex-1 truncate">{SCOPE_LABEL[s]}</span>
                  <span className="flex-none font-mono text-[10px] text-[var(--text-3)]">{scopeSize(s)}</span>
                  {scope === s && <span className="flex-none text-[10px] text-primary">✓</span>}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {chat.messages.length > 0 && (
            <Button variant="surface" size="dmQuiet" style={{ height: 34 }}
              onClick={() => {
                chat.clear();
                setOpenCite(null);
              }}
            >
              New thread
            </Button>
          )}
        </div>
      </div>

      <ChatPanel>
        {chat.messages.length === 0 ? (
          inScope === 0 ? (
            <div style={{ flex: 1, minHeight: 0, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
              <EmptyPanel
                compact
                glyph={<FileIcon size={17} color="var(--s400)" />}
                title={`No ${SCOPE_LABEL[scope].toLowerCase()} to search`}
                body="The retriever has nothing in this scope. Widen the scope, or upload documents to build the index."
                actions={
                  <>
                    <Button variant="surface" size="dmQuiet" onClick={() => setScope("All")}>
                      Search all documents
                    </Button>
                    <Button asChild size="dm">
                      <Link href="/upload" style={{ padding: "0 16px" }}>
                      Upload documents
                      </Link>
                    </Button>
                  </>
                }
              />
            </div>
          ) : (
            <ChatEmpty
              icon={<ChatIcon size={19} color="var(--accent)" />}
              title={`Ask across ${inScope} documents`}
              body="Answers are assembled from your indexed contracts, amendments, invoices and statements — and every claim links back to the exact page it came from."
              suggestions={CHAT_SUGGESTIONS}
              onPick={send}
            />
          )
        ) : (
          <ChatThread
            messages={chat.messages}
            openCite={openCite}
            onToggleCite={(id) => setOpenCite((o) => (o === id ? null : id))}
            onRetry={chat.retry}
            recovery={() => (
              <>
                {scope !== "All" && (
                  <button style={chipStyle(false)} onClick={() => setScope("All")}>
                    Widen to all documents
                  </button>
                )}
                {CHAT_SUGGESTIONS.slice(0, 2).map((q) => (
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
          disabled={inScope === 0}
          placeholder={
            inScope === 0
              ? "Nothing in scope to search…"
              : `Ask anything about your ${SCOPE_LABEL[scope].toLowerCase()}…`
          }
          hint={`Grounded in ${inScope} indexed document${inScope === 1 ? "" : "s"} · ⏎ to send · answers cite their source page`}
        />
      </ChatPanel>

      <StateSwitcher value={simulate} options={SIMULATIONS} onChange={setSimulate} />
    </ChatPage>
  );
}
