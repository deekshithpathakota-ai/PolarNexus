"use client";

import { Copy, ExternalLink } from "lucide-react";
import { Button } from "@/components/common/ui";
import type { DuplicateCandidate } from "@/lib/types";

/** "Potential duplicate detected" — the uploader decides; nothing is ever merged or deleted automatically. */
export function DuplicateNotice({ uploaded, candidates, onKeepBoth, onUpdate, onCancel, busy }: {
  uploaded: string; candidates: DuplicateCandidate[]; onKeepBoth: () => void; onUpdate?: (slug: string) => void; onCancel: () => void; busy?: boolean;
}) {
  const top = candidates[0];
  return (
    <div role="alertdialog" aria-labelledby="dup-h" className="rounded-2xl border border-[#f0dcb4] bg-[#fdf8ee] p-4">
      <p id="dup-h" className="flex items-center gap-2 font-medium text-[#7a520b]"><Copy className="h-4 w-4" aria-hidden /> Potential duplicate detected</p>
      <p className="mt-1 text-[13px] text-[#7a520b]">Similarity: <strong>{top.similarity}%</strong></p>
      <div className="mt-3 grid gap-3 text-[13px] sm:grid-cols-2">
        <div className="rounded-xl bg-white p-3 ring-1 ring-[#f0dcb4]">
          <p className="font-mono text-[10.5px] uppercase tracking-wider text-steel">Existing</p>
          <p className="mt-0.5 font-medium text-night">{top.title}</p>
          <ul className="mt-1 list-disc pl-4 text-[12px] text-ink-soft">{top.signals.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
        <div className="rounded-xl bg-white p-3 ring-1 ring-[#f0dcb4]">
          <p className="font-mono text-[10.5px] uppercase tracking-wider text-steel">Uploaded</p>
          <p className="mt-0.5 break-all font-medium text-night">{uploaded}</p>
          {candidates.length > 1 && <p className="mt-1 text-[12px] text-steel">+{candidates.length - 1} other possible match(es)</p>}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" onClick={onKeepBoth} loading={busy}>Keep both</Button>
        {onUpdate && <Button size="sm" variant="secondary" onClick={() => onUpdate(top.slug)} disabled={busy}>Update existing</Button>}
        <a href={top.url} target="_blank" rel="noopener noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-frost bg-white px-3 text-[13px] text-night hover:bg-ice">
          Review <ExternalLink className="h-3.5 w-3.5" aria-hidden />
        </a>
        <Button size="sm" variant="ghost" onClick={onCancel} disabled={busy}>Cancel</Button>
      </div>
      <p className="mt-2 text-[11.5px] text-[#7a520b]">“Update existing” adds your file as a new version; the previous version stays in the history.</p>
    </div>
  );
}
