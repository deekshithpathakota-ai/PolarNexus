"use client";

import { ArrowRight, BookOpenText, Search, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { BackLink } from "@/components/common/DetailLayout";
import { Button, Card, ErrorState, Field, PageHeader, Skeleton, inputCls } from "@/components/common/ui";
import { useToast } from "@/components/common/Toast";
import { Container } from "@/components/layout/AppShell";
import { VerificationBadge } from "@/components/provenance/Provenance";
import { ApiError, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi, useDebounced } from "@/lib/hooks";
import type { SearchResponse, Story, VerificationStatus } from "@/lib/types";

interface Item { type: string; id: number; slug: string; title: string; kind: string; role: string; verification: VerificationStatus; verification_label: string; url?: string }

const ROLE_FOR: Record<string, string> = { topic: "Research topic", document: "Research paper", dataset: "Dataset", expedition: "Expedition", station: "Station / location", researcher: "Researcher", activity: "Outreach & activities" };

function Builder() {
  const sp = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { can, ready } = useAuth();
  const type = sp.get("type");
  const slug = sp.get("slug");
  const sug = useApi<{ title: string; items: Item[] }>(type && slug ? "/api/stories/suggest" : null, { seed_type: type || "", seed_slug: slug || "" });
  const [items, setItems] = useState<Item[]>([]);
  const [title, setTitle] = useState("");
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 300);
  const found = useApi<SearchResponse>(dq.trim().length >= 2 ? "/api/search" : null, { q: dq, page_size: 8 });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);

  useEffect(() => {
    if (sug.data) {
      setItems(sug.data.items);
      setTitle(sug.data.title);
    }
  }, [sug.data]);

  useEffect(() => {
    if (ready && !can("generate_content")) router.replace(`/login?next=${encodeURIComponent(`/stories/new${type ? `?type=${type}&slug=${slug}` : ""}`)}`);
  }, [ready, can, router, type, slug]);

  const roles = [...new Set(items.map((i) => i.role))];
  const add = (r: SearchResponse["results"][number]) => {
    if (items.some((i) => i.type === r.type && i.id === r.id) || r.type === "content") return;
    const role = r.type === "media" ? (r.extra?.media_type === "video" ? "Video" : "Photograph") : ROLE_FOR[r.type] || "Related";
    setItems((xs) => [...xs, { type: r.type, id: r.id, slug: r.slug, title: r.title, kind: r.kind, role, verification: r.verification || "unverified", verification_label: r.verification_label || "" }]);
    setQ("");
  };
  const save = async () => {
    setBusy(true);
    setErr(null);
    try {
      const s = await post<Story>("/api/stories", {
        title, seed_type: type || undefined, seed_slug: slug || undefined,
        items: items.map((i) => ({ type: i.type, id: i.id, role: i.role })),
      });
      toast("success", "Research story created", "Summaries were generated from the cited evidence.");
      router.push(`/stories/${s.slug}`);
    } catch (e) {
      setErr(e as ApiError);
      setBusy(false);
    }
  };

  return (
    <Container>
      <BackLink href="/stories" label="Back to Research Stories" />
      <PageHeader eyebrow="Research Story builder" title="Connect a piece of research" description="Start from any record. Connected items come from the knowledge graph — remove what does not belong, or search to add more. Explanations are generated only from cited evidence." />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-4">
          <Card className="p-5">
            <Field label="Story title">
              <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} placeholder="e.g. From satellite records to the classroom" />
            </Field>
          </Card>
          {sug.error ? <ErrorState error={sug.error} onRetry={sug.reload} /> : sug.loading ? <Skeleton className="h-64 w-full" /> : items.length === 0 ? (
            <Card className="p-6 text-center text-[14px] text-steel">Search on the right to add the first record, or open a paper or dataset and choose “Build Research Story”.</Card>
          ) : (
            <ol className="space-y-4" aria-label="Story chain">
              {roles.map((role, ri) => (
                <li key={role}>
                  <p className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-steel">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-night text-[10px] text-white">{ri + 1}</span>{role}
                  </p>
                  <ul className="space-y-2">
                    {items.filter((i) => i.role === role).map((i) => (
                      <li key={`${i.type}${i.id}`} className="flex items-center gap-3 rounded-xl border border-frost bg-white px-3 py-2.5 shadow-card">
                        <TypeBadge type={i.type} kind={i.kind} />
                        <span className="min-w-0 flex-1 truncate text-[14px] text-night">{i.title}</span>
                        <VerificationBadge status={i.verification} label={i.verification_label} className="hidden sm:inline-flex" />
                        <button onClick={() => setItems((xs) => xs.filter((x) => !(x.type === i.type && x.id === i.id)))} aria-label={`Remove ${i.title}`} className="rounded-md p-1 text-mist hover:bg-ice hover:text-coral">
                          <X className="h-4 w-4" />
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          )}
        </div>
        <aside className="space-y-4">
          <Card className="p-5">
            <label className="mb-2 block font-mono text-[11px] uppercase tracking-wider text-steel" htmlFor="story-add">Add a record</label>
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-mist" aria-hidden />
              <input id="story-add" className={`${inputCls} pl-9`} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search papers, datasets, photos…" />
            </div>
            {found.data && dq.length >= 2 && (
              <ul className="mt-2 max-h-80 space-y-1 overflow-auto">
                {found.data.results.filter((r) => r.type !== "content").map((r) => (
                  <li key={`${r.type}${r.id}`}>
                    <button onClick={() => add(r)} className="w-full rounded-lg px-2 py-1.5 text-left text-[13px] hover:bg-ice">
                      <span className="block truncate text-night">{r.title}</span>
                      <span className="text-[11.5px] text-steel">{r.kind} · {r.verification_label}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-5">
            <p className="text-[13px] text-ink-soft">{items.length} records in {roles.length} steps.</p>
            {err && <div className="mt-3"><ErrorState error={err} compact /></div>}
            <Button className="mt-3 w-full" onClick={save} loading={busy} disabled={!items.length || title.trim().length < 3} icon={<BookOpenText className="h-4 w-4" />}>
              Create story <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="mt-2 text-[11.5px] text-steel">Stories start as drafts. An editor publishes them.</p>
          </Card>
        </aside>
      </div>
    </Container>
  );
}

export default function Page() {
  return (
    <Suspense>
      <Builder />
    </Suspense>
  );
}
