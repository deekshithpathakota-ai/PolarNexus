"use client";

import clsx from "clsx";
import { ArrowRight, BadgeCheck, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { DemoBadge, ErrorState, PageHeader, Skeleton, Tabs } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { inView, PolarMap, type MapPoint, type MapView } from "@/components/maps/PolarMap";
import { coord } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Expedition, Station } from "@/lib/types";

interface MapData {
  stations: (Omit<Station, "topics"> & { topics: string[]; counts: Record<string, number> })[];
  expeditions: (Omit<Expedition, "topics"> & { topics: string[] })[];
  datasets: { slug: string; title: string; region: string; latitude: number; longitude: number; url: string; data_type: string; topics: string[] }[];
  topics: string[];
}

function StaticFallback({ points }: { points: MapPoint[] }) {
  return (
    <div className="h-full overflow-y-auto rounded-2xl bg-night p-4 text-frost">
      <p className="mb-3 text-sm">The interactive map could not be drawn. Locations:</p>
      <ul className="space-y-1 font-mono text-[12px]">
        {points.map((p) => <li key={p.key}>{p.kind.padEnd(10)} {p.name} — {coord(p.lat, p.lon)}</li>)}
      </ul>
    </div>
  );
}

export default function MapPage() {
  const { data, error, loading, reload } = useApi<MapData>("/api/map");
  const [view, setView] = useState<MapView>("antarctic");
  const [layers, setLayers] = useState({ station: true, expedition: true, dataset: true });
  const [topic, setTopic] = useState("");
  const [sel, setSel] = useState<string | null>(null);

  const points: MapPoint[] = useMemo(() => {
    if (!data) return [];
    const t = (ts: string[]) => !topic || ts.includes(topic);
    return [
      ...(layers.station ? data.stations.filter((s) => t(s.topics)).map((s) => ({ key: `station:${s.slug}`, kind: "station" as const, name: s.name, lat: s.latitude, lon: s.longitude, subtitle: s.kind, verified: s.verified })) : []),
      ...(layers.expedition ? data.expeditions.filter((e) => t(e.topics) && e.latitude != null).map((e) => ({ key: `expedition:${e.slug}`, kind: "expedition" as const, name: e.name, lat: e.latitude!, lon: e.longitude!, subtitle: e.season })) : []),
      ...(layers.dataset ? data.datasets.filter((d) => t(d.topics)).map((d) => ({ key: `dataset:${d.slug}`, kind: "dataset" as const, name: d.title, lat: d.latitude, lon: d.longitude, subtitle: d.data_type })) : []),
    ];
  }, [data, layers, topic]);

  const selected = useMemo(() => {
    if (!sel || !data) return null;
    const [kind, slug] = sel.split(":");
    if (kind === "station") {
      const s = data.stations.find((x) => x.slug === slug)!;
      return { kind, title: s.name, url: `/stations/${s.slug}`, lat: s.latitude, lon: s.longitude, body: s.description, meta: `${s.kind} · est. ${s.established}`, tags: s.topics, verified: s.verified, counts: s.counts };
    }
    if (kind === "expedition") {
      const e = data.expeditions.find((x) => x.slug === slug)!;
      return { kind, title: e.name, url: `/expeditions/${e.slug}`, lat: e.latitude!, lon: e.longitude!, body: e.objective, meta: `${e.program} · ${e.season}`, tags: e.topics, verified: !e.is_demo };
    }
    const d = data.datasets.find((x) => x.slug === slug)!;
    return { kind, title: d.title, url: d.url, lat: d.latitude, lon: d.longitude, body: `${d.data_type} dataset · ${d.region}`, meta: "Dataset (synthetic demo values)", tags: d.topics, verified: false };
  }, [sel, data]);

  const visibleList = points.filter((p) => inView(view, p.lat));

  return (
    <Container className="max-w-[1400px]">
      <PageHeader eyebrow="Explore" title="Polar Map" description="Stations, expedition areas and dataset locations on pole-centred projections. Click any marker for its linked knowledge." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Tabs value={view} onChange={(v) => { setView(v); setSel(null); }} tabs={[{ key: "antarctic", label: "Antarctic" }, { key: "arctic", label: "Arctic" }, { key: "world", label: "World (incl. Himalaya)" }]} />
        <div className="flex flex-wrap gap-1.5">
          {(["station", "expedition", "dataset"] as const).map((k) => (
            <button key={k} aria-pressed={layers[k]} onClick={() => setLayers((l) => ({ ...l, [k]: !l[k] }))}
              className={clsx("rounded-full border px-3 py-1.5 text-[13px] capitalize", layers[k] ? "border-cyan bg-[#e3f4fa] text-cyan-deep" : "border-frost bg-white text-steel")}>
              {k}s
            </button>
          ))}
        </div>
        <select value={topic} onChange={(e) => setTopic(e.target.value)} aria-label="Filter by research topic" className="h-9 rounded-lg border border-frost bg-white px-2.5 text-[13px]">
          <option value="">All research topics</option>
          {data?.topics.map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>
      {error ? <ErrorState error={error} onRetry={reload} /> : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="h-[min(72vh,640px)] min-h-[380px]">
            {loading || !data ? <Skeleton className="h-full w-full rounded-2xl" /> : (
              <ErrorBoundary label="map" fallback={<StaticFallback points={points} />}>
                <PolarMap view={view} points={points} selected={sel} onSelect={setSel} />
              </ErrorBoundary>
            )}
          </div>
          <aside className="flex max-h-[min(72vh,640px)] flex-col overflow-hidden rounded-2xl border border-frost bg-white shadow-card">
            {selected ? (
              <div className="animate-fade-up overflow-y-auto p-5">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <span className="font-mono text-[11px] uppercase tracking-wider text-steel">{selected.kind}</span>
                  <button onClick={() => setSel(null)} aria-label="Close details" className="rounded p-1 text-mist hover:bg-ice"><X className="h-4 w-4" /></button>
                </div>
                <h2 className="text-[22px] leading-tight text-night">{selected.title}</h2>
                <p className="mt-1 text-[13px] text-steel">{selected.meta}</p>
                <p className="mt-1 font-mono text-[12px] text-steel">{coord(selected.lat, selected.lon)}</p>
                <div className="mt-2">{selected.verified ? <span className="inline-flex items-center gap-1 text-[12px] text-teal"><BadgeCheck className="h-3.5 w-3.5" /> Published facts</span> : <DemoBadge label="Demo record" />}</div>
                <p className="mt-3 text-[14px] leading-relaxed text-ink-soft">{selected.body}</p>
                {selected.counts && (
                  <div className="mt-4 grid grid-cols-4 gap-2 rounded-xl bg-snow p-3 text-center">
                    {Object.entries(selected.counts).map(([k, v]) => <div key={k}><p className="font-display text-lg text-night">{v}</p><p className="text-[10.5px] capitalize text-steel">{k}</p></div>)}
                  </div>
                )}
                <div className="mt-3 flex flex-wrap gap-1">{selected.tags.slice(0, 5).map((t) => <span key={t} className="rounded-full bg-ice px-2 py-0.5 text-[11.5px] text-deep">{t}</span>)}</div>
                <Link href={selected.url} className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-cyan-deep px-4 py-2 text-sm font-medium text-white hover:bg-[#0c6f8e]">Open record <ArrowRight className="h-4 w-4" /></Link>
              </div>
            ) : (
              <>
                <p className="border-b border-frost px-4 py-3 text-[13px] text-steel">{visibleList.length} locations in this view — select one</p>
                <ul className="flex-1 overflow-y-auto scrollbar-thin">
                  {visibleList.map((p) => (
                    <li key={p.key}>
                      <button onClick={() => setSel(p.key)} className="flex w-full items-center gap-3 border-b border-frost/60 px-4 py-2.5 text-left hover:bg-snow">
                        <span className={clsx("h-2.5 w-2.5 shrink-0", p.kind === "station" ? "rotate-45 bg-aurora" : p.kind === "expedition" ? "rounded-full bg-[#f0b35a]" : "rounded-[2px] bg-[#7fc8ff]")} />
                        <span className="min-w-0"><span className="block truncate text-[13.5px] text-night">{p.name}</span><span className="block text-[11.5px] text-steel">{p.kind} · {p.subtitle}</span></span>
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </aside>
        </div>
      )}
    </Container>
  );
}
