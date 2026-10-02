"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { Card, DemoBadge, MetaRow } from "@/components/common/ui";
import { OutreachButton } from "@/components/outreach/OutreachButton";
import { ProvenancePanel } from "@/components/provenance/Provenance";
import { KnowledgeTimeline } from "@/components/timeline/KnowledgeTimeline";
import { Container } from "@/components/layout/AppShell";
import { useApi } from "@/lib/hooks";
import type { Related, Researcher, TopicRef } from "@/lib/types";

export default function ResearcherDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: r, error, loading, reload } = useApi<Researcher & { related: Related; topics: TopicRef[] }>(`/api/researchers/${slug}`);
  if (loading && !r) return <DetailSkeleton />;
  if (error || !r) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/researchers", label: "Back to Researchers" }} />;
  const g = r.related.groups;
  return (
    <Container>
      <BackLink href="/researchers" label="Back to Researchers" />
      <header className="mb-6 flex flex-wrap items-center gap-5">
        <span className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-cyan to-teal text-2xl font-medium text-white">
          {r.name.replace(/^Dr\.\s*/, "").split(" ").map((p) => p[0]).slice(0, 2).join("")}
        </span>
        <div>
          <DemoBadge label="Fictional demo profile" />
          <h1 className="mt-2 text-[32px] leading-tight text-night">{r.name}</h1>
          <p className="text-ink-soft">{r.position} · {r.institution}</p>
        </div>
        <div className="sm:ml-auto"><OutreachButton type="researcher" slug={r.slug} size="sm" /></div>
      </header>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6">
          <RelatedKnowledge related={r.related} graph={{ type: "researcher", slug: r.slug }} />
          <Card className="p-5">
            <h2 className="mb-3 text-lg text-night">Research Timeline</h2>
            <KnowledgeTimeline scope={{ researcher: r.slug }} maxItems={12} />
          </Card>
        </div>
        <aside className="space-y-4">
          <ProvenancePanel p={r.provenance} compact />
          <SideCard title="Profile">
            <p className="mb-3 text-[14px] text-ink-soft">{r.bio}</p>
            <dl>
              <MetaRow label="Publications">{g.document?.length || 0}</MetaRow>
              <MetaRow label="Expeditions">{g.expedition?.length || 0}</MetaRow>
              <MetaRow label="Datasets">{g.dataset?.length || 0}</MetaRow>
            </dl>
          </SideCard>
          <SideCard title="Expertise">
            <div className="flex flex-wrap gap-1.5">{r.topics.map((t) => <Link key={t.slug} href={`/topics/${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}</div>
            <Link href={`/explore?researcher=${r.slug}`} className="mt-3 inline-block text-[13px] text-cyan-deep hover:underline">All linked resources →</Link>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
