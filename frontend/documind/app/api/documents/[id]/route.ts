/** One document, with whatever analysis has been written back to it so far. */

import type { NextRequest } from "next/server";
import { DOCUMENT_SERVICE_URL, call, handle } from "@/lib/server/backend";
import type { DocumentDetail } from "@/lib/types";

export async function GET(request: NextRequest, ctx: RouteContext<"/api/documents/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const detail = await call<DocumentDetail>(
      DOCUMENT_SERVICE_URL,
      `/documents/${encodeURIComponent(id)}`,
      { signal: request.signal },
    );
    return Response.json(detail);
  });
}
