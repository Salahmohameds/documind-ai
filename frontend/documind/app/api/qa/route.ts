/**
 * Workspace question answering, in one call.
 *
 * `POST` — `{ question }` → a written answer with citations.
 *
 * The Gateway's `/qa` chains search `/query` → ai `/answer` itself, so this is
 * one round trip where the client would otherwise make two. That is the whole
 * reason it exists; it buys nothing else.
 *
 * Two limits are worth knowing before reaching for it:
 *
 *   - **It cannot be scoped.** `/qa` accepts a question and nothing else — no
 *     `documentId`, no `top_k`. A caller that needs to restrict retrieval to
 *     one document, or to a document type, must use `/api/search` →
 *     `/api/answer` instead. See `askWorkspace` in `lib/api.ts`.
 *   - **It does not filter empty passages.** ai-service requires every chunk to
 *     have at least one character and rejects the *entire* request with a 422
 *     if one does not. `/api/answer` drops empty passages before sending;
 *     `/qa` retrieves inside the Gateway, so there is no point at which this
 *     route could do the same. Tracked in docs/team/handoff-gateway-wiring.md.
 *
 * In `direct` mode there is no Gateway to orchestrate, so the two calls are
 * made here instead and the response shape is identical either way.
 */

import type { NextRequest } from "next/server";
import {
  call,
  envelope,
  errorResponse,
  handle,
  usingGateway,
} from "@/lib/server/backend";

/** How many passages the direct-mode fallback retrieves and forwards. */
const FALLBACK_TOP_K = 8;

/** ai-service speaks snake_case; the frontend contract is camelCase. */
type UpstreamCitation = {
  chunk_id: string;
  document_id: string | null;
  page: number | null;
  snippet: string;
};

type UpstreamAnswer = {
  answer: string;
  citations: UpstreamCitation[];
  grounded: boolean;
  refused: boolean;
  confidence: number;
  meta?: { model?: string; degraded?: boolean };
};

type UpstreamPassage = {
  chunk_id: string;
  document_id: string;
  text: string;
  page: number | null;
  similarity: number;
};

export type QaCitation = {
  chunkId: string;
  documentId: string | null;
  page: number | null;
  snippet: string;
};

export type QaResponse = {
  text: string;
  citations: QaCitation[];
  grounded: boolean;
  refused: boolean;
  confidence: number;
  model: string | null;
  degraded: boolean;
};

export async function POST(request: NextRequest) {
  return handle(async () => {
    const body = (await request.json().catch(() => ({}))) as { question?: string };
    const question = (body.question ?? "").trim();

    if (question === "") {
      return errorResponse(
        envelope("No question supplied", "Send `{ question }`.", "ERR_NO_QUESTION", false),
        400,
      );
    }

    const upstream = usingGateway
      ? await call<UpstreamAnswer>("ai", "/qa", {
          method: "POST",
          body: JSON.stringify({ question }),
          headers: { "Content-Type": "application/json" },
          signal: request.signal,
        })
      : await orchestrate(question, request.signal);

    const answer: QaResponse = {
      text: upstream.answer,
      citations: (upstream.citations ?? []).map((c) => ({
        chunkId: c.chunk_id,
        documentId: c.document_id ?? null,
        page: c.page ?? null,
        snippet: c.snippet,
      })),
      grounded: upstream.grounded,
      refused: upstream.refused,
      confidence: upstream.confidence,
      model: upstream.meta?.model ?? null,
      degraded: upstream.meta?.degraded ?? false,
    };
    return Response.json(answer);
  });
}

/**
 * What the Gateway's `/qa` does, done here for `direct` mode.
 *
 * Unlike the Gateway's version this drops empty passages, because at this
 * point they are in hand — the one place the fallback is strictly better than
 * the endpoint it replaces.
 */
async function orchestrate(question: string, signal: AbortSignal): Promise<UpstreamAnswer> {
  const retrieved = await call<{ results: UpstreamPassage[] }>(
    "search",
    `/search?question=${encodeURIComponent(question)}&top_k=${FALLBACK_TOP_K}`,
    { signal },
  );

  const chunks = (retrieved.results ?? [])
    .filter((r) => Boolean(r.text?.trim()))
    .map((r) => ({
      chunk_id: r.chunk_id,
      document_id: r.document_id,
      text: r.text,
      page: r.page ?? null,
      score: r.similarity ?? null,
    }));

  return call<UpstreamAnswer>("ai", "/answer", {
    method: "POST",
    body: JSON.stringify({ question, chunks }),
    headers: { "Content-Type": "application/json" },
    signal,
  });
}
