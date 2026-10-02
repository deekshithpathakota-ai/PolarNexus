"use client";

import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { Card } from "@/components/common/ui";
import { fmtNum } from "@/lib/format";
import type { DatasetDetail, DatasetIssue } from "@/lib/types";

const SEV = {
  error: { icon: XCircle, cls: "text-coral", label: "Error" },
  warning: { icon: AlertTriangle, cls: "text-[#8a5c0c]", label: "Warning" },
  info: { icon: Info, cls: "text-cyan-deep", label: "Note" },
} as const;

export function IssueList({ issues }: { issues: DatasetIssue[] }) {
  if (!issues.length) {
    return <p className="flex items-center gap-2 text-[13.5px] text-teal"><CheckCircle2 className="h-4 w-4" aria-hidden /> No validation issues found.</p>;
  }
  return (
    <ul className="space-y-1.5">
      {issues.map((i, n) => {
        const s = SEV[i.severity];
        const I = s.icon;
        return (
          <li key={n} className="flex gap-2 text-[13px] leading-relaxed">
            <I className={clsx("mt-0.5 h-4 w-4 shrink-0", s.cls)} aria-label={s.label} />
            <span className="min-w-0 text-ink-soft">
              {i.message}
              {i.examples?.length > 0 && <span className="block font-mono text-[11.5px] text-steel">e.g. {i.examples.join(" · ")}</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Schema + validation report captured when the dataset was ingested. */
export function DatasetQuality({ ds }: { ds: DatasetDetail }) {
  const rep = ds.quality_report || {};
  const verdict = rep.summary?.verdict;
  return (
    <Card as="section" aria-labelledby="dq-heading" className="p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="dq-heading" className="font-mono text-[11px] uppercase tracking-wider text-steel">Schema & validation report</h2>
        {verdict && (
          <span className={clsx("rounded-full px-2.5 py-0.5 font-mono text-[11px] uppercase", verdict === "pass" ? "bg-[#e2f4f1] text-teal" : verdict === "warn" ? "bg-[#fbf1df] text-[#8a5c0c]" : "bg-[#fbe9e5] text-coral")}>
            {verdict === "pass" ? "Passed" : verdict === "warn" ? "Passed with warnings" : "Registered with errors acknowledged"}
          </span>
        )}
      </div>
      {ds.columns_schema && ds.columns_schema.length > 0 && (
        <div className="scrollbar-thin mb-4 overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-[13px]">
            <caption className="sr-only">Detected columns, types and roles</caption>
            <thead className="text-[11px] uppercase tracking-wide text-steel">
              <tr><th className="py-1.5 pr-3 font-medium">Column</th><th className="pr-3 font-medium">Type</th><th className="pr-3 font-medium">Role</th><th className="pr-3 font-medium">Missing</th><th className="font-medium">Range</th></tr>
            </thead>
            <tbody className="divide-y divide-frost/70">
              {ds.columns_schema.map((c) => (
                <tr key={c.name}>
                  <td className="py-1.5 pr-3 font-mono text-[12px] text-night">{c.name}</td>
                  <td className="pr-3 text-ink-soft">{c.type}</td>
                  <td className="pr-3 text-ink-soft">{c.role || "—"}</td>
                  <td className="pr-3 font-mono text-[12px]">{fmtNum(c.missing)}</td>
                  <td className="font-mono text-[12px] text-steel">{c.stats && "min" in c.stats ? `${c.stats.min} … ${c.stats.max}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <IssueList issues={rep.issues || []} />
      {(rep.duplicates_dropped || rep.time_derivation) && (
        <p className="mt-3 text-[12px] text-steel">
          {rep.duplicates_dropped ? `${rep.duplicates_dropped} duplicate row(s) were removed at the uploader's request. ` : ""}
          {rep.time_derivation ? `Time axis derived from: ${rep.time_derivation}.` : ""}
        </p>
      )}
    </Card>
  );
}
