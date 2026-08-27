/**
 * The ai-service analysis endpoints, as one passthrough.
 *
 * `POST /api/ai/classify | extract | summarize | pii | risk`
 *
 * These five take text and return structured analysis. They share a request
 * shape closely enough that five near-identical route files would be five
 * copies of the same twelve lines, so the task is a path segment checked
 * against an allowlist — which is also what stops the segment from being used
 * to reach an arbitrary upstream path.
 *
 * `risk` is deliberately not `/risk` upstream: ai-service mounts it at
 * `/analysis/risk`. The allowlist is where that difference is recorded.
 *
 * `/embed` is not exposed. Nothing in the UI needs raw vectors — search-service
 * owns embedding as part of indexing — and an endpoint that costs model tokens
 * should not be reachable from the browser without a caller that needs it.
 */

import type { NextRequest } from "next/server";
import { call, envelope, errorResponse, handle } from "@/lib/server/backend";

/** Frontend task name → ai-service path. The allowlist *is* the validation. */
const TASKS: Record<string, string> = {
  classify: "/classify",
  extract: "/extract",
  summarize: "/summarize",
  pii: "/pii",
  risk: "/analysis/risk",
};

export async function POST(request: NextRequest, ctx: RouteContext<"/api/ai/[task]">) {
  return handle(async () => {
    const { task } = await ctx.params;
    const path = TASKS[task];

    if (!path) {
      return errorResponse(
        envelope(
          "Unknown analysis task",
          `\`${task}\` is not an analysis endpoint. Available: ${Object.keys(TASKS).join(", ")}.`,
          "ERR_UNKNOWN_TASK",
          false,
        ),
        404,
      );
    }

    const body = (await request.json().catch(() => null)) as Record<string, unknown> | null;

    // Every one of these rejects an empty `text` with a 422, so the round trip
    // is skipped and the caller told which field is missing.
    if (!body || typeof body.text !== "string" || body.text.trim() === "") {
      return errorResponse(
        envelope(
          "Nothing to analyse",
          "Send `{ text }` with the document text to analyse.",
          "ERR_NO_TEXT",
          false,
        ),
        400,
      );
    }

    // Forwarded whole: each task accepts its own optional fields alongside
    // `text` (`document_id`, `document_type`, `max_sentences`), and enumerating
    // them here would mean editing this file every time ai-service adds one.
    const result = await call<unknown>("ai", path, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
      signal: request.signal,
    });

    return Response.json(result);
  });
}
