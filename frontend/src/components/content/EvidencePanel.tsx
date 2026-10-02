"use client";

import clsx from "clsx";
import { CircleCheck, CircleX, ExternalLink, Info, RefreshCw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/common/ui";
import type { ContentItem } from "@/lib/types";

const ICON = { pass: CircleCheck, warn: TriangleAlert, fail: CircleX };
const COLOR = { pass: "text-teal", warn: "text-amber", fail: "text-coral" };

export function EvidenceCheckView({ item, onRecheck, rechecking, onRemoveClaim }: {
  item: ContentItem; onRecheck?: () => void; rechecking?: boolean; onRemoveClaim?: (text: string) => void;
}) {
  const ec = item.evidence_check;
  const [showSentences, setShowSentences] = useState(() => !!ec?.sentences.some((x) => !x.supported));
  if (!ec) return null;
  const cite = (n: number | null) => {
    const c = n ? item.citations?.find((x) => x.n === n) : null;
    return c ? `${c.label}${c.section ? ` · ${c.section}` : ""}${c.page ? `, p. ${c.page}` : ""}` : null;
  };
  const OverallIcon = ICON[ec.overall];
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className={clsx("flex items-center gap-1.5 text-[14px] font-semibold", COLOR[ec.overall])}>
          <OverallIcon className="h-4.5 w-4.5" />
          {ec.overall === "pass" ? "Evidence check passed" : ec.overall === "warn" ? "Evidence check: review warnings" : "Evidence check: issues found"}
        </p>
        {onRecheck && (
          <Button size="sm" variant="ghost" onClick={onRecheck} loading={rechecking} icon={<RefreshCw className="h-3.5 w-3.5" />}>
            Re-run
          </Button>
        )}
      </div>
      <ul className="space-y-1.5">
        {ec.checks.map((c) => {
          const I = ICON[c.status];
          return (
            <li key={c.id} className="flex gap-2 text-[13px]">
              <I className={clsx("mt-0.5 h-4 w-4 shrink-0", COLOR[c.status])} />
              <span>
                <span className="font-medium text-night">{c.label}</span>
                <span className="block text-[12.5px] text-steel">{c.detail}</span>
              </span>
            </li>
          );
        })}
      </ul>
      {ec.sentences.length > 0 && (
        <div className="mt-3">
          <button className="text-[12.5px] text-cyan-deep hover:underline" onClick={() => setShowSentences((s) => !s)}>
            {showSentences ? "Hide" : "Show"} sentence-level support ({ec.sentences.filter((s) => s.supported).length}/{ec.sentences.length} supported)
          </button>
          {showSentences && (
            <ul className="mt-2 space-y-1.5">
              {ec.sentences.map((s, i) => (
                <li key={i} className={clsx("rounded-lg border px-2.5 py-1.5 text-[12.5px] leading-relaxed", s.supported ? "border-[#bfe5df] bg-[#f2faf8]" : "border-[#f0dcb4] bg-[#fdf8ee]")}>
                  {!s.supported && <span className="mb-0.5 flex items-center gap-1 font-mono text-[10.5px] font-semibold uppercase tracking-wide text-[#8a5c0c]"><TriangleAlert className="h-3 w-3" aria-hidden /> Unsupported claim</span>}
                  <span className="text-ink">{s.text}</span>
                  <span className="mt-0.5 block font-mono text-[10.5px] text-steel">
                    {s.supported && cite(s.best_source) ? <>Evidence: [{s.best_source}] {cite(s.best_source)} · </> : null}
                    overlap {Math.round(s.support * 100)}%{!s.supported && s.best_source ? ` · closest [${s.best_source}]` : ""}
                  </span>
                  {!s.supported && onRemoveClaim && (
                    <button onClick={() => onRemoveClaim(s.text)} className="mt-1 text-[11.5px] font-medium text-coral hover:underline">Remove this claim</button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      <p className="mt-3 flex gap-1.5 rounded-lg bg-snow p-2.5 text-[11.5px] leading-relaxed text-steel">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {ec.method_note}
      </p>
    </div>
  );
}

export function CitationList({ item, active, onActive }: { item: ContentItem; active: number | null; onActive: (n: number | null) => void }) {
  return (
    <ol className="space-y-2">
      {(item.citations || []).map((c) => (
        <li key={c.n} id={`cite-${c.n}`} className={clsx("rounded-xl border p-3 transition-colors", active === c.n ? "border-cyan bg-[#f0f9fc]" : "border-frost")}>
          <button className="flex w-full items-start gap-2.5 text-left" onClick={() => onActive(active === c.n ? null : c.n)} aria-expanded={active === c.n}>
            <span className="mt-0.5 flex h-5 min-w-5 items-center justify-center rounded-md bg-[#e3f4fa] font-mono text-[11px] font-semibold text-cyan-deep">{c.n}</span>
            <span className="min-w-0">
              <span className="block text-[13.5px] font-medium text-night">{c.label}</span>
              <span className="block text-[12px] text-steel">{c.section}{c.page ? ` · p. ${c.page}` : ""}</span>
            </span>
          </button>
          {active === c.n && (
            <div className="ml-7 mt-2">
              <blockquote className="border-l-2 border-glacier pl-3 text-[12.5px] leading-relaxed text-ink-soft">{c.quote}</blockquote>
              {c.url && (
                <Link href={c.url} className="mt-1.5 inline-flex items-center gap-1 text-[12.5px] text-cyan-deep hover:underline">
                  Open source <ExternalLink className="h-3 w-3" />
                </Link>
              )}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

export function History({ item }: { item: ContentItem }) {
  return (
    <ol className="relative space-y-3 border-l border-frost pl-4">
      {(item.history || []).map((h, i) => (
        <li key={i} className="relative text-[12.5px]">
          <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white bg-cyan" />
          <span className="font-medium capitalize text-night">{h.action.replace(/_/g, " ")}</span>
          <span className="text-steel"> · {h.by} · {new Date(h.at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
          {h.comment && <span className="block text-ink-soft">{h.comment}</span>}
        </li>
      ))}
    </ol>
  );
}
