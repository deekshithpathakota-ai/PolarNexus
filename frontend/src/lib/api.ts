"use client";

// Thin, typed fetch wrapper. Requests go to same-origin /api/* (proxied to FastAPI by next.config.ts)
// unless NEXT_PUBLIC_API_URL is set, in which case the browser calls the backend directly (CORS enabled).
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const TOKEN_KEY = "polarnexus.token";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — session lasts for this page only */
  }
  memoryToken = token;
}

let memoryToken: string | null = null;

export type Query = Record<string, string | number | boolean | null | undefined | (string | number)[]>;

export function qs(params: Query): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, String(x)));
    else sp.append(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export async function api<T>(path: string, init: RequestInit & { query?: Query; timeoutMs?: number } = {}): Promise<T> {
  const { query, timeoutMs = 30000, ...rest } = init;
  const headers = new Headers(rest.headers);
  const token = getToken() || memoryToken;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  // Marks requests from this app. The API requires it for state-changing calls authenticated only by the HttpOnly
  // session cookie (a cross-site form cannot set custom headers — CSRF protection).
  headers.set("X-PolarNexus-Client", "web");
  if (rest.body && !(rest.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}${query ? qs(query) : ""}`, {
      ...rest,
      headers,
      credentials: API_BASE ? "include" : "same-origin",
      signal: rest.signal ?? ctrl.signal,
    });
  } catch (e) {
    clearTimeout(timer);
    if ((e as Error).name === "AbortError") throw new ApiError("The request took too long. Please try again.", 408);
    throw new ApiError("Unable to reach the PolarNexus service. Check your connection and try again.", 0);
  }
  clearTimeout(timer);
  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail = (data && typeof data === "object" && "detail" in data ? (data as { detail: unknown }).detail : null) as unknown;
    const msg = typeof detail === "string" ? detail : res.status >= 500 ? "Something went wrong on the server." : `Request failed (${res.status}).`;
    if (res.status === 401 && token) {
      setToken(null);
      if (typeof window !== "undefined") window.dispatchEvent(new Event("polarnexus:auth-expired"));
    }
    throw new ApiError(msg, res.status);
  }
  return data as T;
}

export const post = <T,>(path: string, body?: unknown, init: RequestInit = {}) =>
  api<T>(path, { ...init, method: "POST", body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined });
export const put = <T,>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T,>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });

export function downloadUrl(path: string) {
  return `${API_BASE}${path}`;
}
