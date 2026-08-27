/**
 * Account creation.
 *
 * Deliberately does not sign the new account in: the Gateway's
 * `POST /auth/register` issues no token, and the screen it feeds ends on a
 * "check your email" state rather than a dashboard.
 *
 * Like sign-in, a rejection is a result rather than an error — the Gateway
 * returns `{ok:false, field, title, detail}` naming the input that failed, and
 * the form highlights that field. Forwarded verbatim.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { GATEWAY_URL, envelope, errorResponse } from "@/lib/server/backend";

const REGISTER_TIMEOUT_MS = 15_000;

type RegisterInput = {
  name?: string;
  email?: string;
  org?: string;
  password?: string;
};

export async function POST(request: NextRequest) {
  let input: RegisterInput;
  try {
    input = (await request.json()) as RegisterInput;
  } catch {
    return errorResponse(
      envelope(
        "Malformed request",
        "Send `{ name, email, org, password }`.",
        "ERR_BAD_REQUEST",
        false,
      ),
      400,
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${GATEWAY_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: input.name ?? "",
        email: input.email ?? "",
        org: input.org ?? "",
        password: input.password ?? "",
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(REGISTER_TIMEOUT_MS),
    });
  } catch {
    return errorResponse(
      envelope(
        "Cannot reach registration",
        `The API Gateway at ${GATEWAY_URL} did not respond. Check that it is running.`,
        "ERR_UPSTREAM_UNREACHABLE",
      ),
      503,
    );
  }

  const body = await upstream.json().catch(() => null);

  if (body === null) {
    return errorResponse(
      envelope(
        "Registration failed",
        `The Gateway returned ${upstream.status} with no readable body.`,
        "ERR_UPSTREAM_CONTRACT",
        upstream.status >= 500,
      ),
      upstream.status >= 400 ? upstream.status : 502,
    );
  }

  return NextResponse.json(body, { status: upstream.status });
}
