"use client";

import clsx from "clsx";
import { FileText } from "lucide-react";
import { useState } from "react";
import { Markdown } from "@/components/common/Markdown";
import { ErrorState, Skeleton } from "@/components/common/ui";
import { ApiError, post } from "@/lib/api";
import type { SummaryResponse } from "@/lib/types";

const KINDS = [
  ["executive", "Executive Summary"],
  ["research", "Research Summary"],
  ["student", "Student-Friendly"],
  ["100-word", "100-word Summary"],
  ["key-findings", "Key Findings"],
  ["methodology", "Methodology"],
  ["impact", "Research Impact"],
] as const;

export function SummaryPanel({ slug, initial }: { slug: string; initial?: string }) {
  const [kind, setKind] = useState<string | null>(null);
  const [res, setRes] = useState<SummaryResponse | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState<number | null>(null);

  const run = async (k: string) => {
    setKind(k);
    setLoading(true);
    setErr(null);
    setOpen(null);
    try {
      setRes(await post<SummaryResponse>("/api/ai/summary", { document_slug: slug, kind: k }));
    } catch (e) {
      setErr(e as ApiError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {KINDS.map(([k, l]) => (
          <button
            key={k}
            onClick={() => run(k)}
            aria-pressed={kind === k}
            className={clsx(
              "rounded-full border px-3.5 py-1.5 text-[13px] transition-colors",
              kind === k ? "border-cyan bg-[#e3f4fa] font-medium text-cyan-deep" : "border-frost bg-white text-ink-soft hover:border-glacier",
            )}
          >
            {l}
          </button>
        ))}
      </div>
      <div className="mt-4">
        {!kind && !initial && (
          <p className="flex items-center gap-2 rounded-xl border border-dashed border-frost bg-snow p-4 text-sm text-steel">
            <FileText className="h-4 w-4" /> Choose a summary type. Every summary is built only from this document&apos;s own sections and cites them.
          </p>
        )}
        {loading && (
          <div className="space-y-2 rounded-xl border border-frost p-4">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3.5 w-full" />
            <Skeleton className="h-3.5 w-11/12" />
            <Skeleton className="h-3.5 w-4/5" />
          </div>
        )}
        {err && <ErrorState error={err} onRetry={() => kind && run(kind)} compact />}
        {res && !loading && (
          <div className="animate-fade-up rounded-xl border border-frost bg-white p-4">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <h3 className="font-display text-lg text-night">{res.label}</h3>
              <span className="rounded-full border border-frost bg-snow px-2 py-0.5 font-mono text-[10.5px] uppercase text-steel">
                {res.mode === "llm" ? "LLM · grounded" : res.mode === "extractive" ? "Extractive" : "No supporting section"}
              </span>
            </div>
            {res.text ? <Markdown text={res.text} onCite={(n) => setOpen(n)} /> : <p className="text-sm text-ink-soft">{res.notice}</p>}
            {res.notice && res.text && <p className="mt-2 text-[12px] text-steel">{res.notice}</p>}
            {res.sources.length > 0 && (
              <div className="mt-3 border-t border-frost pt-3">
                <p className="mb-1.5 font-mono text-[10.5px] uppercase tracking-wider text-steel">Sections used</p>
                <div className="flex flex-wrap gap-1.5">
                  {res.sources.map((s) => (
                    <button
                      key={s.n}
                      onClick={() => setOpen(open === s.n ? null : s.n)}
                      className={clsx("rounded-md px-2 py-1 text-[12px]", open === s.n ? "bg-cyan text-white" : "bg-ice text-deep hover:bg-frost")}
                    >
                      [{s.n}] {s.section} · p.{s.page}
                    </button>
                  ))}
                </div>
                {open && (
                  <blockquote className="mt-2 border-l-2 border-glacier pl-3 text-[13px] leading-relaxed text-ink-soft">
                    {res.sources.find((s) => s.n === open)?.snippet}
                  </blockquote>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
