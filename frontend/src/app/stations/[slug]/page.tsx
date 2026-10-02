"use client";

import { BadgeCheck, MapPin } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { PolarScene } from "@/components/art/PolarScene";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { ResourceActions } from "@/components/common/ResourceActions";
import { Badge, DemoBadge, MetaRow } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { PolarMap } from "@/components/maps/PolarMap";
import { coord, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Related, Station, TopicRef } from "@/lib/types";

export default function StationDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: s, error, loading, reload } = useApi<Station & { related: Related; topics: TopicRef[] }>(`/api/stations/${slug}`);
  const [sel, setSel] = useState<string | null>(null);
  if (loading && !s) return <DetailSkeleton />;
  if (error || !s) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/stations", label: "Back to Stations" }} />;
  const view = s.latitude < -40 ? "antarctic" : s.latitude > 50 ? "arctic" : "world";
  return (
    <Container>
      <BackLink href="/stations" label="Back to Research Stations" />
      <div className="relative mb-6 overflow-hidden rounded-3xl bg-night">
        <PolarScene scene={slug === "maitri" ? "station-night" : slug === "himadri" ? "arctic-village" : slug === "himansh" ? "mountains" : "station"} seed={slug} title={s.name} className="absolute inset-0 h-full w-full opacity-70" />
        <div className="absolute inset-0 bg-gradient-to-r from-night via-night/80 to-transparent" />
        <div className="relative max-w-2xl p-6 text-white md:p-10">
          <div className="mb-3 flex flex-wrap gap-2">
            <Badge tone="night" className="border-white/20 bg-white/10">{s.region}</Badge>
            {s.verified ? <Badge tone="teal" icon={<BadgeCheck className="h-3 w-3" />}>Verified station facts</Badge> : <DemoBadge label="Demo location" />}
          </div>
          <h1 className="text-[36px] leading-tight md:text-[48px]">{s.name}</h1>
          <p className="mt-1 text-frost/80">{s.kind}</p>
          <p className="mt-4 text-[15.5px] leading-relaxed text-frost/90">{s.description}</p>
          <div className="mt-5 flex flex-wrap gap-2"><ResourceActions itemType="station" slug={s.slug} label={s.name} citation={`${s.name}, ${s.location_name}. Source: ${s.facts_source}.`} /></div>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          <RelatedKnowledge related={s.related} graph={{ type: "station", slug: s.slug }} />
        </div>
        <aside className="space-y-4">
          <div className="h-[300px]">
            <ErrorBoundary label="map">
              <PolarMap view={view} points={[{ key: s.slug, kind: "station", name: s.name, lat: s.latitude, lon: s.longitude, verified: s.verified }]} selected={sel} onSelect={setSel} />
            </ErrorBoundary>
          </div>
          <SideCard title="Station facts">
            <dl>
              <MetaRow label="Location"><span className="inline-flex items-start gap-1"><MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-mist" />{s.location_name}</span></MetaRow>
              <MetaRow label="Coordinates"><span className="font-mono">{coord(s.latitude, s.longitude)}</span></MetaRow>
              <MetaRow label="Country">{s.country}</MetaRow>
              <MetaRow label="Established">{s.established}</MetaRow>
              <MetaRow label="Status">{s.status}</MetaRow>
              <MetaRow label="Source">{s.facts_source}</MetaRow>
              <MetaRow label="Views">{fmtNum(s.views)}</MetaRow>
            </dl>
          </SideCard>
          <SideCard title="Research themes">
            <div className="flex flex-wrap gap-1.5">
              {s.topics.map((t) => <Link key={t.slug} href={`/explore?topic=${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}
            </div>
            <Link href={`/explore?station=${s.slug}`} className="mt-3 inline-block text-[13px] text-cyan-deep hover:underline">All resources linked to {s.name} →</Link>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
