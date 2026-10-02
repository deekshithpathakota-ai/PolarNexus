"use client";

import { ScanEye, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Card, ErrorState, Skeleton, inputCls } from "@/components/common/ui";
import { VerificationBadge } from "@/components/provenance/Provenance";
import { useApi } from "@/lib/hooks";
import type { MediaItem, VerificationStatus } from "@/lib/types";

type Hit = MediaItem & { url: string; similarity: number; timestamp: string | null; frame_url: string | null; verification: VerificationStatus; verification_label: string };
interface Resp { query: string; available: boolean; model?: string; results: Hit[]; notice: string }

const EXAMPLES = ["iceberg near a research vessel", "aerial view of a research station", "people working on sea ice at night", "ship sailing through pack ice", "laboratory building in the Arctic"];

/** Text → image search over photographs and video key frames (CLIP). Finds pictures whose metadata never mentions the words. */
export function VisualSearch({ compact }: { compact?: boolean }) {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const { data, error, loading, reload } = useApi<Resp>(submitted ? "/api/visual/search" : null, { q: submitted, limit: 12 });
  return (
    <Card as="section" aria-labelledby="vs-h" className="p-5">
      <h2 id="vs-h" className="flex items-center gap-2 text-[18px] text-night"><ScanEye className="h-5 w-5 text-cyan-deep" aria-hidden /> Visual semantic search</h2>
      {!compact && <p className="mt-1 text-[13.5px] text-ink-soft">Describe what a picture shows. Images and video frames are compared with your words in a shared image–text embedding space (CLIP), so matches do not depend on captions or tags.</p>}
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); setSubmitted(q.trim()); }}>
        <label htmlFor="vs-q" className="sr-only">Describe the image</label>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-mist" aria-hidden />
          <input id="vs-q" className={`${inputCls} pl-9`} value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. iceberg near a research vessel" minLength={2} maxLength={200} />
        </div>
        <button type="submit" disabled={q.trim().length < 2} className="h-10 rounded-lg bg-cyan-deep px-4 text-sm font-medium text-white hover:bg-[#0c6f8e] disabled:opacity-40">Search</button>
      </form>
      {!submitted && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {EXAMPLES.map((e) => <button key={e} onClick={() => { setQ(e); setSubmitted(e); }} className="rounded-full border border-frost px-2.5 py-0.5 text-[12px] text-deep hover:border-cyan">{e}</button>)}
        </div>
      )}
      {submitted && (
        <div className="mt-4" aria-live="polite">
          {error ? <ErrorState error={error} onRetry={reload} compact /> : loading || !data ? (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="aspect-[4/3]" />)}</div>
          ) : !data.available ? (
            <p className="rounded-lg bg-ice px-3 py-2 text-[13px] text-deep">{data.notice}</p>
          ) : data.results.length === 0 ? (
            <p className="text-[13.5px] text-steel">No photograph or video frame is visually similar enough to “{data.query}”. Try different words, or use the regular search.</p>
          ) : (
            <>
              <ul className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
                {data.results.map((h) => (
                  <li key={h.slug}>
                    <Link href={h.url} className="group block overflow-hidden rounded-xl border border-frost bg-white shadow-card hover:border-glacier">
                      <span className="relative block aspect-[4/3] bg-ice">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={h.frame_url || h.thumbnail_url || ""} alt={h.alt_text || h.title} loading="lazy" className="h-full w-full object-cover" />
                        {h.timestamp && <span className="absolute bottom-1.5 left-1.5 rounded bg-abyss/80 px-1.5 py-0.5 font-mono text-[10.5px] text-white">Relevant frame — {h.timestamp}</span>}
                      </span>
                      <span className="block p-2.5">
                        <span className="line-clamp-2 text-[13px] font-medium leading-snug text-night group-hover:text-cyan-deep">{h.title}</span>
                        <span className="mt-1 flex flex-wrap items-center justify-between gap-1">
                          <span className="font-mono text-[11px] text-steel" title="CLIP cosine similarity — a relevance score, not a probability">sim {h.similarity.toFixed(2)}</span>
                          <VerificationBadge status={h.verification} label={h.verification_label} />
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[12px] text-steel">{data.notice}{data.model ? ` Model: ${data.model}.` : ""}</p>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
