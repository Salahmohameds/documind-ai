/**
 * Who is signed in, as far as the browser is allowed to know.
 *
 * The shell needs a name and initials for the account menu, and the token that
 * carries the identity is httpOnly by design — so the display fields come back
 * through here instead. Never returns the token.
 *
 * A signed-out browser gets `{authenticated: false}` and a 200, not a 401:
 * "nobody is signed in" is a successful answer to this question, and a 401
 * would trip the client's session-expired redirect on every public page.
 */

import { NextResponse } from "next/server";
import { readProfile } from "@/lib/server/session";

export async function GET() {
  const profile = await readProfile();
  return NextResponse.json(
    profile ? { authenticated: true, session: profile } : { authenticated: false },
  );
}
