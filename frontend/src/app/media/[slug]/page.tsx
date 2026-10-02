"use client";

import { Pause, Play } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { PolarScene } from "@/components/art/PolarScene";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { ResourceActions } from "@/components/common/ResourceActions";
import { DemoBadge, MetaRow } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { MediaItem, Related } from "@/lib/types";

export default function MediaDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: m, error, loading, reload } = useApi<MediaItem & { related: Related }>(`/api/media/${slug}`);
  const [playing, setPlaying] = useState(false);
  if (loading && !m) return <DetailSkeleton />;
  if (error || !m) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/media", label: "Back to Media" }} />;
  const kind = m.media_type === "video" ? "Video" : m.media_type === "infographic" ? "Infographic" : "Image";
  return (
    <Container>
      <BackLink href="/media" label="Back to Media library" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6">
          <figure className="overflow-hidden rounded-2xl border border-frost bg-night shadow-card">
            <div className="relative aspect-[16/10]">
              <PolarScene scene={m.scene} seed={m.slug} title={m.title} className={`h-full w-full ${playing ? "animate-[pulse_6s_ease-in-out_infinite]" : ""}`} />
              {m.media_type === "video" && (
                <button
                  onClick={() => setPlaying((p) => !p)}
                  aria-label={playing ? "Pause preview" : "Play preview"}
                  className="absolute inset-0 m-auto flex h-16 w-16 items-center justify-center rounded-full bg-abyss/70 text-white backdrop-blur transition hover:scale-105"
                >
                  {playing ? <Pause className="h-7 w-7" /> : <Play className="ml-1 h-7 w-7" />}
                </button>
              )}
              {m.media_type === "video" && playing && (
                <p className="absolute inset-x-0 bottom-0 bg-abyss/75 px-4 py-2 text-center text-[12.5px] text-frost">
                  Prototype preview — in production the original footage ({m.duration}) streams from object storage.
                </p>
              )}
            </div>
            <figcaption className="bg-white px-5 py-3 text-[12.5px] text-steel">{m.credit} · {m.license}</figcaption>
          </figure>
          <RelatedKnowledge related={m.related} graph={{ type: "media", slug: m.slug }} />
        </div>
        <aside className="space-y-4">
          <div>
            <div className="mb-2 flex flex-wrap gap-2"><TypeBadge type="media" kind={kind} /><DemoBadge label="Prototype artwork" /></div>
            <h1 className="text-[28px] leading-tight text-night">{m.title}</h1>
            <p className="mt-2 text-[15px] leading-relaxed text-ink-soft">{m.description}</p>
            <div className="mt-4 flex flex-wrap gap-2"><ResourceActions itemType="media" slug={m.slug} label={m.title} citation={`${m.title} (${m.year}). ${m.credit}. ${m.license}.`} /></div>
          </div>
          <SideCard title="Details">
            <dl>
              <MetaRow label="Category">{m.category}</MetaRow>
              <MetaRow label="Region">{m.region}</MetaRow>
              <MetaRow label="Year">{m.year}</MetaRow>
              {m.duration && <MetaRow label="Duration">{m.duration}</MetaRow>}
              <MetaRow label="Source">{m.credit}</MetaRow>
              <MetaRow label="License">{m.license}</MetaRow>
              <MetaRow label="Views">{fmtNum(m.views)}</MetaRow>
            </dl>
          </SideCard>
          <SideCard title="Tags & topics">
            <div className="flex flex-wrap gap-1.5">
              {m.tags.map((t) => <Link key={t} href={`/media?q=${encodeURIComponent(t)}`} className="rounded-full bg-snow px-2.5 py-1 text-[12.5px] text-ink-soft ring-1 ring-frost hover:bg-ice">#{t}</Link>)}
              {(m.topics || []).map((t) => <Link key={t.slug} href={`/explore?topic=${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}
            </div>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
