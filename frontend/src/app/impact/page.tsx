"use client";

import { ArrowRight, Bot, FlaskConical, Gauge, Megaphone, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Card, CardSkeleton, ErrorState, PageHeader, SectionTitle } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Impact {
  label: string; disclaimer: string;
  knowledge: { total: number; by_type: Record<string, number>; by_verification: Record<string, number> };
  ai: { questions_answered: number; evidence_grounded: number; insufficient_evidence: number; by_mode: Record<string, number>;
        live_questions: number; citation_validation_rate: number | null; citation_validation_basis: string };
  content: { drafts_generated: number; evidence_checked: number; evidence_pass: number; reviews_completed: number; approved: number; published: number; by_status: Record<string, number> };
  discovery: { searches: number; resource_views: number; top_searches: { query: string; count: number }[];
               most_accessed: { title: string; url: string; type: string; kind: string; views: number }[] };
  measured: { search_latency_ms: { median: number | null; p90: number | null; samples: number };
              ai_latency_ms: { median: number | null; p90: number | null; samples: number };
              review_turnaround_hours: { median: number | null; samples: number; note: string }; note: string };
  workflow: { stage: string; traditional: string; polarnexus: string }[];
}

function Stat({ label, value, sub, icon }: { label: string; value: ReactNode; sub?: string; icon?: ReactNode }) {
  return (
    <Card className="p-4">
      <p className="flex items-center gap-1.5 font-mono text-[10.5px] uppercase tracking-wider text-steel">{icon}{label}</p>
      <p className="mt-1 font-display text-[28px] leading-tight text-night">{value}</p>
      {sub && <p className="mt-0.5 text-[12px] text-steel">{sub}</p>}
    </Card>
  );
}

/** Single-hue magnitude bars; the value is always printed, so the bar never carries meaning alone. */
function Bars({ data, total }: { data: [string, number][]; total?: number }) {
  const max = Math.max(1, ...data.map((d) => d[1]));
  return (
    <ul className="space-y-2">
      {data.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[minmax(0,150px)_1fr_48px] items-center gap-3 text-[13px]" title={`${k}: ${v}${total ? ` of ${total}` : ""}`}>
          <span className="truncate text-ink-soft">{k}</span>
          <span className="h-2.5 rounded-full bg-ice" aria-hidden><span className="block h-full rounded-full bg-cyan-deep" style={{ width: `${(v / max) * 100}%` }} /></span>
          <span className="text-right font-mono text-[12px] text-night">{fmtNum(v)}</span>
        </li>
      ))}
    </ul>
  );
}

const ms = (v: number | null) => (v == null ? "—" : `${fmtNum(Math.round(v))} ms`);

export default function ImpactPage() {
  const { data: d, error, loading, reload } = useApi<Impact>("/api/impact");
  return (
    <Container>
      <PageHeader eyebrow="Impact & KPIs" title="Platform Impact Dashboard"
        description="What the platform holds, how it is used, and how research moves through evidence checks and human review into outreach.">
        <p className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-dashed border-[#e2c58f] bg-[#fdf8ee] px-3 py-1 font-mono text-[11px] uppercase tracking-wide text-[#8a5c0c]">
          <FlaskConical className="h-3.5 w-3.5" aria-hidden /> {d?.label || "Prototype Demonstration Metrics"}
        </p>
      </PageHeader>
      {error ? <ErrorState error={error} onRetry={reload} /> : loading || !d ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <CardSkeleton key={i} rows={1} />)}</div>
      ) : (
        <div className="space-y-8">
          <p className="max-w-3xl text-[13.5px] text-ink-soft">{d.disclaimer}</p>

          <section>
            <SectionTitle eyebrow="Knowledge" title="Unified repository" />
            <div className="grid gap-4 lg:grid-cols-[260px_1fr_1fr]">
              <Stat label="Knowledge resources" value={fmtNum(d.knowledge.total)} sub="across every resource type" />
              <Card className="p-5"><p className="mb-3 font-mono text-[10.5px] uppercase tracking-wider text-steel">By type</p>
                <Bars data={Object.entries(d.knowledge.by_type).filter(([k]) => k !== "Topics")} /></Card>
              <Card className="p-5"><p className="mb-3 font-mono text-[10.5px] uppercase tracking-wider text-steel">By verification status</p>
                <Bars data={Object.entries(d.knowledge.by_verification)} /></Card>
            </div>
          </section>

          <section>
            <SectionTitle eyebrow="AI usage" title="Evidence-grounded answers" />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Stat icon={<Bot className="h-3.5 w-3.5" />} label="Questions answered" value={fmtNum(d.ai.questions_answered)} sub={`${fmtNum(d.ai.live_questions)} live on this deployment`} />
              <Stat icon={<ShieldCheck className="h-3.5 w-3.5" />} label="Evidence-grounded" value={fmtNum(d.ai.evidence_grounded)} sub="strong or limited evidence" />
              <Stat label="Insufficient evidence" value={fmtNum(d.ai.insufficient_evidence)} sub="the assistant declined to answer" />
              <Stat label="Citation validation" value={d.ai.citation_validation_rate == null ? "—" : `${Math.round(d.ai.citation_validation_rate * 100)}%`} sub={d.ai.citation_validation_basis} />
            </div>
          </section>

          <section>
            <SectionTitle eyebrow="Content workflow" title="Research → outreach" action={<Link href="/outreach" className="inline-flex items-center gap-1 text-[13px] text-cyan-deep hover:underline">Outreach feed <ArrowRight className="h-3.5 w-3.5" /></Link>} />
            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <Stat label="Drafts generated" value={fmtNum(d.content.drafts_generated)} />
              <Stat label="Evidence checked" value={fmtNum(d.content.evidence_checked)} sub={`${fmtNum(d.content.evidence_pass)} passed outright`} />
              <Stat label="Reviews completed" value={fmtNum(d.content.reviews_completed)} />
              <Stat label="Approved" value={fmtNum(d.content.approved)} />
              <Stat icon={<Megaphone className="h-3.5 w-3.5" />} label="Published" value={fmtNum(d.content.published)} sub="after human approval" />
              <Stat label="Auto-published" value="0" sub="by design — review is mandatory" />
            </div>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card className="p-5">
              <SectionTitle eyebrow="Discovery" title="Most searched" />
              <p className="mb-3 text-[12.5px] text-steel">{fmtNum(d.discovery.searches)} searches · {fmtNum(d.discovery.resource_views)} resource views</p>
              <Bars data={d.discovery.top_searches.map((s) => [s.query, s.count])} />
            </Card>
            <Card className="p-5">
              <SectionTitle eyebrow="Discovery" title="Most accessed resources" />
              <ol className="space-y-1.5">
                {d.discovery.most_accessed.map((r, i) => (
                  <li key={r.url} className="flex items-baseline gap-2 text-[13.5px]">
                    <span className="w-5 font-mono text-[11px] text-mist">{i + 1}</span>
                    <Link href={r.url} className="min-w-0 flex-1 truncate text-night hover:text-cyan-deep">{r.title}</Link>
                    <span className="font-mono text-[11.5px] text-steel">{fmtNum(r.views)}</span>
                  </li>
                ))}
              </ol>
            </Card>
          </section>

          <section>
            <SectionTitle eyebrow="Measured on this deployment" title="Performance" />
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat icon={<Search className="h-3.5 w-3.5" />} label="Search latency (median)" value={ms(d.measured.search_latency_ms.median)} sub={`p90 ${ms(d.measured.search_latency_ms.p90)} · ${d.measured.search_latency_ms.samples} live searches`} />
              <Stat icon={<Gauge className="h-3.5 w-3.5" />} label="AI answer latency (median)" value={ms(d.measured.ai_latency_ms.median)} sub={`p90 ${ms(d.measured.ai_latency_ms.p90)} · ${d.measured.ai_latency_ms.samples} live questions`} />
              <Stat label="Review turnaround (median)" value={d.measured.review_turnaround_hours.median == null ? "—" : `${d.measured.review_turnaround_hours.median} h`} sub={d.measured.review_turnaround_hours.note} />
            </div>
            <p className="mt-2 text-[12px] text-steel">{d.measured.note} No timing figure on this page is estimated.</p>
          </section>

          <section>
            <SectionTitle eyebrow="Before / after" title="How the workflow changes" />
            <Card className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-left text-[13.5px]">
                <thead className="border-b border-frost bg-snow font-mono text-[10.5px] uppercase tracking-wider text-steel">
                  <tr><th scope="col" className="px-4 py-2.5">Stage</th><th scope="col" className="px-4 py-2.5">Traditional workflow</th><th scope="col" className="px-4 py-2.5">PolarNexus workflow</th></tr>
                </thead>
                <tbody>
                  {d.workflow.map((w) => (
                    <tr key={w.stage} className="border-b border-frost last:border-0">
                      <th scope="row" className="px-4 py-3 font-medium text-night">{w.stage}</th>
                      <td className="px-4 py-3 text-ink-soft">{w.traditional}</td>
                      <td className="px-4 py-3 text-night">{w.polarnexus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
            <p className="mt-2 text-[12px] text-steel">Qualitative comparison — no time savings are claimed without measurement.</p>
          </section>
        </div>
      )}
    </Container>
  );
}
