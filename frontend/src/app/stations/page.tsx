"use client";

import { BadgeCheck, MapPin } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { PolarScene } from "@/components/art/PolarScene";
import { CardSkeleton, DemoBadge, ErrorState, LinkButton, PageHeader, Tabs } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { coord } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Station } from "@/lib/types";

const SCENE: Record<string, string> = { maitri: "station-night", bharati: "station", himadri: "arctic-village", himansh: "mountains", indarc: "fjord", "dakshin-gangotri": "iceshelf", "ncpor-goa": "ocean", "prydz-bay-site": "seaice", "schirmacher-lakes-site": "lake" };

export default function StationsPage() {
  const [region, setRegion] = useState("all");
  const { data, error, loading, reload } = useApi<{ results: Station[] }>("/api/stations", { region: region === "all" ? undefined : region });
  return (
    <Container>
      <PageHeader
        eyebrow="Infrastructure"
        title="Research Stations"
        description="India's polar research bases and observation locations, with the expeditions, datasets and publications connected to each."
        actions={<LinkButton href="/map" variant="secondary">View on Polar Map</LinkButton>}
      >
        <p className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] text-steel">
          <BadgeCheck className="h-4 w-4 text-teal" /> Verified records show only widely published facts (location, approximate coordinates, year established) with their source.
        </p>
      </PageHeader>
      <Tabs className="mb-6 w-fit" value={region} onChange={setRegion}
        tabs={["all", "Antarctic", "Arctic", "Himalaya", "Southern Ocean", "India"].map((r) => ({ key: r, label: r === "all" ? "All" : r }))} />
      {error ? <ErrorState error={error} onRetry={reload} /> : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {loading || !data ? Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />) : data.results.map((s) => (
            <Link key={s.slug} href={`/stations/${s.slug}`} className="group overflow-hidden rounded-2xl border border-frost bg-white shadow-card transition hover:-translate-y-0.5 hover:shadow-lift">
              <div className="relative aspect-[16/9]">
                <PolarScene scene={SCENE[s.slug] || "station"} seed={s.slug} title={s.name} className="h-full w-full" />
                <span className="absolute left-3 top-3 rounded-full bg-abyss/70 px-2.5 py-1 font-mono text-[11px] text-white backdrop-blur">{s.region}</span>
              </div>
              <div className="p-5">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-display text-[21px] text-night group-hover:text-cyan-deep">{s.name}</h3>
                  {s.verified ? <BadgeCheck className="h-5 w-5 shrink-0 text-teal" aria-label="Verified station facts" /> : <DemoBadge label="Demo location" />}
                </div>
                <p className="text-[13px] text-steel">{s.kind}</p>
                <p className="mt-2 flex items-center gap-1 text-[13px] text-ink-soft"><MapPin className="h-3.5 w-3.5 text-mist" /> {s.location_name}</p>
                <p className="mt-1 font-mono text-[12px] text-steel">{coord(s.latitude, s.longitude)} · est. {s.established}</p>
                <p className="mt-1 text-[12.5px] text-teal">{s.status}</p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {s.themes.slice(0, 3).map((t) => <span key={t} className="rounded-full bg-snow px-2 py-0.5 text-[11.5px] text-ink-soft ring-1 ring-frost">{t}</span>)}
                </div>
                {s.counts && (
                  <div className="mt-4 grid grid-cols-4 gap-2 border-t border-frost pt-3 text-center">
                    {(["document", "dataset", "expedition", "media"] as const).map((k) => (
                      <div key={k}><p className="font-display text-lg text-night">{s.counts?.[k] ?? 0}</p><p className="text-[10.5px] capitalize text-steel">{k === "media" ? "media" : `${k}s`}</p></div>
                    ))}
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </Container>
  );
}
