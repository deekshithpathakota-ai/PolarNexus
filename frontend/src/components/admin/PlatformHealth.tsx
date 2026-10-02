"use client";

import clsx from "clsx";
import { Bot, Database, FileWarning, Megaphone, RefreshCw } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useState } from "react";
import { Button, Card, ErrorState, Skeleton } from "@/components/common/ui";
import { useToast } from "@/components/common/Toast";
import { ApiError, post } from "@/lib/api";
import { fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface PH {
  repository: { total_resources: number; verified: number; public_source: number; partner: number; pending: number; demo: number; synthetic: number;
    failed_ingestion: number; processing_queue: number; storage: { backend: string; location: string; durable: boolean } };
  ai: { requests: number; retrieval_success: number; insufficient_evidence: number; retrieval_success_rate: number | null; citation_validation_failures: number;
    citation_markers_removed: number; by_strength: Record<string, number>; note: string;
    provider: { llm_configured: boolean; llm_model: string | null; embedding_provider: string };
    visual: { enabled: boolean; reason?: string | null; indexed_media?: number; model?: string }; ocr: { available: boolean; engine: string | null } };
  content: Record<string, number>;
  data_quality: { duplicate_candidates: number; missing_metadata: number; missing_by_field: Record<string, number>; ocr_failures: number; ocr_partial: number; invalid_datasets: number };
}

function Metric({ label, value, warn, href }: { label: string; value: ReactNode; warn?: boolean; href?: string }) {
  const body = (
    <div className={clsx("rounded-xl px-3 py-2", warn ? "bg-[#fbf1df]" : "bg-snow")}>
      <dt className="text-[12px] text-steel">{label}</dt>
      <dd className={clsx("font-display text-[22px] leading-tight", warn ? "text-[#8a5c0c]" : "text-night")}>{value}</dd>
    </div>
  );
  return href ? <Link href={href} className="block hover:ring-1 hover:ring-glacier rounded-xl">{body}</Link> : body;
}

function Panel({ icon: I, title, children }: { icon: typeof Bot; title: string; children: ReactNode }) {
  return (
    <Card className="p-5">
      <h2 className="mb-3 flex items-center gap-2 text-lg text-night"><I className="h-5 w-5 text-cyan-deep" aria-hidden />{title}</h2>
      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">{children}</dl>
    </Card>
  );
}

export function PlatformHealth() {
  const { data: d, error, loading, reload } = useApi<PH>("/api/admin/platform-health");
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (error) return <ErrorState error={error} onRetry={reload} compact />;
  if (loading || !d) return <Skeleton className="h-64 w-full" />;
  const r = d.repository;
  const pct = (v: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);
  return (
    <section aria-label="Platform health" className="grid gap-5 lg:grid-cols-2">
      <Panel icon={Database} title="Repository health">
        <Metric label="Catalogue records" value={fmtNum(r.total_resources)} href="/admin/repository" />
        <Metric label="Verified" value={fmtNum(r.verified)} href="/admin/provenance" />
        <Metric label="Public source" value={fmtNum(r.public_source)} href="/explore?verification=Public+Source" />
        <Metric label="Pending" value={fmtNum(r.pending)} warn={r.pending > 0} href="/admin/provenance" />
        <Metric label="Demo / synthetic" value={`${fmtNum(r.demo)} / ${fmtNum(r.synthetic)}`} />
        <Metric label="Failed ingestion" value={fmtNum(r.failed_ingestion)} warn={r.failed_ingestion > 0} />
        <Metric label="Processing queue" value={fmtNum(r.processing_queue)} />
        <Metric label="Storage" value={<span className="text-[15px]">{r.storage.backend}{r.storage.durable ? "" : " (not durable)"}</span>} warn={!r.storage.durable} />
      </Panel>
      <Panel icon={Bot} title="AI health">
        <Metric label="AI requests" value={fmtNum(d.ai.requests)} />
        <Metric label="Retrieval success" value={pct(d.ai.retrieval_success_rate)} />
        <Metric label="Insufficient evidence" value={fmtNum(d.ai.insufficient_evidence)} />
        <Metric label="Citation validation failures" value={fmtNum(d.ai.citation_validation_failures)} warn={d.ai.citation_validation_failures > 0} />
        <Metric label="LLM" value={<span className="text-[15px]">{d.ai.provider.llm_configured ? d.ai.provider.llm_model : "not configured"}</span>} />
        <Metric label="Visual search" value={<span className="text-[15px]">{d.ai.visual.enabled ? `${d.ai.visual.indexed_media ?? 0} media` : "unavailable"}</span>} warn={!d.ai.visual.enabled} />
        <Metric label="OCR" value={<span className="text-[15px]">{d.ai.ocr.available ? "available" : "unavailable"}</span>} warn={!d.ai.ocr.available} />
        <div className="col-span-2 sm:col-span-4">
          <Button size="sm" variant="secondary" loading={busy} disabled={!d.ai.visual.enabled} icon={<RefreshCw className="h-3.5 w-3.5" />}
            onClick={async () => { setBusy(true); try { const o = await post<{ vectors: number; media: number }>("/api/admin/visual/reindex"); toast("success", "Visual index rebuilt", `${o.vectors} vectors for ${o.media} media`); reload(); } catch (e) { toast("error", "Rebuild failed", (e as ApiError).message); } finally { setBusy(false); } }}>
            Rebuild visual index
          </Button>
        </div>
      </Panel>
      <Panel icon={Megaphone} title="Content">
        <Metric label="Draft" value={fmtNum(d.content.draft)} href="/studio" />
        <Metric label="Pending review" value={fmtNum(d.content.pending_review)} warn={d.content.pending_review > 0} href="/review" />
        <Metric label="Approved" value={fmtNum(d.content.approved)} href="/review" />
        <Metric label="Published" value={fmtNum(d.content.published)} href="/outreach" />
      </Panel>
      <Panel icon={FileWarning} title="Data quality">
        <Metric label="Duplicate candidates" value={fmtNum(d.data_quality.duplicate_candidates)} warn={d.data_quality.duplicate_candidates > 0} />
        <Metric label="Missing metadata" value={fmtNum(d.data_quality.missing_metadata)} warn={d.data_quality.missing_metadata > 0} />
        <Metric label="OCR failures" value={fmtNum(d.data_quality.ocr_failures)} warn={d.data_quality.ocr_failures > 0} />
        <Metric label="Invalid datasets" value={fmtNum(d.data_quality.invalid_datasets)} warn={d.data_quality.invalid_datasets > 0} />
        {Object.keys(d.data_quality.missing_by_field).length > 0 && (
          <p className="col-span-2 text-[11.5px] text-steel sm:col-span-4">Most often missing: {Object.entries(d.data_quality.missing_by_field).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => `${k} (${v})`).join(", ")}</p>
        )}
      </Panel>
    </section>
  );
}
