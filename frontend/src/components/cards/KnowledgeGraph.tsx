"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ErrorState, Skeleton } from "@/components/common/ui";
import { useApi } from "@/lib/hooks";

interface GNode { key: string; type: string; title: string; kind: string; url: string; depth: number }
interface GEdge { source: string; target: string; relation: string }

const COLORS: Record<string, string> = {
  document: "#1aa3c8", dataset: "#128a87", media: "#7b6cd9", expedition: "#d4952a", station: "#0b1f33", researcher: "#5b7489", topic: "#4fd1a5",
};

/** Lightweight radial relationship graph (no graph database needed): centre → linked records → second hop. */
export function KnowledgeGraph({ type, slug }: { type: string; slug: string }) {
  const { data, error, loading, reload } = useApi<{ nodes: GNode[]; edges: GEdge[] }>(`/api/graph/${type}/${slug}`);
  const router = useRouter();
  const [hover, setHover] = useState<string | null>(null);
  const W = 720, H = 460;

  const layout = useMemo(() => {
    if (!data) return null;
    const pos: Record<string, { x: number; y: number }> = {};
    const centre = data.nodes.find((n) => n.depth === 0);
    if (!centre) return null;
    pos[centre.key] = { x: W / 2, y: H / 2 };
    const ring1 = data.nodes.filter((n) => n.depth === 1);
    ring1.forEach((n, i) => {
      const a = (i / ring1.length) * Math.PI * 2 - Math.PI / 2;
      pos[n.key] = { x: W / 2 + Math.cos(a) * 170, y: H / 2 + Math.sin(a) * 140 };
    });
    const ring2 = data.nodes.filter((n) => n.depth === 2);
    ring2.forEach((n) => {
      const parentEdge = data.edges.find((e) => e.target === n.key);
      const p = parentEdge ? pos[parentEdge.source] : { x: W / 2, y: H / 2 };
      const siblings = ring2.filter((m) => data.edges.find((e) => e.target === m.key)?.source === parentEdge?.source);
      const idx = siblings.indexOf(n);
      const base = Math.atan2(p.y - H / 2, p.x - W / 2);
      const a = base + (idx - (siblings.length - 1) / 2) * 0.32;
      pos[n.key] = { x: Math.min(W - 40, Math.max(40, p.x + Math.cos(a) * 95)), y: Math.min(H - 20, Math.max(20, p.y + Math.sin(a) * 80)) };
    });
    return pos;
  }, [data]);

  if (loading) return <Skeleton className="h-[320px] w-full" />;
  if (error) return <ErrorState error={error} onRetry={reload} compact />;
  if (!data || !layout) return null;

  return (
    <div className="overflow-x-auto rounded-xl bg-snow ring-1 ring-frost">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full min-w-[560px]" role="img" aria-label="Knowledge relationship graph">
        {data.edges.map((e, i) => {
          const a = layout[e.source], b = layout[e.target];
          if (!a || !b) return null;
          const hot = hover && (hover === e.source || hover === e.target);
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={hot ? "#1aa3c8" : "#c7d8e1"} strokeWidth={hot ? 2 : 1.2} />;
        })}
        {data.nodes.map((n) => {
          const p = layout[n.key];
          if (!p) return null;
          const r = n.depth === 0 ? 16 : n.depth === 1 ? 9 : 6;
          return (
            <g
              key={n.key}
              transform={`translate(${p.x} ${p.y})`}
              className="cursor-pointer"
              onMouseEnter={() => setHover(n.key)}
              onMouseLeave={() => setHover(null)}
              onClick={() => router.push(n.url)}
              role="link"
              tabIndex={0}
              aria-label={`${n.kind}: ${n.title}`}
              onKeyDown={(e) => e.key === "Enter" && router.push(n.url)}
            >
              <circle r={r + 4} fill="#fff" />
              <circle r={r} fill={COLORS[n.type] || "#5b7489"} />
              <text
                y={r + 14}
                textAnchor="middle"
                fontSize={n.depth === 0 ? 13 : 11}
                fontWeight={n.depth === 0 ? 600 : 400}
                fill="#0e2233"
                stroke="#f6fafc"
                strokeWidth="3"
                paintOrder="stroke"
                fontFamily="IBM Plex Sans"
              >
                {n.title.length > 30 && hover !== n.key ? n.title.slice(0, 28) + "…" : n.title}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-3 border-t border-frost px-4 py-2 text-[11px] text-steel">
        {Object.entries(COLORS).map(([k, c]) => (
          <span key={k} className="inline-flex items-center gap-1.5 capitalize">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} /> {k}
          </span>
        ))}
      </div>
    </div>
  );
}
