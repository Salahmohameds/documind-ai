/**
 * The document library.
 *
 * `GET`    — the library, with search/filter/sort/pagination applied here
 *            because document-service does not yet accept them (see
 *            `lib/server/documents.ts`).
 * `POST`   — a multipart upload, streamed through to document-service, which
 *            validates the PDF, stores it and publishes the processing job.
 * `DELETE` — bulk delete. Collection-level and body-carrying, matching the
 *            upstream contract: `{ids: […]}` in, a `BulkResult` out.
 */

import type { NextRequest } from "next/server";
import { call, envelope, errorResponse, handle } from "@/lib/server/backend";
import { applyQuery, fetchAllDocuments, parseDocumentQuery } from "@/lib/server/documents";
import { readBulkIds, type BulkResult } from "@/lib/server/bulk";
import type { DocumentSummary } from "@/lib/types";

export async function GET(request: NextRequest) {
  return handle(async () => {
    const query = parseDocumentQuery(new URL(request.url));
    const all = await fetchAllDocuments(request.signal);
    return Response.json(applyQuery(all, query));
  });
}

export async function POST(request: NextRequest) {
  return handle(async () => {
    const form = await request.formData();
    const file = form.get("file");

    if (!(file instanceof File)) {
      return errorResponse(
        envelope(
          "No file supplied",
          "Attach the document as the `file` field of a multipart/form-data body.",
          "ERR_NO_FILE",
          false,
        ),
        400,
      );
    }

    // Rebuilt rather than forwarded verbatim so the upstream request carries
    // exactly one field under the name document-service expects.
    const upstream = new FormData();
    upstream.append("file", file, file.name);

    const created = await call<DocumentSummary>("documents", "/documents", {
      method: "POST",
      body: upstream,
      signal: request.signal,
    });

    // 202: the file is stored and the job is queued; analysis has not run yet.
    // The client polls `/status` from here.
    return Response.json(created, { status: 202 });
  });
}

export async function DELETE(request: NextRequest) {
  return handle(async () => {
    const ids = await readBulkIds(request);
    if (ids === null) return badBulkBody();

    const result = await call<BulkResult>("documents", "/documents", {
      method: "DELETE",
      body: JSON.stringify({ ids }),
      headers: { "Content-Type": "application/json" },
      signal: request.signal,
    });

    return Response.json(result);
  });
}

function badBulkBody() {
  return errorResponse(
    envelope(
      "Nothing to delete",
      "Send `{ ids: [...] }` with at least one document id.",
      "ERR_NO_IDS",
      false,
    ),
    400,
  );
}
