/**
 * Sign-in. The one place a JWT enters the system.
 *
 * The Gateway answers `POST /auth/login` with `{ok, token, session}`. The
 * token is moved straight into an httpOnly cookie and stripped from the body,
 * so the browser receives the display fields and never the credential.
 *
 * A rejected sign-in is not an error here — it is a result. The Gateway
 * returns `{ok:false, title, detail, lockedOut}` with a 401, and the form
 * renders those fields directly, so the body is forwarded verbatim rather than
 * flattened into the generic error envelope.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { GATEWAY_URL, envelope, errorResponse } from "@/lib/server/backend";
import { setSessionCookie, type SessionView } from "@/lib/server/session";

/** Sign-in has to survive a cold Gateway, so it gets longer than a data call. */
const LOGIN_TIMEOUT_MS = 15_000;

type GatewayLogin = {
  ok?: boolean;
  token?: string;
  session?: SessionView;
};

export async function POST(request: NextRequest) {
  let credentials: { email?: string; password?: string };
  try {
    credentials = (await request.json()) as { email?: string; password?: string };
  } catch {
    return errorResponse(
      envelope("Malformed request", "Send `{ email, password }`.", "ERR_BAD_REQUEST", false),
      400,
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${GATEWAY_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: credentials.email ?? "",
        password: credentials.password ?? "",
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(LOGIN_TIMEOUT_MS),
    });
  } catch {
    return errorResponse(
      envelope(
        "Cannot reach sign-in",
        `The API Gateway at ${GATEWAY_URL} did not respond. Check that it is running.`,
        "ERR_UPSTREAM_UNREACHABLE",
      ),
      503,
    );
  }

  const body = (await upstream.json().catch(() => null)) as GatewayLogin | null;

  // A refusal the user can act on — wrong password, locked out. Passed through
  // with its status so the form keeps the Gateway's own wording.
  if (!upstream.ok || !body?.ok) {
    return NextResponse.json(
      body ?? {
        ok: false,
        title: "Sign-in failed",
        detail: `The Gateway returned ${upstream.status}.`,
        lockedOut: false,
      },
      { status: upstream.status === 200 ? 401 : upstream.status },
    );
  }

  if (!body.token || !body.session) {
    return errorResponse(
      envelope(
        "Sign-in incomplete",
        "The Gateway accepted the credentials but returned no session token.",
        "ERR_UPSTREAM_CONTRACT",
        false,
      ),
      502,
    );
  }

  // `token` is deliberately absent from what goes back to the browser.
  const response = NextResponse.json({ ok: true, session: body.session });
  setSessionCookie(response, body.token, body.session);
  return response;
}
