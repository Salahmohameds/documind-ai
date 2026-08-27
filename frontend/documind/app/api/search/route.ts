/**
 * Semantic retrieval, backed by search-service.
 *
 * `GET`  — `?q=…&topK=…&documentId=…` → ranked passages.
 * `POST` — `{ documentId, content }` → chunk, embed and index a document.
 *
 * search-service has no per-document filter, so `documentId` is applied here:
 * we over-fetch and narrow, which is correct but not efficient. Pushing the
 * filter into the vector query is the real fix.
 */

import type { NextRequest } from "next/server";
import { call, envelope, errorResponse, handle } from "@/lib/server/backend";

/** search-service speaks snake_case; the frontend contract is camelCase. */
type UpstreamPassage = {
  chunk_id: string;
  document_id: string;
  text: string;
  page: number | null;
  similarity: number;
};

type UpstreamQueryResponse = { question: string; results: UpstreamPassage[] };

export type Passage = {
  chunkId: string;
  documentId: string;
  text: string;
  page: number | null;
  similarity: number;
};

export type RetrievalResponse = { question: string; passages: Passage[] };

/** Over-fetch factor when narrowing to a single document after the fact. */
const SCOPED_OVERFETCH = 6;

export async function GET(request: NextRequest) {
  return handle(async () => {
    const url = new URL(request.url);
    const question = (url.searchParams.get("q") ?? "").trim();
    const documentId = url.searchParams.get("documentId");
    const topK = Math.max(1, Math.min(50, Number(url.searchParams.get("topK")) || 5));

    if (question === "") {
      return errorResponse(
        envelope("No question supplied", "Pass the question as `q`.", "ERR_NO_QUESTION", false),
        400,
      );
    }

    const upstreamTopK = documentId ? Math.min(50, topK * SCOPED_OVERFETCH) : topK;
    const upstream = await call<UpstreamQueryResponse>(
      "search",
      `/search?question=${encodeURIComponent(question)}&top_k=${upstreamTopK}`,
      { signal: request.signal },
    );

    let results = upstream.results ?? [];
    if (documentId) results = results.filter((r) => r.document_id === documentId).slice(0, topK);

    const body: RetrievalResponse = {
      question: upstream.question,
      passages: results.map((r) => ({
        chunkId: r.chunk_id,
        documentId: r.document_id,
        text: r.text,
        page: r.page ?? null,
        similarity: r.similarity,
      })),
    };
    return Response.json(body);
  });
}

export async function POST(request: NextRequest) {
  return handle(async () => {
    const body = (await request.json()) as { documentId?: string; content?: string | string[] };

    if (!body.documentId || body.content === undefined) {
      return errorResponse(
        envelope(
          "Nothing to index",
          "Send `{ documentId, content }`, where content is the full text or an array of per-page texts.",
          "ERR_NO_CONTENT",
          false,
        ),
        400,
      );
    }

    const indexed = await call<{ document_id: string; chunks_indexed: number }>(
      "search",
      "/index",
      {
        method: "POST",
        body: JSON.stringify({ document_id: body.documentId, content: body.content }),
        headers: { "Content-Type": "application/json" },
        signal: request.signal,
      },
    );

    return Response.json({
      documentId: indexed.document_id,
      chunksIndexed: indexed.chunks_indexed,
    });
  });
}
