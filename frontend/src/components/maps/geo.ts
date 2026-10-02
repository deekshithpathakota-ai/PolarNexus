"use client";

import type { FeatureCollection, MultiPolygon, Polygon, Feature } from "geojson";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";

let cache: Promise<FeatureCollection<Polygon | MultiPolygon> | Feature<Polygon | MultiPolygon>> | null = null;

/** Loads the bundled Natural Earth 110m land outline (world-atlas, public domain). No external map API needed. */
export function loadLand() {
  if (!cache) {
    cache = import("world-atlas/land-110m.json").then((m) => {
      const topo = (m.default ?? m) as unknown as Topology<{ land: GeometryCollection }>;
      return feature(topo, topo.objects.land) as unknown as FeatureCollection<Polygon | MultiPolygon>;
    });
  }
  return cache;
}
