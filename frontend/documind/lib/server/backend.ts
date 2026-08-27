/**
 * Server-side access to the DocuMind backend.
 *
 * Only route handlers under `app/api/` and server components import this. The
 * browser never learns a service URL, a service token, or the session JWT: it
 * talks to `/api/…` on the same origin, and this module is the only code that
 * knows where anything actually lives.
 *
 * Traffic goes through the API Gateway, which owns authentication. Set
 * `DOCUMIND_API_MODE=direct` to bypass it and call each service on its own
 * port — the escape hatch for working on a service in isolation, or for
 * reverting if the Gateway turns out to be the problem.
 */

import { NextResponse } from "next/server";
import { clearSessionCookie, readSessionToken } from "@/lib/server/session";

/* -- Where things live --------------------------------------------------- */

/**
 * The Gateway. Everything the UI needs is mounted here at the same path the
 * downstream service uses, so switching modes changes the host and nothing
 * else.
 */
export const GATEWAY_URL = (
  process.env.GATEWAY_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

/**
 * Individual services. Still needed in two places: `direct` mode, and the
 * health report, which asks each service for its own `/readiness` because the
 * Gateway has no per-service health aggregation to ask instead.
 */
export const DOCUMENT_SERVICE_URL = (
  process.env.DOCUMENT_SERVICE_URL ?? "http://localhost:8081"
).replace(/\/+$/, "");

export const SEARCH_SERVICE_URL = (
  process.env.SEARCH_SERVICE_URL ?? "http://localhost:8080"
).replace(/\/+$/, "");

export const AI_SERVICE_URL = (
  process.env.AI_SERVICE_URL ?? "http://localhost:8082"
).replace(/\/+$/, "");

export type Service = "documents" | "search" | "ai";

const SERVICE_URL: Record<Service, string> = {
  documents: DOCUMENT_SERVICE_URL,
  search: SEARCH_SERVICE_URL,
  ai: AI_SERVICE_URL,
};

export type ApiMode = "gateway" | "direct";

/** `gateway` unless explicitly set otherwise — the flag fails closed, onto auth. */
export const API_MODE: ApiMode =
  process.env.DOCUMIND_API_MODE === "direct" ? "direct" : "gateway";

/** True when a capability exists only on the Gateway and has no direct equivalent. */
export const usingGateway = API_MODE === "gateway";

/**
 * Which host serves a call.
 *
 * The path never changes: the Gateway mounts `/documents`, `/search`, `/index`,
 * `/classify` and the rest at exactly the paths the services use, so mode
 * selection is a base-URL swap and callers stay identical.
 */
export function route(service: Service): string {
  return API_MODE === "gateway" ? GATEWAY_URL : SERVICE_URL[service];
}

/**
 * search-service rejects everything except its probes without a bearer unless
 * it runs with `DISABLE_AUTH=true`. Only used in `direct` mode — in `gateway`
 * mode the session JWT is the credential.
 *
 * Note the Gateway strips `Authorization` before forwarding and mints nothing
 * downstream, so a search-service with auth enforced will reject the Gateway's
 * own calls. Tracked in docs/team/handoff-gateway-wiring.md.
 */
const SERVICE_TOKEN = process.env.SEARCH_SERVICE_TOKEN ?? "";

/** How long a service gets before we give up and report it unavailable. */
const TIMEOUT_MS = Number(process.env.BACKEND_TIMEOUT_MS ?? 10_000);

/* -- The one error shape ------------------------------------------------- */

/**
 * The single error envelope the frontend understands.
 *
 * document-service already emits exactly this, so its errors are forwarded
 * verbatim. Everything else — and there are nine distinct shapes across the
 * Gateway, the three services and FastAPI itself — is normalised into it by
 * `readError`, so `lib/api.ts` has one thing to parse.
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

export function errorResponse(body: ErrorEnvelope, status: number): NextResponse {
  return NextResponse.json(body, { status });
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

/**
 * The token was missing, expired or rejected.
 *
 * Its own code because it is the one error with a required side effect: the
 * cookie has to be cleared, and the client has to navigate to sign-in rather
 * than render a retry button for something no retry can fix.
 */
export const SESSION_EXPIRED = "ERR_SESSION_EXPIRED";

/* -- Calling a service --------------------------------------------------- */

type CallOptions = {
  method?: string;
  body?: BodyInit;
  headers?: Record<string, string>;
  /** Forwarded so a client navigating away actually cancels the upstream call. */
  signal?: AbortSignal;
  /**
   * Skip the session bearer. Only for calls that are legitimately anonymous —
   * sign-in and registration, which are how a session is obtained in the first
   * place.
   */
  anonymous?: boolean;
};

/**
 * Calls the backend and returns its parsed JSON, or throws `BackendError`.
 *
 * Route handlers catch that one error type and forward `err.envelope` with
 * `err.status`, which is why no handler needs its own error vocabulary.
 */
export async function call<T>(
  service: Service,
  path: string,
  opts: CallOptions = {},
): Promise<T> {
  const { method = "GET", body, headers = {}, signal, anonymous = false } = opts;
  const base = route(service);

  if (!anonymous) {
    if (API_MODE === "gateway") {
      const token = await readSessionToken();
      // No cookie at all is the same outcome as a rejected one — sign in. Said
      // here rather than after a pointless round trip the Gateway would 401.
      if (!token) throw sessionExpired();
      headers.Authorization = `Bearer ${token}`;
    } else if (service === "search" && SERVICE_TOKEN) {
      headers.Authorization = `Bearer ${SERVICE_TOKEN}`;
    }
  }

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
      // Backend data is per-request and mutable; a cached document list would
      // show a stale pipeline state seconds after an upload.
      cache: "no-store",
    });
  } catch (cause) {
    // The caller cancelled — not a backend failure, and not ours to report.
    if (signal?.aborted) {
      throw new BackendError(
        envelope("Request cancelled", "The request was cancelled.", "ERR_CANCELLED", false),
        499,
      );
    }
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

  // Any 401 from the Gateway means this session is over. There is no refresh
  // endpoint, so retrying can only produce another 401.
  if (response.status === 401 && !anonymous) throw sessionExpired();

  if (!response.ok) throw new BackendError(await readError(response, base), response.status);

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function sessionExpired(): BackendError {
  return new BackendError(
    envelope(
      "Your session has ended",
      "Sessions last 24 hours and cannot be renewed. Sign in to continue.",
      SESSION_EXPIRED,
      false,
    ),
    401,
  );
}

/* -- Reading an error ---------------------------------------------------- */

/**
 * Turns whatever the backend returned on an error into the standard envelope.
 *
 * Nine shapes reach this function, and they disagree about almost everything —
 * which key holds the title, whether `detail` is a string or a list, whether
 * there is a body at all:
 *
 *   1. `{error, detail, code, retryable}`     document-service
 *   2. `{code, title, detail, retryable}`     ai-service — `title`, not `error`
 *   3. `{error, detail, code}`                Gateway 401, no `retryable`
 *   4. `{error, detail, code: ERR_PROXY}`     Gateway 502/504
 *   5. `{detail: "..."}`                      FastAPI HTTPException
 *   6. `{detail: [{loc, msg, ...}]}`          FastAPI 422 — a *list*
 *   7. `{error: "..."}`                       search-service auth, no `detail`
 *   8. `{ok: false, title, detail}`           Gateway login/register
 *   9. no JSON at all                         crashed proxy, HTML, empty body
 *
 * Shapes 1–4 and 8 carry service-authored copy, so they are forwarded intact
 * rather than flattened to a generic message.
 */
async function readError(response: Response, base: string): Promise<ErrorEnvelope> {
  const fallbackCode = `ERR_UPSTREAM_${response.status}`;
  const retryable = response.status >= 500;

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    // (9) HTML from a crashed proxy, or an empty body.
    return envelope(
      "Service error",
      `${base} returned ${response.status} ${response.statusText}.`,
      fallbackCode,
      retryable,
    );
  }

  if (payload && typeof payload === "object") {
    const p = payload as Record<string, unknown>;
    const code = typeof p.code === "string" ? p.code : fallbackCode;
    const flag = typeof p.retryable === "boolean" ? p.retryable : retryable;

    // (1)(3)(4) Already our envelope — forward it so service copy wins.
    if (typeof p.error === "string" && typeof p.detail === "string") {
      return { error: p.error, detail: p.detail, code, retryable: flag };
    }

    // (2)(8) Same fields, `title` where document-service says `error`.
    if (typeof p.title === "string" && typeof p.detail === "string") {
      return { error: p.title, detail: p.detail, code, retryable: flag };
    }

    // (6) FastAPI validation. Each entry names the field it rejected, which is
    // the only part a user can act on — losing it to a generic "returned 422"
    // leaves them staring at a form with no idea which input was wrong.
    if (Array.isArray(p.detail)) {
      const problems = p.detail
        .map(readValidationProblem)
        .filter((s): s is string => s !== null);
      return envelope(
        "That request was rejected",
        problems.length > 0
          ? problems.join("; ")
          : `${base} rejected the request as invalid.`,
        "ERR_VALIDATION",
        false,
      );
    }

    // (5) FastAPI HTTPException.
    if (typeof p.detail === "string") {
      return envelope("Service error", p.detail, fallbackCode, retryable);
    }

    // (7) search-service's auth middleware — `error` and nothing else.
    if (typeof p.error === "string") {
      return envelope("Service error", p.error, fallbackCode, retryable);
    }
  }

  return envelope(
    "Service error",
    `${base} returned ${response.status} ${response.statusText}.`,
    fallbackCode,
    retryable,
  );
}

/** `{loc: ["body","chunks",0,"text"], msg: "..."}` → `"chunks.0.text: ..."`. */
function readValidationProblem(entry: unknown): string | null {
  if (!entry || typeof entry !== "object") return null;
  const e = entry as { loc?: unknown; msg?: unknown };
  if (typeof e.msg !== "string") return null;

  const path = Array.isArray(e.loc)
    ? e.loc
        // The first segment is always where it came from — body, query, path —
        // which the user did not choose and cannot correct.
        .slice(1)
        .map((segment) => String(segment))
        .join(".")
    : "";

  return path === "" ? e.msg : `${path}: ${e.msg}`;
}

/* -- Handler wrapper ----------------------------------------------------- */

/**
 * Wraps a route handler so every thrown `BackendError` becomes its envelope.
 *
 * An ended session additionally clears the cookie on the way out, so the next
 * request from this browser is unauthenticated by construction rather than
 * depending on the client having handled the redirect.
 */
export async function handle(run: () => Promise<Response>): Promise<Response> {
  try {
    return await run();
  } catch (err) {
    if (err instanceof BackendError) {
      const response = errorResponse(err.envelope, err.status);
      if (err.envelope.code === SESSION_EXPIRED) clearSessionCookie(response);
      return response;
    }
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
