/**
 * Grounded answer generation, backed by ai-service.
 *
 * `POST` — `{ question, passages[] }` → a written answer with citations.
 *
 * This is a generation proxy, not a search endpoint. ai-service's `/answer`
 * deliberately does not retrieve (see `services/ai-service/app/routes/answer.py`),
 * so the caller retrieves first via `/api/search` and passes the passages it
 * got. Keeping the two calls separate is what lets retrieval quality and
 * answer quality be measured independently.
 */

import type { NextRequest } from "next/server";
import { AI_SERVICE_URL, call, envelope, errorResponse, handle } from "@/lib/server/backend";

/** How many passages we will forward. Matches ai-service's own context cap. */
const MAX_PASSAGES = 12;

/** ai-service speaks snake_case; the frontend contract is camelCase. */
type UpstreamCitation = {
  chunk_id: string;
  document_id: string | null;
  page: number | null;
  snippet: string;
};

type UpstreamAnswerResponse = {
  answer: string;
  citations: UpstreamCitation[];
  grounded: boolean;
  refused: boolean;
  confidence: number;
  meta?: { model?: string; provider?: string; duration_ms?: number; degraded?: boolean };
};

export type AnswerCitation = {
  chunkId: string;
  documentId: string | null;
  page: number | null;
  snippet: string;
};

export type AnswerResponse = {
  text: string;
  citations: AnswerCitation[];
  /** True when every citation marker resolved to a passage that was supplied. */
  grounded: boolean;
  /** True when the model said the context does not answer the question. */
  refused: boolean;
  /** Share of citation markers that resolved — not a semantic confidence. */
  confidence: number;
  model: string | null;
  /** True when the answer came from a fallback path inside ai-service. */
  degraded: boolean;
};

type RequestPassage = {
  chunkId?: string;
  documentId?: string | null;
  text?: string;
  page?: number | null;
  similarity?: number;
};

export async function POST(request: NextRequest) {
  return handle(async () => {
    const body = (await request.json()) as { question?: string; passages?: RequestPassage[] };
    const question = (body.question ?? "").trim();

    if (question === "") {
      return errorResponse(
        envelope("No question supplied", "Send `{ question, passages }`.", "ERR_NO_QUESTION", false),
        400,
      );
    }

    // A passage with no text cannot ground anything, and ai-service rejects it
    // outright — dropping it here keeps one empty hit from failing the whole
    // request.
    const passages = (body.passages ?? [])
      .filter((p): p is RequestPassage & { text: string } => Boolean(p.text?.trim()))
      .slice(0, MAX_PASSAGES);

    const upstream = await call<UpstreamAnswerResponse>(AI_SERVICE_URL, "/answer", {
      method: "POST",
      body: JSON.stringify({
        question,
        chunks: passages.map((p, i) => ({
          chunk_id: p.chunkId ?? `chunk-${i + 1}`,
          document_id: p.documentId ?? null,
          text: p.text,
          page: p.page ?? null,
          score: p.similarity ?? null,
        })),
      }),
      headers: { "Content-Type": "application/json" },
      signal: request.signal,
    });

    const answer: AnswerResponse = {
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
