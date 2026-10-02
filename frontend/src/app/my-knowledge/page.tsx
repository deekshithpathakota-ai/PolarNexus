"use client";

import { Bookmark, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Card, EmptyState, ErrorState, PageHeader, Skeleton } from "@/components/common/ui";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { Container } from "@/components/layout/AppShell";
import { del, qs } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Saved { id: number; item_type: string; item_slug: string; label: string; query: Record<string, string | string[]>; at: string }
const URLS: Record<string, string> = { document: "/resources", dataset: "/datasets", media: "/media", expedition: "/expeditions", station: "/stations", researcher: "/researchers" };

function MyKnowledge() {
  const { data, error, loading, reload, setData } = useApi<{ results: Saved[] }>("/api/saved");
  const history = useApi<{ results: { query: string; mode: string; results: number; at: string }[] }>("/api/search/history");
  const toast = useToast();
  const remove = async (id: number) => {
    try {
      await del(`/api/saved/${id}`);
      setData(data ? { results: data.results.filter((s) => s.id !== id) } : null);
    } catch (e) {
      toast("error", "Could not remove", (e as Error).message);
    }
  };
  const items = data?.results.filter((s) => s.item_type !== "search") || [];
  const searches = data?.results.filter((s) => s.item_type === "search") || [];
  return (
    <Container className="max-w-[1100px]">
      <PageHeader eyebrow="Personal" title="My Knowledge" description="Your saved documents, datasets, media and searches." />
      {error ? <ErrorState error={error} onRetry={reload} /> : loading ? <Skeleton className="h-64 w-full rounded-2xl" /> : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <Card className="p-5">
            <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Saved resources · {items.length}</h2>
            {items.length === 0 ? <EmptyState icon={<Bookmark className="h-6 w-6" />} title="Nothing saved yet" body="Use the Save button on any resource page." /> : (
              <ul className="divide-y divide-frost">
                {items.map((s) => (
                  <li key={s.id} className="flex items-center gap-3 py-3">
                    <TypeBadge type={s.item_type} />
                    <Link href={`${URLS[s.item_type]}/${s.item_slug}`} className="min-w-0 flex-1 truncate text-[14px] text-night hover:text-cyan-deep">{s.label}</Link>
                    <span className="hidden text-[11.5px] text-mist sm:block">{timeAgo(s.at)}</span>
                    <button aria-label={`Remove ${s.label}`} onClick={() => remove(s.id)} className="rounded p-1.5 text-mist hover:bg-ice hover:text-coral"><Trash2 className="h-4 w-4" /></button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <div className="space-y-4">
            <Card className="p-5">
              <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Saved searches</h2>
              {searches.length === 0 ? <p className="text-[13px] text-steel">Use “Save search” on the Explore page.</p> : (
                <ul className="space-y-1.5">
                  {searches.map((s) => (
                    <li key={s.id} className="flex items-center gap-2">
                      <Link href={`/explore${qs(s.query as Record<string, string>)}`} className="flex min-w-0 flex-1 items-center gap-2 text-[13.5px] text-night hover:text-cyan-deep"><Search className="h-3.5 w-3.5 shrink-0 text-mist" /><span className="truncate">{s.label}</span></Link>
                      <button aria-label="Remove saved search" onClick={() => remove(s.id)} className="text-mist hover:text-coral"><Trash2 className="h-3.5 w-3.5" /></button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card className="p-5">
              <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Search history</h2>
              {!history.data?.results.length ? <p className="text-[13px] text-steel">Your searches will appear here.</p> : (
                <ul className="space-y-1.5">
                  {history.data.results.map((h) => (
                    <li key={h.query}><Link href={`/explore?q=${encodeURIComponent(h.query)}&mode=${h.mode}`} className="flex justify-between gap-2 text-[13px] text-ink-soft hover:text-cyan-deep"><span className="truncate">{h.query}</span><span className="shrink-0 text-mist">{h.results}</span></Link></li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      )}
    </Container>
  );
}

export default function Page() {
  return <RequireAuth title="My Knowledge"><MyKnowledge /></RequireAuth>;
}
