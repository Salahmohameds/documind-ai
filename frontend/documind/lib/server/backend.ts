/**
 * Server-side access to the DocuMind microservices.
 *
 * Only route handlers under `app/api/` import this. The browser never learns a
 * service URL or a service token: it talks to `/api/…` on the same origin, and
 * this module is the only place that knows where `document-service` and
 * `search-service` actually live.
 */

/** Where each service listens. Overridden per environment; never hard-coded in a component. */
export const DOCUMENT_SERVICE_URL = (
  process.env.DOCUMENT_SERVICE_URL ?? "http://localhost:8081"
).replace(/\/+$/, "");

export const SEARCH_SERVICE_URL = (
  process.env.SEARCH_SERVICE_URL ?? "http://localhost:8080"
).replace(/\/+$/, "");

/**
 * search-service rejects everything except its probes unless a bearer token is
 * present (`DISABLE_AUTH=true` in local dev). The gateway will mint these once
 * it exists; until then the token is a shared secret held server-side only.
 */
const SERVICE_TOKEN = process.env.SEARCH_SERVICE_TOKEN ?? "";

/** How long a service gets before we give up and report it unavailable. */
const TIMEOUT_MS = Number(process.env.BACKEND_TIMEOUT_MS ?? 10_000);

/**
 * The single error envelope the frontend understands.
 *
 * document-service already emits exactly this shape, so an upstream error can
 * be forwarded verbatim. Everything else — a timeout, a refused connection, a
 * bare-string FastAPI detail — is normalised into it here, so `lib/api.ts` has
 * one shape to parse rather than four.
 */
export type ErrorEnvelope = {
  error: string;
  detail: string;
  code: string;
  retryable: boolean;
};

export function envelope(
  error: string,
  detail: string,
  code: string,
  retryable = true,
): ErrorEnvelope {
  return { error, detail, code, retryable };
}

export function errorResponse(body: ErrorEnvelope, status: number): Response {
  return Response.json(body, { status });
}

/** Distinguishes "the service answered with an error" from "we never reached it". */
export class BackendError extends Error {
  constructor(
    readonly envelope: ErrorEnvelope,
    readonly status: number,
  ) {
    super(envelope.error);
    this.name = "BackendError";
  }
}

type CallOptions = {
  method?: string;
  body?: BodyInit;
  headers?: Record<string, string>;
  /** Forwarded so a client navigating away actually cancels the upstream call. */
  signal?: AbortSignal;
  /** search-service needs the bearer; document-service does not. */
  auth?: boolean;
};

/**
 * Calls a service and returns its parsed JSON, or throws `BackendError`.
 *
 * Route handlers catch that one error type and forward `err.envelope` with
 * `err.status`, which is why no handler needs its own error vocabulary.
 */
export async function call<T>(
  base: string,
  path: string,
  opts: CallOptions = {},
): Promise<T> {
  const { method = "GET", body, headers = {}, signal, auth = false } = opts;

  if (auth && SERVICE_TOKEN) headers.Authorization = `Bearer ${SERVICE_TOKEN}`;

  // Two independent reasons to abort — the caller going away, and our own
  // deadline — folded into the one signal `fetch` accepts.
  const timeout = AbortSignal.timeout(TIMEOUT_MS);
  const abort = signal ? AbortSignal.any([signal, timeout]) : timeout;

  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      method,
      body,
      headers,
      signal: abort,
      // Service data is per-request and mutable; a cached document list would
      // show a stale pipeline state seconds after an upload.
      cache: "no-store",
    });
  } catch (cause) {
    // The caller cancelled — not a service failure, and not ours to report.
    if (signal?.aborted) throw new BackendError(
      envelope("Request cancelled", "The request was cancelled.", "ERR_CANCELLED", false),
      499,
    );
    const timedOut = cause instanceof DOMException && cause.name === "TimeoutError";
    throw new BackendError(
      envelope(
        "Service unavailable",
        timedOut
          ? `The service at ${base} did not respond within ${TIMEOUT_MS / 1000}s.`
          : `Could not reach the service at ${base}. Check that it is running and that its URL is configured.`,
        timedOut ? "ERR_UPSTREAM_TIMEOUT" : "ERR_UPSTREAM_UNREACHABLE",
      ),
      503,
    );
  }

  if (!response.ok) throw new BackendError(await readError(response, base), response.status);

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * Turns whatever a service returned on an error into the standard envelope.
 *
 * document-service returns the envelope already; FastAPI's own validation and
 * `HTTPException` return `{detail}`; a crashed proxy returns HTML. All three
 * have to arrive at the UI as something a user can read.
 */
async function readError(response: Response, base: string): Promise<ErrorEnvelope> {
  const fallbackCode = `ERR_UPSTREAM_${response.status}`;
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    return envelope(
      "Service error",
      `${base} returned ${response.status} ${response.statusText}.`,
      fallbackCode,
      response.status >= 500,
    );
  }

  if (payload && typeof payload === "object") {
    const p = payload as Record<string, unknown>;
    // Already our envelope — forward it unchanged so service-authored copy wins.
    if (typeof p.error === "string" && typeof p.detail === "string") {
      return {
        error: p.error,
        detail: p.detail,
        code: typeof p.code === "string" ? p.code : fallbackCode,
        retryable: typeof p.retryable === "boolean" ? p.retryable : response.status >= 500,
      };
    }
    if (typeof p.detail === "string") {
      return envelope("Service error", p.detail, fallbackCode, response.status >= 500);
    }
    if (typeof p.error === "string") {
      return envelope("Service error", p.error, fallbackCode, response.status >= 500);
    }
  }

  return envelope(
    "Service error",
    `${base} returned ${response.status} ${response.statusText}.`,
    fallbackCode,
    response.status >= 500,
  );
}

/** Wraps a route handler body so every thrown `BackendError` becomes its envelope. */
export async function handle(run: () => Promise<Response>): Promise<Response> {
  try {
    return await run();
  } catch (err) {
    if (err instanceof BackendError) return errorResponse(err.envelope, err.status);
    return errorResponse(
      envelope(
        "Unexpected error",
        err instanceof Error ? err.message : "An unexpected error occurred.",
        "ERR_INTERNAL",
        false,
      ),
      500,
    );
  }
}
