"use client";

import { Lock } from "lucide-react";
import type { ReactNode } from "react";
import { Container } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { LinkButton, Spinner } from "./ui";

/** Client-side route guard. The backend enforces the same permissions on every API call. */
export function RequireAuth({ permission, children, title }: { permission?: string; children: ReactNode; title?: string }) {
  const { user, ready, can } = useAuth();
  if (!ready)
    return (
      <Container>
        <Spinner />
      </Container>
    );
  if (!user || (permission && !can(permission)))
    return (
      <Container>
        <div className="mx-auto max-w-lg rounded-2xl border border-frost bg-white p-8 text-center shadow-card">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-ice text-cyan-deep">
            <Lock className="h-5 w-5" />
          </div>
          <h1 className="text-2xl text-night">{title || "Restricted area"}</h1>
          <p className="mt-2 text-[14px] text-ink-soft">
            {user
              ? `Your role (${user.role_label}) doesn't include access to this area. Switch to a role with the right permissions.`
              : "Sign in with a professional account to continue. Demo accounts are available for every role."}
          </p>
          <LinkButton href={`/login?next=${encodeURIComponent(typeof window !== "undefined" ? window.location.pathname + window.location.search : "/")}`} className="mt-5">
            {user ? "Switch account" : "Sign in"}
          </LinkButton>
        </div>
      </Container>
    );
  return <>{children}</>;
}
