/**
 * The polling endpoint for a document still moving through the pipeline.
 *
 * Deliberately separate from the detail route: a list of ten processing rows
 * polls this every couple of seconds, and it must not drag the full analysis
 * payload across the wire each time.
 */

import type { NextRequest } from "next/server";
import { DOCUMENT_SERVICE_URL, call, handle } from "@/lib/server/backend";
import type { DocError } from "@/lib/types";

export type DocumentStatus = {
  id: string;
  status: string;
  risk: number | null;
  verdict: string;
  progress?: { step: number; pct: number } | null;
  error?: DocError | null;
};

export async function GET(request: NextRequest, ctx: RouteContext<"/api/documents/[id]/status">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const status = await call<DocumentStatus>(
      DOCUMENT_SERVICE_URL,
      `/documents/${encodeURIComponent(id)}/status`,
      { signal: request.signal },
    );
    return Response.json(status);
  });
}
