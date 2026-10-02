"use client";

import clsx from "clsx";
import {
  BookOpen,
  Check,
  CircleAlert,
  Copy,
  ExternalLink,
  FlaskConical,
  RefreshCw,
  ShieldCheck,
  SquarePen,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { Markdown } from "@/components/common/Markdown";
import { InfoTip, GLOSSARY } from "@/components/common/ui";
import { post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AskResponse } from "@/lib/types";

export function EvidencePill({ status, label }: { status: AskResponse["evidence_status"]; label: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium",
        status === "strong" && "bg-[#e2f4f1] text-teal",
        status === "limited" && "bg-[#fbf1df] text-[#8a5c0c]",
        status === "insufficient" && "bg-[#fbe9e5] text-coral",
      )}
    >
      {status === "strong" ? <ShieldCheck className="h-3.5 w-3.5" /> : <CircleAlert className="h-3.5 w-3.5" />}
      {label}
    </span>
  );
}

export function ModeTag({ mode, label }: { mode: string; label: string }) {
  return (
    <span
      title={label}
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-wide",
        mode === "curated_demo" ? "border-dashed border-[#e2c58f] bg-[#fdf8ee] text-[#8a5c0c]" : "border-frost bg-snow text-steel",
      )}
    >
      {mode === "curated_demo" && <FlaskConical className="h-3 w-3" />}
      {mode === "curated_demo" ? "Demo response" : mode === "llm" ? "LLM · grounded" : mode === "extractive" ? "Extractive" : mode === "metadata" ? "Metadata" : "No answer"}
    </span>
  );
}

export function AnswerCard({ res, onRegenerate, regenerating }: { res: AskResponse; onRegenerate?: () => void; regenerating?: boolean }) {
  const [active, setActive] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [fb, setFb] = useState<"up" | "down" | null>(null);
  const refs = useRef<Record<number, HTMLLIElement | null>>({});
  const { can } = useAuth();

  const openCite = (n: number) => {
    setActive(n);
    refs.current[n]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  const insufficient = res.evidence_status === "insufficient";
  const firstDoc = res.sources.find((s) => s.resource_type === "document");

  return (
    <article className="animate-fade-up overflow-hidden rounded-2xl border border-frost bg-white shadow-card">
      <div className="flex flex-wrap items-center gap-2 border-b border-frost bg-snow/70 px-5 py-3">
        <EvidencePill status={res.evidence_status} label={res.evidence_label} />
        <ModeTag mode={res.mode} label={res.mode_label} />
        {res.document && (
          <span className="inline-flex items-center gap-1 rounded-full bg-ice px-2 py-0.5 text-[11.5px] text-deep">
            <BookOpen className="h-3 w-3" /> Scoped to this document
          </span>
        )}
        <span className="ml-auto hidden font-mono text-[10.5px] text-mist sm:block">
          {res.retrieval.passages_considered} passages retrieved · {res.retrieval.passages_used} used
        </span>
      </div>

      <div className="px-5 py-4">
        <p className="mb-1 font-mono text-[10.5px] uppercase tracking-wider text-steel">Answer</p>
        <Markdown text={res.answer} onCite={openCite} citeTitle={(n) => res.sources.find((s) => s.n === n)?.title} />
        {res.notice && <p className="mt-3 rounded-lg bg-[#fbf1df] px-3 py-2 text-[13px] text-[#7a520b]">{res.notice}</p>}
        {res.mode === "curated_demo" && (
          <p className="mt-3 text-[12px] text-steel">
            This response was prepared in advance for the demonstration because no language model is configured. Every citation opens a real repository passage.
          </p>
        )}
        {insufficient && res.suggestions && (
          <div className="mt-3">
            <p className="text-[13px] font-medium text-night">Try instead</p>
            <ul className="mt-1 list-disc pl-5 text-[13px] text-ink-soft">
              {res.suggestions.map((s) => <li key={s}>{s}</li>)}
            </ul>
          </div>
        )}
      </div>

      {res.sources.length > 0 && (
        <div className="border-t border-frost px-5 py-4">
          <p className="mb-2 flex items-center gap-1.5 font-mono text-[10.5px] uppercase tracking-wider text-steel">
            Evidence used <InfoTip label="Evidence" text={GLOSSARY.evidence} />
          </p>
          <ol className="space-y-2">
            {res.sources.map((s) => (
              <li
                key={s.n}
                ref={(el) => {
                  refs.current[s.n] = el;
                }}
                className={clsx("rounded-xl border p-3 transition-colors", active === s.n ? "border-cyan bg-[#f0f9fc]" : "border-frost bg-white")}
              >
                <button className="flex w-full items-start gap-3 text-left" onClick={() => setActive(active === s.n ? null : s.n)} aria-expanded={active === s.n}>
                  <span className="mt-0.5 flex h-5 min-w-5 items-center justify-center rounded-md bg-[#e3f4fa] font-mono text-[11px] font-semibold text-cyan-deep">{s.n}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[14px] font-medium text-night">{s.title}</span>
                    <span className="block text-[12px] text-steel">
                      {s.kind} · {s.section}
                      {s.resource_type === "document" ? ` · p. ${s.page}` : ""}
                      {s.is_demo ? " · demo record" : ""}
                    </span>
                  </span>
                </button>
                {active === s.n && (
                  <div className="ml-8 mt-2">
                    <blockquote className="border-l-2 border-glacier pl-3 text-[13.5px] leading-relaxed text-ink-soft">{s.snippet}</blockquote>
                    <Link href={s.url} className="mt-2 inline-flex items-center gap-1 text-[13px] font-medium text-cyan-deep hover:underline">
                      Open source record <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {res.related.length > 0 && (
        <div className="border-t border-frost px-5 py-4">
          <p className="mb-2 font-mono text-[10.5px] uppercase tracking-wider text-steel">Related knowledge</p>
          <div className="flex flex-wrap gap-2">
            {res.related.map((r) => (
              <Link key={`${r.type}${r.id}`} href={r.url} className="rounded-full border border-frost bg-snow px-3 py-1 text-[12.5px] text-deep hover:border-glacier hover:bg-ice">
                {r.title} <span className="text-mist">· {r.kind}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1 border-t border-frost bg-snow/50 px-3 py-2">
        <button
          onClick={async () => {
            const cites = res.sources.map((s) => `[${s.n}] ${s.title} — ${s.section}`).join("\n");
            try {
              await navigator.clipboard.writeText(`${res.answer}\n\nSources:\n${cites}`);
              setCopied(true);
              setTimeout(() => setCopied(false), 1800);
            } catch {
              /* clipboard blocked */
            }
          }}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12.5px] text-ink-soft hover:bg-ice"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-teal" /> : <Copy className="h-3.5 w-3.5" />} {copied ? "Copied" : "Copy"}
        </button>
        {onRegenerate && (
          <button onClick={onRegenerate} disabled={regenerating} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12.5px] text-ink-soft hover:bg-ice disabled:opacity-50">
            <RefreshCw className={clsx("h-3.5 w-3.5", regenerating && "animate-spin")} /> Regenerate
          </button>
        )}
        {!insufficient && firstDoc && can("generate_content") && (
          <Link
            href={`/studio?type=document&slug=${firstDoc.slug}`}
            className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12.5px] text-ink-soft hover:bg-ice"
          >
            <SquarePen className="h-3.5 w-3.5" /> Create outreach content
          </Link>
        )}
        <span className="ml-auto flex items-center gap-1">
          <span className="mr-1 hidden text-[12px] text-mist sm:inline">Helpful?</span>
          {(["up", "down"] as const).map((v) => {
            const I = v === "up" ? ThumbsUp : ThumbsDown;
            return (
              <button
                key={v}
                aria-label={v === "up" ? "Helpful" : "Not helpful"}
                aria-pressed={fb === v}
                onClick={() => {
                  setFb(v);
                  post("/api/ai/feedback", { query_id: res.query_id, feedback: v }).catch(() => {});
                }}
                className={clsx("rounded-lg p-1.5 hover:bg-ice", fb === v ? "text-cyan-deep" : "text-mist")}
              >
                <I className="h-4 w-4" />
              </button>
            );
          })}
        </span>
      </div>
    </article>
  );
}
