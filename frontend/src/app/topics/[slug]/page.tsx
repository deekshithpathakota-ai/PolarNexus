"use client";

import { Tag } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ResourceRow } from "@/components/cards/ResourceCard";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { Card, LinkButton } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { OutreachButton } from "@/components/outreach/OutreachButton";
import { KnowledgeTimeline } from "@/components/timeline/KnowledgeTimeline";
import { useApi } from "@/lib/hooks";
import type { Card as CardT } from "@/lib/types";

interface TopicDetail {
  slug: string; name: string; category: string; description: string; total: number;
  counts: Record<string, number>; groups: Record<string, CardT[]>; related_topics: { slug: string; name: string; count: number }[];
  year_span: [number, number] | null;
}
const LABELS: Record<string, string> = {
  document: "Documents", dataset: "Datasets", media: "Media", expedition: "Expeditions", station: "Stations",
  researcher: "Researchers", activity: "Institutional Activities", content: "Published Outreach",
};

export default function TopicPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: t, error, loading, reload } = useApi<TopicDetail>(`/api/topics/${slug}`);
  if (loading && !t) return <DetailSkeleton />;
  if (error || !t) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/explore", label: "Back to Explore" }} />;
  return (
    <Container>
      <BackLink href="/explore" label="Back to Explore" />
      <header className="mb-6">
        <p className="mb-2 inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.18em] text-cyan-deep"><Tag className="h-3.5 w-3.5" aria-hidden /> Topic · {t.category}</p>
        <h1 className="text-[32px] leading-tight text-night md:text-[40px]">{t.name}</h1>
        <p className="mt-2 max-w-3xl text-[15.5px] text-ink-soft">{t.description}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(t.counts).map(([g, n]) => <span key={g} className="rounded-full bg-ice px-3 py-1 text-[12.5px] text-deep"><strong>{n}</strong> {g}</span>)}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <OutreachButton type="topic" slug={t.slug} size="sm" />
          <LinkButton href={`/explore?topic=${t.slug}`} variant="secondary" size="sm">Search within this topic</LinkButton>
          <LinkButton href={`/assistant?q=${encodeURIComponent(`What does the repository say about ${t.name.toLowerCase()}?`)}`} variant="secondary" size="sm">Ask the AI</LinkButton>
        </div>
      </header>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          <Card className="p-5">
            <h2 className="mb-1 text-lg text-night">Knowledge Timeline</h2>
            <p className="mb-4 text-[13px] text-steel">{t.year_span ? `${t.year_span[0]} – ${t.year_span[1]} · ` : ""}every dated record tagged with this topic. Click any item to open it.</p>
            <KnowledgeTimeline scope={{ topic: t.slug }} />
          </Card>
        </div>
        <aside className="space-y-4">
          {Object.entries(t.groups).map(([type, items]) => (
            <SideCard key={type} title={LABELS[type] || type}>
              <div className="-mx-2.5">{items.slice(0, 5).map((i) => <ResourceRow key={`${i.type}${i.id}`} item={i} />)}</div>
            </SideCard>
          ))}
          {t.related_topics.length > 0 && (
            <SideCard title="Related topics">
              <div className="flex flex-wrap gap-1.5">
                {t.related_topics.map((r) => <Link key={r.slug} href={`/topics/${r.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{r.name} <span className="text-mist">{r.count}</span></Link>)}
              </div>
            </SideCard>
          )}
        </aside>
      </div>
    </Container>
  );
}
