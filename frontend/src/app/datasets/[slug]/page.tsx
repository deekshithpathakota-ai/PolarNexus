"use client";

import { MapPin } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { DatasetExplorer } from "@/components/charts/DatasetExplorer";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { ResourceActions } from "@/components/common/ResourceActions";
import { Card, DemoBadge, MetaRow } from "@/components/common/ui";
import { OutreachButton } from "@/components/outreach/OutreachButton";
import { ProvenancePanel, VerificationBadge } from "@/components/provenance/Provenance";
import { ScientificTrust } from "@/components/provenance/Trust";
import { StoryButton } from "@/components/stories/StoryButton";
import { DatasetQuality } from "@/components/datasets/DatasetQuality";
import { Container } from "@/components/layout/AppShell";
import { fmtDate, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { DatasetDetail } from "@/lib/types";

export default function DatasetPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: ds, error, loading, reload } = useApi<DatasetDetail>(`/api/datasets/${slug}`);
  if (loading && !ds) return <DetailSkeleton />;
  if (error || !ds) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/datasets", label: "Back to Datasets" }} />;
  return (
    <Container>
      <BackLink href="/datasets" label="Back to Datasets" />
      <header className="mb-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <TypeBadge type="dataset" kind={ds.data_type} />
          <span className="inline-flex items-center gap-1 text-[13px] text-steel"><MapPin className="h-3.5 w-3.5" /> {ds.region}</span>
          {ds.provenance?.verification_status === "synthetic_demo" || (!ds.provenance && ds.is_demo) ? (
            <DemoBadge label="Synthetic demonstration values" />
          ) : (
            ds.provenance && <VerificationBadge status={ds.provenance.verification_status} label={ds.provenance.verification_label} official={ds.provenance.official} />
          )}
        </div>
        <h1 className="text-[30px] leading-tight text-night md:text-[38px]">{ds.title}</h1>
        <p className="mt-3 max-w-3xl text-[15.5px] leading-relaxed text-ink-soft">{ds.description}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          <ResourceActions itemType="dataset" slug={ds.slug} label={ds.title} download={`/api/datasets/${ds.slug}/download`}
            citation={`${ds.source} (${ds.year}). ${ds.title} [${ds.format}]. ${ds.license}. PolarNexus record /datasets/${ds.slug}.`} />
          <OutreachButton type="dataset" slug={ds.slug} size="sm" />
          <StoryButton type="dataset" slug={ds.slug} />
        </div>
      </header>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6">
          <Card className="p-5">
            <ErrorBoundary label="dataset explorer">
              <DatasetExplorer ds={ds} />
            </ErrorBoundary>
          </Card>
          {(ds.quality_report?.issues || ds.columns_schema?.length) ? <DatasetQuality ds={ds} /> : null}
          <RelatedKnowledge related={ds.related} graph={{ type: "dataset", slug: ds.slug }} />
        </div>
        <aside className="space-y-4">
          <ProvenancePanel p={ds.provenance} />
          <SideCard title="Dataset metadata">
            <dl>
              <MetaRow label="Temporal">{fmtDate(ds.temporal_start)} – {fmtDate(ds.temporal_end)}</MetaRow>
              <MetaRow label="Spatial">{ds.spatial_coverage}</MetaRow>
              <MetaRow label="Records">{fmtNum(ds.record_count)}</MetaRow>
              <MetaRow label="Format">{ds.format}</MetaRow>
              <MetaRow label="Size">{ds.size_label}</MetaRow>
              <MetaRow label="License">{ds.license}</MetaRow>
              <MetaRow label="Source">{ds.source}</MetaRow>
              {ds.creator && <MetaRow label="Creator">{ds.creator}</MetaRow>}
              {ds.source_url && <MetaRow label="Original file"><a href={ds.source_url} target="_blank" rel="noopener noreferrer" className="break-all text-cyan-deep hover:underline">{ds.source_url.replace(/^https?:\/\//, "")}</a></MetaRow>}
              <MetaRow label="DOI">{ds.doi ? <a className="text-cyan-deep hover:underline" href={`https://doi.org/${ds.doi}`} target="_blank" rel="noopener noreferrer">{ds.doi}</a> : <span className="italic text-mist">Not recorded</span>}</MetaRow>
              <MetaRow label="Updated">{fmtDate(ds.updated_at)}</MetaRow>
            </dl>
          </SideCard>
          <ScientificTrust type="dataset" slug={ds.slug} />
          {ds.quality && (
            <SideCard title="Variables, units & completeness">
              <ul className="space-y-1.5">
                {ds.quality.variables.map((v) => (
                  <li key={v.name} className="text-[13px]">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="font-mono text-[12px] text-night">{v.name}</span>
                      <span className="text-[11.5px] text-steel">{v.unit || "—"}</span>
                    </div>
                    {v.completeness !== null && (
                      <div className="mt-0.5 flex items-center gap-2">
                        <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-ice" aria-hidden>
                          <span className="block h-full rounded-full bg-teal" style={{ width: `${Math.round(v.completeness * 100)}%` }} />
                        </span>
                        <span className="w-10 text-right font-mono text-[10.5px] text-steel">{Math.round(v.completeness * 100)}%</span>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[11.5px] text-steel">
                {ds.quality.georeferenced !== null && <>Georeferenced records: {Math.round(ds.quality.georeferenced * 100)}%. </>}
                {ds.quality.note}
              </p>
            </SideCard>
          )}
          <SideCard title="Topics">
            <div className="flex flex-wrap gap-1.5">
              {ds.topics.map((t) => <Link key={t.slug} href={`/topics/${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}
            </div>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
