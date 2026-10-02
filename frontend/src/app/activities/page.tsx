"use client";

import { SlidersHorizontal, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ActivityCard } from "@/components/cards/ActivityCard";
import { Button, CardSkeleton, Chip, DemoBadge, EmptyState, ErrorState, Field, Modal, PageHeader, Pagination, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Activity } from "@/lib/types";

interface ListResponse {
  total: number; page: number; pages: number; results: Activity[];
  facets: { activity_types: Record<string, number>; organisations: Record<string, number>; years: Record<string, number> };
  type_labels: Record<string, string>;
}
const VERIFICATION = ["Verified", "Uploaded", "Pending", "Demo"];

function Activities() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { can } = useAuth();
  const [open, setOpen] = useState(false);
  const get = (k: string) => sp.get(k) || "";
  const set = (u: Record<string, string | null>) => {
    const next = new URLSearchParams(sp.toString());
    Object.entries(u).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!("page" in u)) next.delete("page");
    router.push(`${pathname}?${next.toString()}`, { scroll: false });
  };
  const q = get("q"), type = get("activity_type"), year = get("year"), org = get("organisation"), loc = get("location");
  const topic = get("topic"), ver = get("verification"), status = get("status"), sort = get("sort") || "newest", page = Number(get("page") || 1);
  const { data, error, loading, reload } = useApi<ListResponse>("/api/activities", {
    q, activity_type: type, year, organisation: org, location: loc, topic, verification: ver, status, sort, page, page_size: 9,
  });
  const topics = useApi<{ results: { slug: string; name: string; count: number }[] }>("/api/topics");
  const [qDraft, setQDraft] = useState(q);
  const chips = [
    type && { label: data?.type_labels[type] || type, clear: () => set({ activity_type: null }) },
    year && { label: `Year ${year}`, clear: () => set({ year: null }) },
    org && { label: org, clear: () => set({ organisation: null }) },
    loc && { label: `Location: ${loc}`, clear: () => set({ location: null }) },
    topic && { label: topics.data?.results.find((t) => t.slug === topic)?.name || topic, clear: () => set({ topic: null }) },
    ver && { label: ver, clear: () => set({ verification: null }) },
    status && { label: status, clear: () => set({ status: null }) },
  ].filter(Boolean) as { label: string; clear: () => void }[];

  const filters = (
    <div className="space-y-4">
      <Field label="Activity type">
        <select className={inputCls} value={type} onChange={(e) => set({ activity_type: e.target.value || null })}>
          <option value="">All types</option>
          {Object.entries(data?.facets.activity_types || {}).map(([k, n]) => <option key={k} value={k}>{data?.type_labels[k] || k} ({n})</option>)}
        </select>
      </Field>
      <Field label="Year">
        <select className={inputCls} value={year} onChange={(e) => set({ year: e.target.value || null })}>
          <option value="">Any year</option>
          {Object.entries(data?.facets.years || {}).sort((a, b) => Number(b[0]) - Number(a[0])).map(([y, n]) => <option key={y} value={y}>{y} ({n})</option>)}
        </select>
      </Field>
      <Field label="Organisation">
        <select className={inputCls} value={org} onChange={(e) => set({ organisation: e.target.value || null })}>
          <option value="">Any organisation</option>
          {Object.keys(data?.facets.organisations || {}).map((o) => <option key={o}>{o}</option>)}
        </select>
      </Field>
      <Field label="Location">
        <input className={inputCls} defaultValue={loc} key={`loc${loc}`} placeholder="e.g. Goa, Online, Maitri"
          onBlur={(e) => e.target.value !== loc && set({ location: e.target.value || null })}
          onKeyDown={(e) => e.key === "Enter" && set({ location: (e.target as HTMLInputElement).value || null })} />
      </Field>
      <Field label="Topic">
        <select className={inputCls} value={topic} onChange={(e) => set({ topic: e.target.value || null })}>
          <option value="">Any topic</option>
          {topics.data?.results.filter((t) => t.count).map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
        </select>
      </Field>
      <Field label="Verification status">
        <select className={inputCls} value={ver} onChange={(e) => set({ verification: e.target.value || null })}>
          <option value="">Any</option>
          {VERIFICATION.map((v) => <option key={v}>{v}</option>)}
        </select>
      </Field>
      <Field label="Status">
        <select className={inputCls} value={status} onChange={(e) => set({ status: e.target.value || null })}>
          <option value="">Any</option><option value="upcoming">Upcoming</option><option value="completed">Completed</option>
          {can("manage_repository") && <option value="archived">Archived</option>}
        </select>
      </Field>
    </div>
  );

  return (
    <Container>
      <PageHeader
        eyebrow="Institutional activities"
        title="Workshops, Outreach & Institutional Events"
        description="Seminars, school outreach, exhibitions, expedition briefings, announcements and achievements — each connected to the research, expeditions, stations, people and media behind it."
        actions={can("manage_repository") ? <Button onClick={() => router.push("/admin/activities")}>Manage activities</Button> : undefined}
      >
        <div className="mt-3"><DemoBadge label="Activities in this prototype are demonstration records" /></div>
      </PageHeader>
      <form className="mb-4 flex gap-2" role="search" onSubmit={(e) => { e.preventDefault(); set({ q: qDraft.trim() || null }); }}>
        <label htmlFor="act-q" className="sr-only">Search activities</label>
        <input id="act-q" className={inputCls} value={qDraft} onChange={(e) => setQDraft(e.target.value)} placeholder="Search activities, organisers, venues…" />
        <Button type="submit">Search</Button>
      </form>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {chips.map((c) => <Chip key={c.label} active onRemove={c.clear}>{c.label}</Chip>)}
        {chips.length > 0 && <button className="text-[13px] text-cyan-deep hover:underline" onClick={() => set({ activity_type: null, year: null, organisation: null, location: null, topic: null, verification: null, status: null })}>Clear all</button>}
        <div className="ml-auto flex items-center gap-2">
          <label htmlFor="act-sort" className="sr-only">Sort</label>
          <select id="act-sort" value={sort} onChange={(e) => set({ sort: e.target.value })} className="h-9 rounded-lg border border-frost bg-white px-2.5 text-[13px]">
            <option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="upcoming">Upcoming first</option>
            <option value="alphabetical">Alphabetical</option><option value="views">Most viewed</option>
          </select>
          <Button variant="secondary" size="sm" className="lg:hidden" onClick={() => setOpen(true)} icon={<SlidersHorizontal className="h-3.5 w-3.5" />}>Filters{chips.length ? ` (${chips.length})` : ""}</Button>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[250px_minmax(0,1fr)]">
        <aside className="hidden lg:block"><div className="sticky top-20 rounded-2xl border border-frost bg-white p-4 shadow-card">{filters}</div></aside>
        <section aria-live="polite" aria-busy={loading}>
          {data && <p className="mb-3 text-[13px] text-steel"><strong className="text-night">{fmtNum(data.total)}</strong> {data.total === 1 ? "activity" : "activities"}</p>}
          {error ? <ErrorState error={error} onRetry={reload} />
            : loading && !data ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((i) => <CardSkeleton key={i} />)}</div>
            : !data?.results.length ? <EmptyState title="No activities found" body="Try removing a filter." action={chips.length ? <Button variant="secondary" onClick={() => set({ activity_type: null, year: null, organisation: null, location: null, topic: null, verification: null, status: null })}>Clear filters</Button> : undefined} />
            : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{data.results.map((a) => <ActivityCard key={a.id} a={a} />)}</div>}
          {data && <Pagination page={data.page} pages={data.pages} onPage={(p) => set({ page: String(p) })} />}
        </section>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title="Filter activities">
        {filters}
        <Button className="mt-4 w-full" onClick={() => setOpen(false)} icon={<X className="h-4 w-4" />}>Show {data ? fmtNum(data.total) : ""} activities</Button>
      </Modal>
    </Container>
  );
}

export default function Page() {
  return <Suspense><Activities /></Suspense>;
}
