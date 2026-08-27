/**
 * Sign-out.
 *
 * The Gateway issues stateless JWTs and has no revocation endpoint, so signing
 * out is exactly one thing: drop the cookie. The token stays technically valid
 * until it expires, which is a property of the token design rather than
 * something this route can fix — worth knowing if a token is ever leaked.
 */

import { NextResponse } from "next/server";
import { clearSessionCookie } from "@/lib/server/session";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  clearSessionCookie(response);
  return response;
}
