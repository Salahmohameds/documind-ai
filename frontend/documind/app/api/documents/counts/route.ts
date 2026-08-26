/**
 * Library counts by lifecycle state.
 *
 * The sidebar badges need two numbers and nothing else. Giving them their own
 * endpoint keeps a nav badge from pulling the whole document list into every
 * page of the app.
 */

import type { NextRequest } from "next/server";
import { handle } from "@/lib/server/backend";
import { fetchAllDocuments } from "@/lib/server/documents";
import type { DocumentSummary } from "@/lib/types";

export type DocumentCounts = {
  total: number;
  queued: number;
  processing: number;
  completed: number;
  failed: number;
  /** Queued + processing — what the "in flight" badge shows. */
  inFlight: number;
};

export async function GET(request: NextRequest) {
  return handle(async () => {
    const all = await fetchAllDocuments(request.signal);
    const count = (status: DocumentSummary["status"]) =>
      all.filter((d) => d.status === status).length;

    const queued = count("queued");
    const processing = count("processing");

    const counts: DocumentCounts = {
      total: all.length,
      queued,
      processing,
      completed: count("completed"),
      failed: count("failed"),
      inFlight: queued + processing,
    };
    return Response.json(counts);
  });
}
