"use client";

import { geoAzimuthalEqualArea, geoEqualEarth, geoGraticule10, geoPath, type GeoProjection } from "d3-geo";
import type { Feature, FeatureCollection, MultiPolygon, Polygon } from "geojson";
import clsx from "clsx";
import { Minus, Plus, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { loadLand } from "./geo";

export type MapView = "antarctic" | "arctic" | "world";
export interface MapPoint {
  key: string;
  kind: "station" | "expedition" | "dataset";
  name: string;
  lat: number;
  lon: number;
  subtitle?: string;
  verified?: boolean;
}

const W = 760;
const H = 620;

function projection(view: MapView): GeoProjection {
  if (view === "antarctic") return geoAzimuthalEqualArea().rotate([-40, 90]).scale(400).translate([W / 2, H / 2]).clipAngle(52);
  if (view === "arctic") return geoAzimuthalEqualArea().rotate([-10, -90]).scale(520).translate([W / 2, H / 2]).clipAngle(42);
  return geoEqualEarth().scale(150).translate([W / 2, H / 2 + 10]);
}

export function inView(view: MapView, lat: number) {
  if (view === "antarctic") return lat < -40;
  if (view === "arctic") return lat > 50;
  return true;
}

/**
 * Interactive polar map: azimuthal (pole-centred) projections for the Antarctic and Arctic and an
 * Equal Earth world view. All geography is bundled (Natural Earth 110m via world-atlas), so the map
 * works offline and never depends on an external tile/API service.
 */
export function PolarMap({ view, points, selected, onSelect }: {
  view: MapView;
  points: MapPoint[];
  selected: string | null;
  onSelect: (key: string | null) => void;
}) {
  const [land, setLand] = useState<FeatureCollection<Polygon | MultiPolygon> | Feature<Polygon | MultiPolygon> | null>(null);
  const [failed, setFailed] = useState(false);
  const [zoom, setZoom] = useState(1);
  useEffect(() => {
    loadLand().then(setLand).catch(() => setFailed(true));
  }, []);
  useEffect(() => setZoom(1), [view]);

  const proj = useMemo(() => projection(view), [view]);
  const path = useMemo(() => geoPath(proj), [proj]);
  const grat = useMemo(() => path(geoGraticule10()) || "", [path]);
  const sphere = useMemo(() => path({ type: "Sphere" }) || "", [path]);
  const visible = points.filter((p) => inView(view, p.lat));
  // greedy label placement: label a station only if no already-labelled point sits too close
  const labelled = useMemo(() => {
    const placed: [number, number][] = [];
    const keys = new Set<string>();
    [...visible].sort((a, b) => Number(b.verified !== false) - Number(a.verified !== false)).forEach((p) => {
      if (p.kind !== "station") return;
      const xy = proj([p.lon, p.lat]);
      if (!xy) return;
      const minGap = 34 / zoom;
      if (placed.every(([x, y]) => Math.abs(x - xy[0]) > minGap * 3 || Math.abs(y - xy[1]) > minGap * 0.6)) {
        placed.push([xy[0], xy[1]]);
        keys.add(p.key);
      }
    });
    return keys;
  }, [visible, proj, zoom]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl bg-abyss">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full touch-pan-y" role="img" aria-label={`${view} map of stations, expeditions and datasets`} onClick={() => onSelect(null)}>
        <defs>
          <radialGradient id="map-sea" cx="50%" cy="50%" r="60%">
            <stop offset="0" stopColor="#12304a" />
            <stop offset="1" stopColor="#061423" />
          </radialGradient>
        </defs>
        <g transform={`translate(${W / 2} ${H / 2}) scale(${zoom}) translate(${-W / 2} ${-H / 2})`} style={{ transition: "transform 300ms ease" }}>
          <path d={sphere} fill="url(#map-sea)" stroke="#1c4563" />
          <path d={grat} fill="none" stroke="#9fd3e6" strokeOpacity="0.1" strokeWidth={0.8 / zoom} />
          {land && <path d={path(land) || ""} fill="#dbe9f0" stroke="#9fd3e6" strokeWidth={0.5 / zoom} />}
          {failed && (
            <text x={W / 2} y={40} textAnchor="middle" fill="#8fa6b8" fontSize="13">
              Coastline layer unavailable — showing coordinates only
            </text>
          )}
          {visible.map((p) => {
            const xy = proj([p.lon, p.lat]);
            if (!xy) return null;
            const active = selected === p.key;
            const s = 1 / zoom;
            const color = p.kind === "station" ? "#4fd1a5" : p.kind === "expedition" ? "#f0b35a" : "#7fc8ff";
            return (
              <g
                key={p.key}
                transform={`translate(${xy[0]} ${xy[1]}) scale(${s})`}
                className="cursor-pointer"
                role="button"
                tabIndex={0}
                aria-label={`${p.kind}: ${p.name}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect(p.key);
                }}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(p.key)}
              >
                {active && <circle r="18" fill={color} opacity="0.25" />}
                {p.kind === "station" ? (
                  <rect x="-7" y="-7" width="14" height="14" transform="rotate(45)" fill={color} stroke="#061423" strokeWidth="1.5" strokeDasharray={p.verified === false ? "2 2" : undefined} />
                ) : p.kind === "expedition" ? (
                  <circle r="6.5" fill={color} stroke="#061423" strokeWidth="1.5" />
                ) : (
                  <rect x="-5.5" y="-5.5" width="11" height="11" rx="2" fill={color} stroke="#061423" strokeWidth="1.5" />
                )}
                {(active || labelled.has(p.key)) && (
                  <text x="12" y="4" fontSize="12.5" fill="#eaf3f7" fontFamily="IBM Plex Sans" stroke="#061423" strokeWidth="3" paintOrder="stroke">
                    {p.name}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>
      <div className="absolute right-3 top-3 flex flex-col gap-1">
        {[
          { icon: Plus, label: "Zoom in", fn: () => setZoom((z) => Math.min(4, z * 1.5)) },
          { icon: Minus, label: "Zoom out", fn: () => setZoom((z) => Math.max(1, z / 1.5)) },
          { icon: RotateCcw, label: "Reset view", fn: () => setZoom(1) },
        ].map(({ icon: I, label, fn }) => (
          <button key={label} aria-label={label} onClick={fn} className="rounded-lg bg-night/80 p-2 text-frost backdrop-blur hover:bg-deep">
            <I className="h-4 w-4" />
          </button>
        ))}
      </div>
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-3 rounded-lg bg-night/80 px-3 py-2 text-[11.5px] text-frost backdrop-blur">
        <Legend color="#4fd1a5" shape="diamond" label="Station" />
        <Legend color="#f0b35a" shape="circle" label="Expedition" />
        <Legend color="#7fc8ff" shape="square" label="Dataset" />
      </div>
      <p className="absolute bottom-3 right-3 hidden font-mono text-[10px] text-mist sm:block">Natural Earth 110m · {view === "world" ? "Equal Earth" : "Azimuthal equal-area"}</p>
    </div>
  );
}

function Legend({ color, shape, label }: { color: string; shape: "diamond" | "circle" | "square"; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={clsx("inline-block h-2.5 w-2.5", shape === "circle" && "rounded-full", shape === "square" && "rounded-[2px]", shape === "diamond" && "rotate-45")}
        style={{ background: color }}
      />
      {label}
    </span>
  );
}
