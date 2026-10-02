"use client";

import { CircleCheck, Ship } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { ResourceActions } from "@/components/common/ResourceActions";
import { Badge, Card, DemoBadge, MetaRow } from "@/components/common/ui";
import { OutreachButton } from "@/components/outreach/OutreachButton";
import { ProvenancePanel } from "@/components/provenance/Provenance";
import { KnowledgeTimeline } from "@/components/timeline/KnowledgeTimeline";
import { Container } from "@/components/layout/AppShell";
import { coord } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Expedition, Related, TopicRef } from "@/lib/types";

export default function ExpeditionDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: e, error, loading, reload } = useApi<Expedition & { related: Related; topics: TopicRef[] }>(`/api/expeditions/${slug}`);
  if (loading && !e) return <DetailSkeleton />;
  if (error || !e) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/expeditions", label: "Back to Expeditions" }} />;
  return (
    <Container>
      <BackLink href="/expeditions" label="Back to Expedition timeline" />
      <header className="mb-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge tone="amber" icon={<Ship className="h-3 w-3" />}>{e.program} expedition</Badge>
          <span className="font-mono text-[13px] text-steel">{e.season}</span>
          {e.is_demo ? <DemoBadge label="Demonstration record" /> : <Badge tone="teal">Published facts only</Badge>}
        </div>
        <h1 className="text-[30px] leading-tight text-night md:text-[40px]">{e.name}</h1>
        <p className="mt-3 max-w-3xl text-[16px] leading-relaxed text-ink-soft">{e.objective}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          <OutreachButton type="expedition" slug={e.slug} size="sm" />
          <ResourceActions itemType="expedition" slug={e.slug} label={e.name} />
        </div>
      </header>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6">
          <Card className="p-6">
            <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Highlights</h2>
            <ul className="space-y-2.5">
              {e.highlights.map((h) => <li key={h} className="flex gap-2.5 text-[15px] text-ink"><CircleCheck className="mt-0.5 h-4.5 w-4.5 shrink-0 text-teal" /> {h}</li>)}
            </ul>
            {e.verified_note && <p className="mt-4 rounded-lg bg-snow p-3 text-[12.5px] text-steel">Source note: {e.verified_note}</p>}
          </Card>
          <RelatedKnowledge related={e.related} graph={{ type: "expedition", slug: e.slug }} />
          <Card className="p-5">
            <h2 className="mb-3 text-lg text-night">Knowledge Timeline</h2>
            <KnowledgeTimeline scope={{ expedition: e.slug }} maxItems={12} />
          </Card>
        </div>
        <aside className="space-y-4">
          <ProvenancePanel p={e.provenance} />
          <SideCard title="Expedition record">
            <dl>
              <MetaRow label="Programme">{e.program}</MetaRow>
              <MetaRow label="Season">{e.season}</MetaRow>
              <MetaRow label="Region">{e.region}</MetaRow>
              <MetaRow label="Leader">{e.leader}</MetaRow>
              <MetaRow label="Vessel">{e.vessel}</MetaRow>
              <MetaRow label="Participants">{e.participants}{!e.is_demo ? " (illustrative)" : ""}</MetaRow>
              {e.latitude != null && e.longitude != null && <MetaRow label="Area">{coord(e.latitude, e.longitude)}</MetaRow>}
            </dl>
          </SideCard>
          <SideCard title="Research themes">
            <div className="flex flex-wrap gap-1.5">
              {(e.topics.length ? e.topics : []).map((t) => <Link key={t.slug} href={`/topics/${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}
            </div>
            <Link href={`/explore?expedition=${e.slug}`} className="mt-3 inline-block text-[13px] text-cyan-deep hover:underline">All resources from this expedition →</Link>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
