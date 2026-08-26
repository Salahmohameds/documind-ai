/**
 * The document library.
 *
 * `GET`  — the library, with search/filter/sort/pagination applied here
 *          because document-service does not yet accept them (see
 *          `lib/server/documents.ts`).
 * `POST` — a multipart upload, streamed straight through to document-service,
 *          which validates the PDF, stores it and publishes the processing job.
 */

import type { NextRequest } from "next/server";
import { DOCUMENT_SERVICE_URL, call, envelope, errorResponse, handle } from "@/lib/server/backend";
import { applyQuery, fetchAllDocuments, parseDocumentQuery } from "@/lib/server/documents";
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

    const created = await call<DocumentSummary>(DOCUMENT_SERVICE_URL, "/documents", {
      method: "POST",
      body: upstream,
      signal: request.signal,
    });

    // 202: document-service has stored the file and queued the job; analysis
    // has not run yet. The client polls `/status` from here.
    return Response.json(created, { status: 202 });
  });
}
