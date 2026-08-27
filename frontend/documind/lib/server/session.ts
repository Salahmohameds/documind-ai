/**
 * The signed-in session, held in an httpOnly cookie.
 *
 * The Gateway issues a 24-hour HS256 JWT and has no refresh endpoint, so a
 * stolen token is usable for a full day. That is the whole reason the token
 * never reaches JavaScript: it is written here by a route handler, read back
 * only on the server, and the browser is given the display fields alone.
 *
 * `lib/server/backend.ts` reads it; `app/api/auth/*` writes and clears it.
 */

import { cookies } from "next/headers";
import type { NextResponse } from "next/server";

export const SESSION_COOKIE = "documind_session";

/**
 * Display identity — name, email, initials — kept beside the token.
 *
 * Separate from the JWT because the JWT carries only `sub`, `role` and `exp`:
 * the person's name exists solely in the Gateway's sign-in response, and the
 * shell needs it to render the account menu. Also httpOnly, and read back
 * through `GET /api/auth/session`, so the browser cannot edit who it claims
 * to be even in a purely cosmetic way.
 */
export const PROFILE_COOKIE = "documind_profile";

/**
 * Matches the Gateway's `JWT_EXPIRATION_HOURS` (24h).
 *
 * Deliberately not longer than the token: a cookie that outlives its JWT
 * turns every request into a 401 the user cannot see the cause of, and with
 * no refresh endpoint there is nothing to renew it with.
 */
const MAX_AGE_SECONDS = 24 * 60 * 60;

/** What the browser is allowed to know about the session. */
export type SessionView = {
  email: string;
  name: string;
  initials: string;
};

/** The bearer token for the current request, or null when signed out. */
export async function readSessionToken(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value ?? null;
}

/** The display identity for the current request, or null when signed out. */
export async function readProfile(): Promise<SessionView | null> {
  const jar = await cookies();
  const raw = jar.get(PROFILE_COOKIE)?.value;
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<SessionView>;
    if (typeof parsed.email !== "string") return null;
    return {
      email: parsed.email,
      name: typeof parsed.name === "string" ? parsed.name : parsed.email,
      initials: typeof parsed.initials === "string" ? parsed.initials : "??",
    };
  } catch {
    // A corrupted cookie is a signed-out user, not a crash.
    return null;
  }
}

/**
 * Attaches the session to a response.
 *
 * `sameSite: "lax"` rather than `strict` so that following a link into the app
 * from elsewhere does not land the user on a signed-out page; the cookie is
 * never read cross-site for a state-changing request because every mutation
 * goes through `fetch` from our own origin.
 */
export function setSessionCookie(
  response: NextResponse,
  token: string,
  profile: SessionView,
): void {
  const options = {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: MAX_AGE_SECONDS,
  } as const;

  response.cookies.set({ name: SESSION_COOKIE, value: token, ...options });
  response.cookies.set({
    name: PROFILE_COOKIE,
    value: JSON.stringify(profile),
    ...options,
  });
}

/** Removes the session — used on sign-out and whenever the Gateway says 401. */
export function clearSessionCookie(response: NextResponse): void {
  const options = {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  } as const;

  response.cookies.set({ name: SESSION_COOKIE, value: "", ...options });
  response.cookies.set({ name: PROFILE_COOKIE, value: "", ...options });
}
