/**
 * The shared shape of document-service's bulk operations.
 *
 * Delete and reprocess have the same contract in both directions, and one
 * property worth stating plainly: **a per-document failure is a 200.** The
 * result reports which ids succeeded and why the rest did not, so a route
 * handler must never read a successful call as "everything worked".
 */

import type { NextRequest } from "next/server";

export type BulkResult = {
  requested: number;
  succeeded: string[];
  failed: { id: string; name: string; reason: string }[];
};

/**
 * Reads `{ids: [...]}` from a request body.
 *
 * Returns `null` for anything unusable — absent body, wrong shape, empty list
 * — so the caller answers with its own message rather than forwarding a
 * pointless call that document-service would reject with a 422.
 */
export async function readBulkIds(request: NextRequest): Promise<string[] | null> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return null;
  }

  if (!body || typeof body !== "object") return null;
  const ids = (body as { ids?: unknown }).ids;
  if (!Array.isArray(ids)) return null;

  const clean = ids.filter((id): id is string => typeof id === "string" && id !== "");
  return clean.length > 0 ? clean : null;
}
