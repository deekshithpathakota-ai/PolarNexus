"use client";

import { CalendarDays, Link2, MapPin, Star } from "lucide-react";
import Link from "next/link";
import { PolarScene } from "@/components/art/PolarScene";
import { Badge, DemoBadge } from "@/components/common/ui";
import { VerificationBadge } from "@/components/provenance/Provenance";
import { fmtDate } from "@/lib/format";
import type { Activity } from "@/lib/types";

export function activityWhen(a: Pick<Activity, "date" | "end_date">) {
  if (!a.date) return "Date to be announced";
  return a.end_date && a.end_date !== a.date ? `${fmtDate(a.date)} – ${fmtDate(a.end_date)}` : fmtDate(a.date);
}

export function ActivityCard({ a }: { a: Activity }) {
  return (
    <Link href={a.url} className="group flex h-full flex-col overflow-hidden rounded-2xl border border-frost bg-white shadow-card transition-all hover:-translate-y-0.5 hover:border-glacier hover:shadow-lift">
      <div className="relative aspect-[16/7] overflow-hidden bg-ice">
        <PolarScene scene={a.cover_scene} seed={a.slug} title={a.title} className="h-full w-full transition-transform duration-500 group-hover:scale-[1.03]" />
        <div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
          <Badge tone="night" className="border-white/20 bg-abyss/70 text-white">{a.activity_type_label}</Badge>
          {a.status === "upcoming" && <Badge tone="teal">Upcoming</Badge>}
          {a.featured && <Badge tone="amber" icon={<Star className="h-3 w-3" />}>Featured</Badge>}
        </div>
      </div>
      <div className="flex flex-1 flex-col p-5">
        <p className="mb-1.5 flex items-center gap-1.5 font-mono text-[12px] text-steel"><CalendarDays className="h-3.5 w-3.5" aria-hidden /> {activityWhen(a)}</p>
        <h3 className="font-display text-[18px] leading-snug text-night group-hover:text-cyan-deep">{a.title}</h3>
        <p className="mt-2 line-clamp-2 text-[13.5px] leading-relaxed text-ink-soft">{a.description}</p>
        <p className="mt-3 flex items-center gap-1.5 text-[12.5px] text-steel"><MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden /> <span className="truncate">{a.location}</span></p>
        <p className="mt-1 truncate text-[12.5px] text-steel">{a.organisation}</p>
        <div className="mt-auto flex items-center justify-between gap-2 pt-4">
          {a.is_demo ? <DemoBadge label="Demo" /> : <VerificationBadge status={a.verification} label={a.verification_label} />}
          {a.related_count ? <span className="inline-flex items-center gap-1 text-[12px] text-steel"><Link2 className="h-3.5 w-3.5" aria-hidden /> {a.related_count} linked records</span> : null}
        </div>
      </div>
    </Link>
  );
}
