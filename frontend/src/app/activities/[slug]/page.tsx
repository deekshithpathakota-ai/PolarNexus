"use client";

import { Building, CalendarDays, CircleCheck, MapPin, Users } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { PolarScene } from "@/components/art/PolarScene";
import { activityWhen } from "@/components/cards/ActivityCard";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { Badge, Card, DemoBadge, MetaRow } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { OutreachButton } from "@/components/outreach/OutreachButton";
import { ProvenancePanel, VerificationBadge } from "@/components/provenance/Provenance";
import { coord, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Activity, Related, TopicRef } from "@/lib/types";

export default function ActivityDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: a, error, loading, reload } = useApi<Activity & { related: Related; topics: TopicRef[] }>(`/api/activities/${slug}`);
  if (loading && !a) return <DetailSkeleton />;
  if (error || !a) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/activities", label: "Back to Activities" }} />;
  return (
    <Container>
      <BackLink href="/activities" label="Back to Institutional Activities" />
      <div className="relative mb-6 overflow-hidden rounded-3xl bg-night">
        <PolarScene scene={a.cover_scene} seed={a.slug} title={a.title} className="absolute inset-0 h-full w-full opacity-60" />
        <div className="absolute inset-0 bg-gradient-to-r from-night via-night/85 to-night/30" />
        <div className="relative max-w-3xl p-6 text-white md:p-10">
          <div className="mb-3 flex flex-wrap gap-2">
            <Badge tone="night" className="border-white/20 bg-white/10">{a.activity_type_label}</Badge>
            {a.status === "upcoming" && <Badge tone="teal">Upcoming</Badge>}
            {a.is_demo ? <DemoBadge label="Demonstration record" /> : <VerificationBadge status={a.verification} label={a.verification_label} />}
          </div>
          <h1 className="text-[30px] leading-tight md:text-[42px]">{a.title}</h1>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[14px] text-frost/90">
            <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-4 w-4" aria-hidden /> {activityWhen(a)}</span>
            <span className="inline-flex items-center gap-1.5"><MapPin className="h-4 w-4" aria-hidden /> {a.location}</span>
            <span className="inline-flex items-center gap-1.5"><Building className="h-4 w-4" aria-hidden /> {a.organisation}</span>
          </div>
          <div className="mt-5"><OutreachButton type="activity" slug={a.slug} variant="primary" size="sm" /></div>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          <Card className="p-6">
            <h2 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">About this activity</h2>
            <p className="text-[16px] leading-[1.75] text-ink">{a.description}</p>
            {a.outcomes.length > 0 && (
              <>
                <h3 className="mb-2 mt-5 font-mono text-[11px] uppercase tracking-wider text-steel">Outcomes</h3>
                <ul className="space-y-2">
                  {a.outcomes.map((o) => <li key={o} className="flex gap-2.5 text-[15px] text-ink"><CircleCheck className="mt-0.5 h-4.5 w-4.5 shrink-0 text-teal" aria-hidden /> {o}</li>)}
                </ul>
              </>
            )}
          </Card>
          {a.related && <RelatedKnowledge related={a.related} graph={{ type: "activity", slug: a.slug }} />}
        </div>
        <aside className="space-y-4">
          <ProvenancePanel p={a.provenance} />
          <SideCard title="Activity details">
            <dl>
              <MetaRow label="Type">{a.activity_type_label}</MetaRow>
              <MetaRow label="When">{activityWhen(a)}</MetaRow>
              <MetaRow label="Location">{a.location}</MetaRow>
              {a.latitude != null && a.longitude != null && <MetaRow label="Coordinates"><span className="font-mono">{coord(a.latitude, a.longitude)}</span></MetaRow>}
              <MetaRow label="Organisation">{a.organisation}</MetaRow>
              {a.department && <MetaRow label="Department">{a.department}</MetaRow>}
              {a.audience && <MetaRow label="Audience"><span className="inline-flex items-center gap-1"><Users className="h-3.5 w-3.5 text-mist" aria-hidden /> {a.audience}</span></MetaRow>}
              <MetaRow label="Status"><span className="capitalize">{a.status}</span></MetaRow>
              <MetaRow label="Views">{fmtNum(a.views)}</MetaRow>
            </dl>
          </SideCard>
          {(a.topics as TopicRef[] | undefined)?.length ? (
            <SideCard title="Topics">
              <div className="flex flex-wrap gap-1.5">
                {(a.topics as TopicRef[]).map((t) => <Link key={t.slug} href={`/topics/${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}
              </div>
            </SideCard>
          ) : null}
        </aside>
      </div>
    </Container>
  );
}
