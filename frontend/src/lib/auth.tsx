"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, getToken, post, setToken } from "./api";
import type { Role, User } from "./types";

interface AuthState {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  demoLogin: (role: Role) => Promise<User>;
  logout: () => Promise<void>;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

const PUBLIC_PERMS = ["search", "read", "ask_ai"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
    const onExpired = () => setUser(null);
    window.addEventListener("polarnexus:auth-expired", onExpired);
    return () => window.removeEventListener("polarnexus:auth-expired", onExpired);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await post<{ access_token: string; user: User }>("/api/auth/login", { email, password });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const demoLogin = useCallback(async (role: Role) => {
    const res = await post<{ access_token: string; user: User }>("/api/auth/demo-login", { role });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await post("/api/auth/logout");
    } catch {
      /* token may already be invalid */
    }
    setToken(null);
    setUser(null);
  }, []);

  const can = useCallback((p: string) => (user ? user.permissions.includes(p) : PUBLIC_PERMS.includes(p)), [user]);

  const value = useMemo(() => ({ user, ready, login, demoLogin, logout, can }), [user, ready, login, demoLogin, logout, can]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
