"use client";

import clsx from "clsx";
import Link from "next/link";
import { useMemo, useState } from "react";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/ui";
import { VerificationBadge } from "@/components/provenance/Provenance";
import { useApi } from "@/lib/hooks";
import type { VerificationStatus } from "@/lib/types";

interface TItem {
  key: string; type: string; kind: string; title: string; url: string; year: number; date: string | null;
  summary: string; region: string; is_demo: boolean; verification: VerificationStatus; verification_label: string; group: string;
}
interface TResponse { items: TItem[]; total: number; years: { year: number; count: number }[]; anchors: string[]; note: string }

const TYPES: { key: string; label: string }[] = [
  { key: "document", label: "Documents" }, { key: "dataset", label: "Datasets" }, { key: "expedition", label: "Expeditions" },
  { key: "media", label: "Media" }, { key: "activity", label: "Activities" }, { key: "content", label: "Outreach" },
];

/** Chronological, clickable view of the records connected to a topic, expedition, station or researcher. */
export function KnowledgeTimeline({ scope, maxItems, showFilters = true }: {
  scope: { topic?: string; expedition?: string; station?: string; researcher?: string; activity?: string };
  maxItems?: number;
  showFilters?: boolean;
}) {
  const [types, setTypes] = useState<string[]>([]);
  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");
  const [expanded, setExpanded] = useState(false);
  const { data, error, loading, reload } = useApi<TResponse>("/api/timeline", {
    ...scope, type: types, year_from: from || undefined, year_to: to || undefined,
  });
  const items = useMemo(() => {
    const all = data?.items || [];
    return maxItems && !expanded ? all.slice(-maxItems) : all;
  }, [data, maxItems, expanded]);
  const byYear = useMemo(() => {
    const m = new Map<number, TItem[]>();
    items.forEach((i) => m.set(i.year, [...(m.get(i.year) || []), i]));
    return [...m.entries()];
  }, [items]);

  return (
    <div>
      {showFilters && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div role="group" aria-label="Resource types" className="flex flex-wrap gap-1.5">
            {TYPES.map((t) => {
              const on = types.includes(t.key);
              return (
                <button key={t.key} type="button" aria-pressed={on}
                  onClick={() => setTypes(on ? types.filter((x) => x !== t.key) : [...types, t.key])}
                  className={clsx("rounded-full border px-3 py-1 text-[12.5px]", on ? "border-cyan bg-[#e3f4fa] text-cyan-deep" : "border-frost bg-white text-ink-soft hover:border-glacier")}>
                  {t.label}
                </button>
              );
            })}
          </div>
          <div className="ml-auto flex items-center gap-1.5 text-[12.5px] text-steel">
            <label className="sr-only" htmlFor="tl-from">From year</label>
            <input id="tl-from" type="number" inputMode="numeric" placeholder="From" value={from} onChange={(e) => setFrom(e.target.value)}
              className="h-8 w-20 rounded-lg border border-frost px-2 text-[12.5px]" min={1900} max={2100} />
            <span aria-hidden>–</span>
            <label className="sr-only" htmlFor="tl-to">To year</label>
            <input id="tl-to" type="number" inputMode="numeric" placeholder="To" value={to} onChange={(e) => setTo(e.target.value)}
              className="h-8 w-20 rounded-lg border border-frost px-2 text-[12.5px]" min={1900} max={2100} />
          </div>
        </div>
      )}
      {error ? <ErrorState error={error} onRetry={reload} compact />
        : loading && !data ? <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
        : !items.length ? <EmptyState title="No dated records" body="Nothing in the repository matches these timeline filters yet." />
        : (
          <ol className="relative ml-2 border-l-2 border-frost pl-5 sm:ml-12" aria-label="Knowledge timeline">
            {byYear.map(([year, list]) => (
              <li key={year} className="relative mb-5 last:mb-0">
                <span className="absolute -left-[31px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-white bg-cyan-deep ring-2 ring-frost" aria-hidden />
                <p className="mb-2 font-mono text-[13px] font-semibold text-night sm:absolute sm:-left-[88px] sm:top-0 sm:w-12 sm:text-right">{year}</p>
                <ul className="space-y-2">
                  {list.map((i) => (
                    <li key={i.key}>
                      <Link href={i.url} className="group block rounded-xl border border-frost bg-white p-3 shadow-card transition hover:border-glacier hover:shadow-lift">
                        <div className="mb-1 flex flex-wrap items-center gap-1.5">
                          <TypeBadge type={i.type} kind={i.kind} />
                          {i.date && <span className="font-mono text-[11px] text-steel">{i.date}</span>}
                          <VerificationBadge className="ml-auto" status={i.verification} label={i.is_demo ? (i.verification === "synthetic_demo" ? "Synthetic" : "Demo") : i.verification_label} />
                        </div>
                        <p className="text-[14.5px] font-medium leading-snug text-night group-hover:text-cyan-deep">{i.title}</p>
                        <p className="mt-0.5 line-clamp-2 text-[12.5px] text-ink-soft">{i.summary}</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        )}
      {data && maxItems && data.items.length > maxItems && (
        <button onClick={() => setExpanded((e) => !e)} className="mt-3 text-[13px] text-cyan-deep hover:underline">
          {expanded ? "Show recent only" : `Show all ${data.items.length} records`}
        </button>
      )}
      {data && <p className="mt-3 text-[11.5px] text-steel">{data.note}</p>}
    </div>
  );
}
