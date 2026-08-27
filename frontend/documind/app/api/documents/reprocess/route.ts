/**
 * Bulk reprocess.
 *
 * document-service resets each document to *queued* and republishes the
 * processing job on the same Redis stream the upload flow uses, so a
 * reprocessed document is indistinguishable downstream from a fresh one.
 *
 * Its own route rather than a verb on `/api/documents` because reprocess is a
 * POST and the collection already answers POST with "upload a file".
 */

import type { NextRequest } from "next/server";
import { call, envelope, errorResponse, handle } from "@/lib/server/backend";
import { readBulkIds, type BulkResult } from "@/lib/server/bulk";

export async function POST(request: NextRequest) {
  return handle(async () => {
    const ids = await readBulkIds(request);
    if (ids === null) {
      return errorResponse(
        envelope(
          "Nothing to reprocess",
          "Send `{ ids: [...] }` with at least one document id.",
          "ERR_NO_IDS",
          false,
        ),
        400,
      );
    }

    const result = await call<BulkResult>("documents", "/documents/reprocess", {
      method: "POST",
      body: JSON.stringify({ ids }),
      headers: { "Content-Type": "application/json" },
      signal: request.signal,
    });

    return Response.json(result);
  });
}
