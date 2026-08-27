/**
 * Documents the pipeline has not finished with.
 *
 * The upload screen's queue is browser-local: it knows about files this tab
 * uploaded and nothing else. Reload the page mid-run and the queue empties
 * while the nav badge -- which counts server-side -- still says two are in
 * flight. The two disagreed because they were answering different questions.
 *
 * This is the question the badge answers, returning rows rather than a number
 * so the queue can show the same documents it is counting.
 *
 * Its own route rather than `?status=` on the library because "in flight" is
 * two statuses, and asking for them separately would fold the whole library
 * twice to answer one question.
 */

import type { NextRequest } from "next/server";
import { handle } from "@/lib/server/backend";
import { fetchAllDocuments } from "@/lib/server/documents";
import type { DocumentSummary } from "@/lib/types";

export async function GET(request: NextRequest) {
  return handle(async () => {
    const all = await fetchAllDocuments(request.signal);
    const inFlight = all.filter(
      (d: DocumentSummary) => d.status === "queued" || d.status === "processing",
    );

    // Oldest first: the one that has been waiting longest is the one worth
    // looking at, and it is the one a newest-first order would bury.
    inFlight.sort((a, b) => a.uploadedAt - b.uploadedAt);

    return Response.json({ rows: inFlight });
  });
}
