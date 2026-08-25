"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";

export type AsyncStatus = "loading" | "reloading" | "ready" | "error";

export type AsyncState<T> = {
  data: T | null;
  status: AsyncStatus;
  error: ApiError | null;
  /** Re-runs the loader keeping the previous data on screen. */
  reload: () => void;
  /** Re-runs it from scratch, clearing data first. */
  retry: () => void;
  setData: (updater: (prev: T) => T) => void;
};

/**
 * The one place loading / error / retry is modelled. Every screen reads its
 * data through this, so wiring a real endpoint means changing the `load`
 * callback and nothing else.
 */
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [error, setError] = useState<ApiError | null>(null);
  const [nonce, setNonce] = useState(0);
  const hasData = useRef(false);
  const loadRef = useRef(load);

  // Declared before the loader effect so the ref is current when it runs.
  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    const controller = new AbortController();
    let live = true;

    setStatus(hasData.current ? "reloading" : "loading");
    setError(null);

    loadRef
      .current(controller.signal)
      .then((result) => {
        if (!live) return;
        hasData.current = true;
        setDataState(result);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        if (!live || (e instanceof DOMException && e.name === "AbortError")) return;
        setError(
          e instanceof ApiError
            ? e
            : new ApiError("Something went wrong", e instanceof Error ? e.message : "Unknown error"),
        );
        setStatus("error");
      });

    return () => {
      live = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const retry = useCallback(() => {
    hasData.current = false;
    setDataState(null);
    setNonce((n) => n + 1);
  }, []);

  const setData = useCallback((updater: (prev: T) => T) => {
    setDataState((prev) => (prev === null ? prev : updater(prev)));
  }, []);

  return { data, status, error, reload, retry, setData };
}

/** Tracks a one-shot mutation (delete, export, retry) with its own states. */
export type ActionStatus = "idle" | "pending" | "success" | "error";

export function useAction<A extends unknown[], R>(fn: (...args: A) => Promise<R>) {
  const [status, setStatus] = useState<ActionStatus>("idle");
  const [result, setResult] = useState<R | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const run = useCallback(
    async (...args: A) => {
      setStatus("pending");
      setError(null);
      try {
        const r = await fn(...args);
        setResult(r);
        setStatus("success");
        return r;
      } catch (e) {
        setError(e instanceof ApiError ? e : new ApiError("Action failed", String(e)));
        setStatus("error");
        return null;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const reset = useCallback(() => {
    setStatus("idle");
    setResult(null);
    setError(null);
  }, []);

  return { run, reset, status, result, error, pending: status === "pending" };
}

/** Debounces a rapidly-changing value — used by the documents search box. */
export function useDebounced<T>(value: T, ms = 320): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}
