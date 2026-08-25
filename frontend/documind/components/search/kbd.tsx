"use client";

import type { ReactNode } from "react";

/** A key cap. Used in the palette footer and on the topbar trigger. */
export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="dm-kbd">{children}</kbd>;
}
