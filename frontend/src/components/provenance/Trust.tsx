"use client";

import clsx from "clsx";
import { CheckCircle2, CircleDashed, CircleDot, Download, FlaskConical, History, Info, ListTree, ScrollText, XCircle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Card, ErrorState, Skeleton, Tabs } from "@/components/common/ui";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { FairRecord, Lineage, LineageStage, VersionEntry } from "@/lib/types";
import { VerificationBadge } from "./Provenance";

type Tab = "versions" | "fair" | "lineage";

/** "Scientific trust" panel: append-only version history, FAIR metadata record and provenance pipeline. */
export function ScientificTrust({ type, slug, defaultTab = "lineage" }: { type: string; slug: string; defaultTab?: Tab }) {
  const [tab, setTab] = useState<Tab>(defaultTab);
  return (
    <Card as="section" aria-labelledby="trust-heading" className="p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="trust-heading" className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-steel">
          <ListTree className="h-4 w-4 text-cyan-deep" aria-hidden /> Scientific trust
        </h2>
        <Tabs
          value={tab}
          onChange={setTab}
          tabs={[
            { key: "lineage", label: "Pipeline" },
            { key: "versions", label: "Versions" },
            { key: "fair", label: "Metadata" },
          ]}
        />
      </div>
      {tab === "lineage" && <LineageView path={`/api/lineage/${type}/${slug}`} />}
      {tab === "versions" && <VersionHistory type={type} slug={slug} />}
      {tab === "fair" && <FairPanel type={type} slug={slug} />}
    </Card>
  );
}

const STATE_STYLE: Record<string, { icon: typeof CheckCircle2; cls: string; label: string }> = {
  done: { icon: CheckCircle2, cls: "text-teal", label: "Done" },
  info: { icon: CircleDot, cls: "text-cyan-deep", label: "Recorded" },
  in_progress: { icon: CircleDot, cls: "text-[#5a4bb5]", label: "In progress" },
  pending: { icon: CircleDashed, cls: "text-mist", label: "Pending" },
  missing: { icon: CircleDashed, cls: "text-amber", label: "Not recorded" },
  not_applicable: { icon: CircleDashed, cls: "text-mist", label: "Not applicable" },
  rejected: { icon: XCircle, cls: "text-coral", label: "Rejected" },
  demo: { icon: FlaskConical, cls: "text-[#8a5c0c]", label: "Demonstration" },
};

export function LineageStages({ stages }: { stages: LineageStage[] }) {
  return (
    <ol className="relative space-y-3 border-l border-frost pl-5">
      {stages.map((s) => {
        const st = STATE_STYLE[s.state] || STATE_STYLE.pending;
        const I = st.icon;
        return (
          <li key={s.key} className="relative">
            <span className={clsx("absolute -left-[27px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-white", st.cls)}>
              <I className="h-4 w-4" aria-hidden />
            </span>
            <p className="text-[13.5px] font-medium text-night">
              {s.label} <span className={clsx("ml-1 font-mono text-[10.5px] uppercase tracking-wide", st.cls)}>{st.label}</span>
            </p>
            <p className="text-[12.5px] leading-relaxed text-ink-soft">
              {s.detail}
              {(s.at || s.actor) && <span className="text-steel"> · {[s.at && fmtDate(s.at), s.actor].filter(Boolean).join(" · ")}</span>}
            </p>
          </li>
        );
      })}
    </ol>
  );
}

export function LineageView({ path, showSources = true }: { path: string; showSources?: boolean }) {
  const { data, error, loading, reload } = useApi<Lineage>(path);
  if (error) return <ErrorState error={error} onRetry={reload} compact />;
  if (loading || !data) return <Skeleton className="h-40 w-full" />;
  return (
    <div className="space-y-4">
      <LineageStages stages={data.stages} />
      {showSources && data.generated_from && data.generated_from.length > 0 && (
        <div>
          <p className="mb-2 font-mono text-[10.5px] uppercase tracking-wider text-steel">Generated from</p>
          <ul className="space-y-1.5">
            {data.generated_from.map((g) => (
              <li key={`${g.type}-${g.id}`} className="flex flex-wrap items-center gap-2 text-[13px]">
                {g.url ? <Link href={g.url} className="font-medium text-cyan-deep hover:underline">{g.title}</Link> : <span className="font-medium">{g.title}</span>}
                <span className="text-steel">
                  {g.type} · {g.citations} citation{g.citations === 1 ? "" : "s"}
                  {g.pages.length > 0 && ` · p. ${g.pages.join(", ")}`}
                </span>
                {g.verification_status && <VerificationBadge status={g.verification_status} label={g.verification_label} />}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function VersionHistory({ type, slug }: { type: string; slug: string }) {
  const { data, error, loading, reload } = useApi<{ versions: VersionEntry[]; policy: string }>(`/api/versions/${type}/${slug}`);
  const [open, setOpen] = useState<number | null>(null);
  if (error) return <ErrorState error={error} onRetry={reload} compact />;
  if (loading || !data) return <Skeleton className="h-32 w-full" />;
  if (!data.versions.length) return <p className="text-[13px] text-steel">No versions recorded yet.</p>;
  return (
    <div>
      <ol className="space-y-2">
        {data.versions.map((v) => (
          <li key={v.version} className="rounded-lg border border-frost bg-snow/60 px-3 py-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[13.5px] text-night">
                <span className="mr-2 inline-flex items-center gap-1 font-mono text-[11px] text-cyan-deep"><History className="h-3.5 w-3.5" aria-hidden />v{v.version}</span>
                {v.change}
              </p>
              <span className="text-[12px] text-steel">{fmtDate(v.date)} · {v.user}</span>
            </div>
            {v.changed_fields.length > 0 && <p className="mt-1 text-[12px] text-steel">Changed: {v.changed_fields.join(", ")}</p>}
            <button className="mt-1 text-[12px] text-cyan-deep hover:underline" aria-expanded={open === v.version} onClick={() => setOpen(open === v.version ? null : v.version)}>
              {open === v.version ? "Hide snapshot" : "View snapshot"}
            </button>
            {open === v.version && (
              <pre className="scrollbar-thin mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-md bg-white p-2 font-mono text-[11px] text-ink-soft ring-1 ring-frost">
                {JSON.stringify(Object.fromEntries(Object.entries(v.snapshot).filter(([k]) => k !== "content_archive")), null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ol>
      <p className="mt-2 flex items-center gap-1.5 text-[12px] text-steel"><Info className="h-3.5 w-3.5" aria-hidden />{data.policy}</p>
    </div>
  );
}

function fmtValue(v: unknown): string {
  if (v == null) return "";
  if (Array.isArray(v)) return v.map((x) => (typeof x === "object" && x ? (x as { name?: string; orcid?: string | null }).name + ((x as { orcid?: string | null }).orcid ? ` (ORCID ${(x as { orcid: string }).orcid})` : "") : String(x))).join("; ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function FairPanel({ type, slug }: { type: string; slug: string }) {
  const { data, error, loading, reload } = useApi<FairRecord>(`/api/fair/${type}/${slug}`);
  if (error) return <ErrorState error={error} onRetry={reload} compact />;
  if (loading || !data) return <Skeleton className="h-48 w-full" />;
  const pct = Math.round(data.completeness * 100);
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}-metadata.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2" aria-label={`Required metadata ${pct}% complete`}>
          <span className="h-2 w-28 rounded-full bg-ice" aria-hidden><span className="block h-full rounded-full bg-teal" style={{ width: `${pct}%` }} /></span>
          <span className="font-mono text-[12px] text-night">{pct}% complete</span>
        </div>
        <button type="button" onClick={download} className="inline-flex items-center gap-1 text-[12.5px] text-cyan-deep hover:underline"><Download className="h-3.5 w-3.5" aria-hidden />Download JSON</button>
      </div>
      <dl className="divide-y divide-frost/70">
        {data.fields.map((f) => (
          <div key={f.key} className="grid grid-cols-[minmax(0,130px)_minmax(0,1fr)] gap-3 py-1.5 text-[13px]">
            <dt className="text-steel">
              {f.label}
              <span className="block font-mono text-[10px] text-mist">{f.term}</span>
            </dt>
            <dd className={clsx("min-w-0 break-words", f.value == null ? "italic text-mist" : "text-night")}>
              {f.value == null ? (f.required ? "Missing — not recorded" : "Not recorded") : fmtValue(f.value)}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 flex items-start gap-1.5 text-[12px] leading-relaxed text-steel"><ScrollText className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />{data.standard}. Missing values are shown as missing — never generated. {data.orcid_note}</p>
    </div>
  );
}
