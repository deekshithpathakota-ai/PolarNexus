"use client";

import clsx from "clsx";
import { ArrowRight, BookOpen, Building2, Database, Film, Image as ImageIcon, MapPin, Ship, UserRound } from "lucide-react";
import Link from "next/link";
import { PolarScene } from "@/components/art/PolarScene";
import { Badge, DemoBadge, type Tone } from "@/components/common/ui";
import { highlightTerms } from "@/components/common/Markdown";
import type { Card as CardT, SearchResult } from "@/lib/types";

export const TYPE_META: Record<string, { icon: typeof BookOpen; tone: Tone; label: string }> = {
  document: { icon: BookOpen, tone: "cyan", label: "Document" },
  dataset: { icon: Database, tone: "teal", label: "Dataset" },
  media: { icon: ImageIcon, tone: "violet", label: "Media" },
  expedition: { icon: Ship, tone: "amber", label: "Expedition" },
  station: { icon: Building2, tone: "night", label: "Station" },
  researcher: { icon: UserRound, tone: "slate", label: "Researcher" },
};

export function TypeBadge({ type, kind }: { type: string; kind?: string }) {
  const m = TYPE_META[type] || TYPE_META.document;
  const I = type === "media" && kind === "Video" ? Film : m.icon;
  return (
    <Badge tone={m.tone} icon={<I className="h-3 w-3" />}>
      {kind || m.label}
    </Badge>
  );
}

export function ResourceCard({ item, terms = [], compact, showReason }: { item: CardT | SearchResult; terms?: string[]; compact?: boolean; showReason?: boolean }) {
  const r = item as SearchResult;
  const scene = (item.extra?.scene as string) || null;
  return (
    <Link
      href={item.url}
      className={clsx(
        "group flex h-full flex-col overflow-hidden rounded-2xl border border-frost bg-white shadow-card transition-all hover:-translate-y-0.5 hover:border-glacier hover:shadow-lift",
      )}
    >
      {scene && !compact && (
        <div className="relative aspect-[16/9] overflow-hidden bg-ice">
          <PolarScene scene={scene} seed={item.slug} title={item.title} className="h-full w-full transition-transform duration-500 group-hover:scale-[1.03]" />
          {item.extra?.media_type === "video" && (
            <span className="absolute bottom-2 right-2 rounded-md bg-abyss/75 px-1.5 py-0.5 font-mono text-[10.5px] text-white">▶ {String(item.extra?.duration || "video")}</span>
          )}
        </div>
      )}
      <div className={clsx("flex flex-1 flex-col", compact ? "p-4" : "p-5")}>
        <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
          <TypeBadge type={item.type} kind={item.kind} />
          {item.region && (
            <span className="inline-flex items-center gap-1 text-[12px] text-steel">
              <MapPin className="h-3 w-3" /> {item.region}
            </span>
          )}
          {item.year && <span className="font-mono text-[12px] text-steel">· {item.year}</span>}
          {item.is_demo && <DemoBadge className="ml-auto" label="Demo" />}
        </div>
        <h3 className={clsx("font-display leading-snug text-night group-hover:text-cyan-deep", compact ? "text-[16px]" : "text-[18px]")}>
          {highlightTerms(item.title, terms)}
        </h3>
        {!compact && (
          <p className="mt-2 line-clamp-3 text-[13.5px] leading-relaxed text-ink-soft">
            {highlightTerms(r.highlight || item.summary, terms)}
          </p>
        )}
        {showReason && r.match_type && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[11.5px]">
            <span className="rounded bg-ice px-1.5 py-0.5 font-mono text-steel">{r.match_type}</span>
            {r.matched_section && <span className="text-steel">in “{r.matched_section}”</span>}
            {r.matching_concepts.map((c) => (
              <span key={c} className="rounded-full bg-[#e2f4f1] px-2 py-0.5 text-teal">{c}</span>
            ))}
          </div>
        )}
        <div className="mt-auto flex items-center justify-between gap-3 pt-4">
          <div className="flex min-w-0 flex-wrap gap-1">
            {item.topics.slice(0, compact ? 1 : 2).map((t) => (
              <span key={t} className="truncate rounded-full bg-snow px-2 py-0.5 text-[11.5px] text-ink-soft ring-1 ring-frost">{t}</span>
            ))}
          </div>
          {r.relevance != null && showReason ? (
            <span className="flex shrink-0 items-center gap-1.5" title="Relative relevance within this result set">
              <span className="h-1.5 w-14 overflow-hidden rounded-full bg-ice">
                <span className="block h-full rounded-full bg-cyan" style={{ width: `${Math.max(8, (r.relevance || 0) * 100)}%` }} />
              </span>
            </span>
          ) : (
            <ArrowRight className="h-4 w-4 shrink-0 text-mist transition-transform group-hover:translate-x-0.5 group-hover:text-cyan-deep" />
          )}
        </div>
      </div>
    </Link>
  );
}

export function ResourceRow({ item }: { item: CardT }) {
  return (
    <Link href={item.url} className="group flex items-start gap-3 rounded-xl border border-transparent p-2.5 hover:border-frost hover:bg-snow">
      <div className="mt-0.5 rounded-lg bg-ice p-2 text-deep">
        {(() => {
          const I = (TYPE_META[item.type] || TYPE_META.document).icon;
          return <I className="h-4 w-4" />;
        })()}
      </div>
      <div className="min-w-0">
        <p className="line-clamp-2 text-[14px] font-medium leading-snug text-night group-hover:text-cyan-deep">{item.title}</p>
        <p className="mt-0.5 text-[12px] text-steel">
          {item.kind}
          {item.region ? ` · ${item.region}` : ""}
          {item.year ? ` · ${item.year}` : ""}
          {item.relation ? ` · ${item.relation.replace(/_/g, " ")}` : ""}
        </p>
      </div>
    </Link>
  );
}
