"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type Query } from "./api";

export interface Loadable<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
  setData: (d: T | null) => void;
}

/** Fetch JSON on mount / when key changes. Never throws — exposes error for <ErrorState>. */
export function useApi<T>(path: string | null, query?: Query, deps: unknown[] = []): Loadable<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const [tick, setTick] = useState(0);
  const key = JSON.stringify([path, query, tick, ...deps]);
  const seq = useRef(0);

  useEffect(() => {
    if (!path) {
      setLoading(false);
      return;
    }
    const mine = ++seq.current;
    setLoading(true);
    setError(null);
    api<T>(path, { query })
      .then((d) => {
        if (mine === seq.current) setData(d);
      })
      .catch((e: ApiError) => {
        if (mine === seq.current) setError(e instanceof ApiError ? e : new ApiError(String(e), 0));
      })
      .finally(() => {
        if (mine === seq.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}

export function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function useLocalList(key: string, max = 8) {
  const [items, setItems] = useState<string[]>([]);
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw) setItems(JSON.parse(raw));
    } catch {
      /* ignore */
    }
  }, [key]);
  const push = useCallback(
    (v: string) => {
      setItems((prev) => {
        const next = [v, ...prev.filter((x) => x.toLowerCase() !== v.toLowerCase())].slice(0, max);
        try {
          window.localStorage.setItem(key, JSON.stringify(next));
        } catch {
          /* ignore */
        }
        return next;
      });
    },
    [key, max],
  );
  const clear = useCallback(() => {
    setItems([]);
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  }, [key]);
  return { items, push, clear };
}
