"use client";

import { useMemo } from "react";
import { searchWorkspace, type Simulate } from "@/lib/api";
import { useAsync, useDebounced } from "@/lib/use-async";
import type { SearchHit, SearchResponse } from "@/lib/search/types";

/**
 * The palette's data binding. Deliberately thin: `useAsync` already models
 * loading / reloading / error / retry and aborts the in-flight request when
 * its deps change, so a fast typist cancels their own stale queries for free.
 *
 * Two properties matter for how instant this feels:
 *
 *  - **Previous results stay on screen while the next query runs.** `useAsync`
 *    reports `reloading` rather than clearing `data`, so the list never blinks
 *    to empty between keystrokes.
 *  - **The request is debounced, the input is not.** What the user types
 *    echoes immediately; only the query behind it waits.
 */

/** Short enough to feel live, long enough that a word isn't four queries. */
const DEBOUNCE_MS = 130;

export type SearchState = {
  /** The response currently rendered — may be for a slightly older query. */
  data: SearchResponse | null;
  /** Every hit, flattened in visual order, for keyboard traversal. */
  flat: SearchHit[];
  status: "loading" | "reloading" | "ready" | "error";
  error: { title: string; detail: string; code?: string } | null;
  /** True between a keystroke and the query it will fire. */
  typing: boolean;
  retry: () => void;
};

export function useSearch(query: string, simulate: Simulate = "ok"): SearchState {
  const debounced = useDebounced(query, DEBOUNCE_MS);

  const state = useAsync(
    (signal) => searchWorkspace(debounced, { simulate, signal }),
    [debounced, simulate],
  );

  const flat = useMemo(
    () => (state.data ? state.data.groups.flatMap((g) => g.hits) : []),
    [state.data],
  );

  return {
    data: state.data,
    flat,
    status: state.status,
    error: state.error,
    typing: query.trim() !== debounced.trim(),
    retry: state.retry,
  };
}
