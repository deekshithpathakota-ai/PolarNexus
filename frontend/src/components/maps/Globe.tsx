"use client";

import { geoGraticule10, geoOrthographic, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { useEffect, useRef, useState } from "react";
import { loadLand } from "./geo";

const MARKERS: { name: string; lon: number; lat: number }[] = [
  { name: "Maitri", lon: 11.73, lat: -70.77 },
  { name: "Bharati", lon: 76.19, lat: -69.41 },
  { name: "Himadri", lon: 11.93, lat: 78.92 },
  { name: "Himansh", lon: 77.6, lat: 32.4 },
];

/** Slowly rotating globe tilted towards Antarctica. Pure SVG, bundled land data, no external services. */
export function Globe({ size = 420 }: { size?: number }) {
  const [land, setLand] = useState<FeatureCollection<Polygon | MultiPolygon> | Feature<Polygon | MultiPolygon> | null>(null);
  const [rot, setRot] = useState(40);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    loadLand().then(setLand).catch(() => setLand(null));
  }, []);

  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    let last = performance.now();
    const tick = (t: number) => {
      if (t - last > 40) {
        setRot((r) => (r + 0.18) % 360);
        last = t;
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, []);

  const r = size / 2 - 6;
  const proj = geoOrthographic().scale(r).translate([size / 2, size / 2]).rotate([-rot, 62, 0]).clipAngle(90);
  const path = geoPath(proj);
  const grat = path(geoGraticule10()) || "";

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="h-full w-full" role="img" aria-label="Globe showing Indian polar research stations">
      <defs>
        <radialGradient id="globe-ocean" cx="40%" cy="35%" r="70%">
          <stop offset="0" stopColor="#1c4563" />
          <stop offset="1" stopColor="#071526" />
        </radialGradient>
        <radialGradient id="globe-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0.82" stopColor="#1aa3c8" stopOpacity="0" />
          <stop offset="1" stopColor="#1aa3c8" stopOpacity="0.35" />
        </radialGradient>
      </defs>
      <circle cx={size / 2} cy={size / 2} r={r + 6} fill="url(#globe-glow)" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="url(#globe-ocean)" stroke="#2d6f8f" strokeWidth="1" />
      <path d={grat} fill="none" stroke="#9fd3e6" strokeOpacity="0.12" strokeWidth="0.7" />
      {land && <path d={path(land) || ""} fill="#d5e6ee" fillOpacity="0.92" stroke="#9fd3e6" strokeWidth="0.4" />}
      {MARKERS.map((m) => {
        const p = proj([m.lon, m.lat]);
        const visible = p && (geoPath(proj)({ type: "Point", coordinates: [m.lon, m.lat] }) || "").length > 0;
        if (!p || !visible) return null;
        return (
          <g key={m.name}>
            <circle cx={p[0]} cy={p[1]} r="9" fill="#4fd1a5" opacity="0.25">
              <animate attributeName="r" values="5;12;5" dur="3s" repeatCount="indefinite" />
            </circle>
            <circle cx={p[0]} cy={p[1]} r="3.6" fill="#4fd1a5" stroke="#061423" strokeWidth="1" />
            <text x={p[0] + 8} y={p[1] + 4} fontSize="11" fill="#eaf3f7" fontFamily="IBM Plex Mono">{m.name}</text>
          </g>
        );
      })}
    </svg>
  );
}
