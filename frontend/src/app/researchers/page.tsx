"use client";

import Link from "next/link";
import { useState } from "react";
import { CardSkeleton, DemoBadge, ErrorState, PageHeader, Pagination, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useApi, useDebounced } from "@/lib/hooks";
import type { Paged, Researcher } from "@/lib/types";

export default function ResearchersPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, error, loading, reload } = useApi<Paged<Researcher>>("/api/researchers", { q: dq, page, page_size: 12 });
  return (
    <Container>
      <PageHeader eyebrow="People" title="Researchers" description="Researcher profiles linked to their publications, expeditions and datasets.">
        <div className="mt-3"><DemoBadge label="Fictional demo profiles — not real institutional staff" /></div>
      </PageHeader>
      <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Search by name or expertise…" className={`${inputCls} mb-5 max-w-md`} aria-label="Search researchers" />
      {error ? <ErrorState error={error} onRetry={reload} /> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {loading || !data ? Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />) : data.results.map((r) => (
            <Link key={r.slug} href={`/researchers/${r.slug}`} className="flex gap-4 rounded-2xl border border-frost bg-white p-5 shadow-card hover:border-glacier hover:shadow-lift">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan to-teal font-medium text-white">
                {r.name.replace(/^Dr\.\s*/, "").split(" ").map((p) => p[0]).slice(0, 2).join("")}
              </span>
              <span className="min-w-0">
                <span className="block font-display text-[17px] text-night">{r.name}</span>
                <span className="block text-[13px] text-steel">{r.position}</span>
                <span className="mt-2 flex flex-wrap gap-1">{r.expertise.slice(0, 3).map((e) => <span key={e} className="rounded-full bg-ice px-2 py-0.5 text-[11.5px] text-deep">{e}</span>)}</span>
              </span>
            </Link>
          ))}
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} onPage={setPage} />}
    </Container>
  );
}
