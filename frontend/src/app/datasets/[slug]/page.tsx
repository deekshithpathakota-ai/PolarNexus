"use client";

import { MapPin, SquarePen } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { DatasetExplorer } from "@/components/charts/DatasetExplorer";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { ResourceActions } from "@/components/common/ResourceActions";
import { Card, DemoBadge, LinkButton, MetaRow } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { fmtDate, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { DatasetDetail } from "@/lib/types";

export default function DatasetPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: ds, error, loading, reload } = useApi<DatasetDetail>(`/api/datasets/${slug}`);
  const { can } = useAuth();
  if (loading && !ds) return <DetailSkeleton />;
  if (error || !ds) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/datasets", label: "Back to Datasets" }} />;
  return (
    <Container>
      <BackLink href="/datasets" label="Back to Datasets" />
      <header className="mb-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <TypeBadge type="dataset" kind={ds.data_type} />
          <span className="inline-flex items-center gap-1 text-[13px] text-steel"><MapPin className="h-3.5 w-3.5" /> {ds.region}</span>
          <DemoBadge label="Synthetic demonstration values" />
        </div>
        <h1 className="text-[30px] leading-tight text-night md:text-[38px]">{ds.title}</h1>
        <p className="mt-3 max-w-3xl text-[15.5px] leading-relaxed text-ink-soft">{ds.description}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          <ResourceActions itemType="dataset" slug={ds.slug} label={ds.title} download={`/api/datasets/${ds.slug}/download`}
            citation={`${ds.source} (${ds.year}). ${ds.title} [${ds.format}]. ${ds.license}. PolarNexus record /datasets/${ds.slug}.`} />
          {can("generate_content") && <LinkButton href={`/studio?type=dataset&slug=${ds.slug}`} variant="dark" size="sm" icon={<SquarePen className="h-3.5 w-3.5" />}>Create outreach content</LinkButton>}
        </div>
      </header>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6">
          <Card className="p-5">
            <ErrorBoundary label="dataset explorer">
              <DatasetExplorer ds={ds} />
            </ErrorBoundary>
          </Card>
          <RelatedKnowledge related={ds.related} graph={{ type: "dataset", slug: ds.slug }} />
        </div>
        <aside className="space-y-4">
          <SideCard title="Dataset metadata">
            <dl>
              <MetaRow label="Temporal">{fmtDate(ds.temporal_start)} – {fmtDate(ds.temporal_end)}</MetaRow>
              <MetaRow label="Spatial">{ds.spatial_coverage}</MetaRow>
              <MetaRow label="Records">{fmtNum(ds.record_count)}</MetaRow>
              <MetaRow label="Format">{ds.format}</MetaRow>
              <MetaRow label="Size">{ds.size_label}</MetaRow>
              <MetaRow label="License">{ds.license}</MetaRow>
              <MetaRow label="Source">{ds.source}</MetaRow>
              <MetaRow label="Updated">{fmtDate(ds.updated_at)}</MetaRow>
            </dl>
          </SideCard>
          <SideCard title="Topics">
            <div className="flex flex-wrap gap-1.5">
              {ds.topics.map((t) => <Link key={t.slug} href={`/explore?topic=${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}
            </div>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
