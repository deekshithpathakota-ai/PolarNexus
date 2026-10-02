"use client";

import { Accessibility, Captions, ExternalLink, Pause, Play, ScanEye } from "lucide-react";
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
import { ProcessingSteps } from "@/components/media/ProcessingSteps";
import { ProvenancePanel } from "@/components/provenance/Provenance";
import { ScientificTrust } from "@/components/provenance/Trust";
import { StoryButton } from "@/components/stories/StoryButton";
import { coord, fmtBytes, fmtDate, fmtDuration, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { MediaItem, Related } from "@/lib/types";

const EXIF_LABELS: Record<string, string> = {
  camera_make: "Camera make", camera_model: "Camera model", datetime_original: "Captured (EXIF)", exposure_time: "Exposure (s)",
  f_number: "f-number", iso: "ISO", focal_length: "Focal length (mm)", video_codec: "Video codec", audio_codec: "Audio codec",
  container: "Container",
};

export default function MediaDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: m, error, loading, reload } = useApi<MediaItem & { related: Related }>(`/api/media/${slug}`);
  const [playing, setPlaying] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  if (loading && !m) return <DetailSkeleton />;
  if (error || !m) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/media", label: "Back to Media" }} />;
  const kind = m.media_type === "video" ? "Video" : m.media_type === "infographic" ? "Infographic" : "Image";
  const ready = (m.processing_status || "ready") === "ready";
  const real = m.has_file && m.file_url && ready;
  const exifRows = Object.entries(m.exif || {}).filter(([k]) => EXIF_LABELS[k]);
  return (
    <Container>
      <BackLink href="/media" label="Back to Media library" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6">
          <figure className="overflow-hidden rounded-2xl border border-frost bg-night shadow-card">
            <div className="relative aspect-[16/10]">
              {real && m.media_type === "video" ? (
                <video controls preload="metadata" poster={m.thumbnail_url || undefined} className="h-full w-full bg-black object-contain" aria-label={m.alt_text || m.title}>
                  <source src={m.file_url!} type={m.mime_type || undefined} />
                  {m.captions_url && <track kind="captions" src={m.captions_url} srcLang="en" label="English captions" default />}
                  Your browser cannot play this video. <a href={m.file_url!}>Download it</a> instead.
                </video>
              ) : real ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={m.file_url!} alt={m.alt_text || m.description || m.title} className="h-full w-full object-contain" />
              ) : (
                <>
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
                </>
              )}
            </div>
            <figcaption className="bg-white px-5 py-3 text-[12.5px] text-steel">
              {m.caption && m.caption !== m.description && <span className="mb-1 block text-[13px] text-ink-soft">{m.caption}</span>}
              {m.credit} · {m.license}
              {m.source_url && (
                <a href={m.source_url} target="_blank" rel="noopener noreferrer" className="ml-2 inline-flex items-center gap-1 text-cyan-deep hover:underline">
                  Original <ExternalLink className="h-3 w-3" aria-hidden />
                </a>
              )}
            </figcaption>
          </figure>
          {!ready && (
            <SideCard title="Processing">
              <ProcessingSteps status={m.processing_status || "processing"} steps={m.processing_steps || []} error={m.processing_error} />
            </SideCard>
          )}
          {m.transcript && (
            <SideCard title="Transcript">
              <p className="mb-2 flex items-center gap-1.5 text-[12.5px] text-steel">
                <Captions className="h-4 w-4" aria-hidden />
                {m.transcript_source === "uploaded" ? "Transcript supplied by the uploader" : `Generated by speech-to-text (${(m.transcript_source || "").replace("stt:", "")})`} · indexed for search
              </p>
              <p className={`text-[14px] leading-relaxed text-ink-soft ${showTranscript ? "" : "line-clamp-4"}`}>{m.transcript}</p>
              <button className="mt-2 text-[13px] text-cyan-deep hover:underline" onClick={() => setShowTranscript((s) => !s)} aria-expanded={showTranscript}>
                {showTranscript ? "Show less" : "Show full transcript"}
              </button>
            </SideCard>
          )}
          <SideCard title="Accessibility">
            <dl>
              <MetaRow label="Alt text">{m.alt_text ? m.alt_text : <span className="italic text-mist">Not provided — the description is used instead</span>}</MetaRow>
              {m.media_type === "video" && (
                <>
                  <MetaRow label="Captions">{m.captions_url ? "WebVTT caption track available in the player" : <span className="italic text-mist">Unavailable for this video</span>}</MetaRow>
                  <MetaRow label="Transcript">{m.transcript ? "Available below" : <span className="italic text-mist">Unavailable for this video</span>}</MetaRow>
                </>
              )}
              {real && (
                <MetaRow label="Visual index">
                  <span className="inline-flex items-center gap-1.5">
                    <ScanEye className="h-3.5 w-3.5 text-cyan-deep" aria-hidden />
                    {m.visual_status === "indexed" ? (m.media_type === "video" ? "Key frames embedded for visual search" : "Embedded for visual search") :
                      m.visual_status === "failed" ? "Visual embedding failed" : "Not visually indexed (visual search unavailable on this server)"}
                  </span>
                </MetaRow>
              )}
              {m.is_demo && <MetaRow label="Note"><span className="inline-flex items-center gap-1.5"><Accessibility className="h-3.5 w-3.5" aria-hidden />Illustrative artwork — described by its title and description.</span></MetaRow>}
            </dl>
          </SideCard>
          <RelatedKnowledge related={m.related} graph={{ type: "media", slug: m.slug }} />
        </div>
        <aside className="space-y-4">
          <div>
            <div className="mb-2 flex flex-wrap gap-2">
              <TypeBadge type="media" kind={kind} />
              {m.is_demo && <DemoBadge label="Prototype artwork" />}
            </div>
            <h1 className="text-[28px] leading-tight text-night">{m.title}</h1>
            <p className="mt-2 text-[15px] leading-relaxed text-ink-soft">{m.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <ResourceActions itemType="media" slug={m.slug} label={m.title} citation={`${m.title} (${m.year}). ${m.credit}. ${m.license}.`} download={real ? m.file_url! : undefined} />
              <StoryButton type="media" slug={m.slug} variant="subtle" />
            </div>
          </div>
          <ProvenancePanel p={m.provenance} compact />
          <ScientificTrust type="media" slug={m.slug} />
          <SideCard title="Details">
            <dl>
              <MetaRow label="Category">{m.category}</MetaRow>
              <MetaRow label="Region">{m.region}</MetaRow>
              <MetaRow label="Year">{m.year}</MetaRow>
              {(m.duration_seconds || m.duration) && <MetaRow label="Duration">{fmtDuration(m.duration_seconds) || m.duration}</MetaRow>}
              {m.width && m.height && <MetaRow label="Dimensions">{m.width} × {m.height} px</MetaRow>}
              {m.filename && <MetaRow label="File">{m.filename} · {m.mime_type} · {fmtBytes(m.size_bytes)}</MetaRow>}
              {m.captured_at && <MetaRow label="Captured">{fmtDate(m.captured_at)}</MetaRow>}
              {m.location && <MetaRow label="Location">{m.location}</MetaRow>}
              {m.latitude != null && m.longitude != null && <MetaRow label="Coordinates"><span className="font-mono">{coord(m.latitude, m.longitude)}</span></MetaRow>}
              {!m.is_demo && m.uploaded_at && <MetaRow label="Uploaded">{fmtDate(m.uploaded_at)}</MetaRow>}
              <MetaRow label="Source">{m.credit}</MetaRow>
              <MetaRow label="License">{m.license}</MetaRow>
              <MetaRow label="Views">{fmtNum(m.views)}</MetaRow>
            </dl>
          </SideCard>
          {exifRows.length > 0 && (
            <SideCard title={m.media_type === "video" ? "Technical metadata" : "EXIF metadata"}>
              <dl>{exifRows.map(([k, v]) => <MetaRow key={k} label={EXIF_LABELS[k]}>{String(v)}</MetaRow>)}</dl>
            </SideCard>
          )}
          <SideCard title="Tags & topics">
            <div className="flex flex-wrap gap-1.5">
              {m.tags.map((t) => <Link key={t} href={`/media?q=${encodeURIComponent(t)}`} className="rounded-full bg-snow px-2.5 py-1 text-[12.5px] text-ink-soft ring-1 ring-frost hover:bg-ice">#{t}</Link>)}
              {(m.topics || []).map((t) => <Link key={t.slug} href={`/topics/${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>)}
            </div>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
