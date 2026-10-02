"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Card, CardSkeleton, ErrorState, Skeleton } from "./ui";
import { Container } from "@/components/layout/AppShell";

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="mb-4 inline-flex items-center gap-1.5 text-[13px] text-steel hover:text-cyan-deep">
      <ArrowLeft className="h-3.5 w-3.5" /> {label}
    </Link>
  );
}

export function DetailSkeleton() {
  return (
    <Container>
      <Skeleton className="mb-4 h-4 w-32" />
      <Skeleton className="mb-3 h-9 w-2/3" />
      <Skeleton className="mb-8 h-4 w-1/3" />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <CardSkeleton rows={8} />
        <CardSkeleton rows={6} />
      </div>
    </Container>
  );
}

export function DetailError({ error, onRetry, back }: { error: { message: string; status?: number }; onRetry: () => void; back: { href: string; label: string } }) {
  return (
    <Container>
      <BackLink {...back} />
      <ErrorState error={error.status === 404 ? { ...error, message: "This record isn't in the repository. It may have been archived or the link may be wrong." } : error} onRetry={onRetry} />
    </Container>
  );
}

export function SideCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="p-5">
      <h2 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">{title}</h2>
      {children}
    </Card>
  );
}
