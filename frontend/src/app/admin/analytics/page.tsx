"use client";

import Link from "next/link";
import { useState } from "react";
import { Donut, HBar, UsageChart, VBar, type Analytics } from "@/components/charts/AdminCharts";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { RequireAuth } from "@/components/common/RequireAuth";
import { Card, DemoBadge, ErrorState, PageHeader, Skeleton, Tabs } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useApi } from "@/lib/hooks";

function AnalyticsPage() {
  const [days, setDays] = useState("60");
  const { data: a, error, loading, reload } = useApi<Analytics>("/api/analytics", { days });
  return (
    <Container className="max-w-[1400px]">
      <PageHeader eyebrow="Insights" title="Analytics" description="How people discover, ask about and share polar knowledge."
        actions={<Tabs value={days} onChange={setDays} tabs={[{ key: "30", label: "30 days" }, { key: "60", label: "60 days" }, { key: "90", label: "90 days" }]} />}>
        <div className="mt-3"><DemoBadge label={a?.label || "Prototype demonstration analytics"} /></div>
      </PageHeader>
      {error ? <ErrorState error={error} onRetry={reload} /> : loading || !a ? <Skeleton className="h-[700px] w-full rounded-2xl" /> : (
        <ErrorBoundary label="analytics">
          <div className="grid gap-5 lg:grid-cols-2">
            <Card className="p-5 lg:col-span-2"><h2 className="mb-2 text-lg text-night">Discovery & AI usage</h2><UsageChart data={a.timeline} /></Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">Most searched topics</h2><HBar data={a.top_searches.map((s) => ({ name: s.query, value: s.count }))} height={300} /></Card>
            <Card className="p-5">
              <h2 className="mb-3 text-lg text-night">Popular resources</h2>
              <ol className="space-y-2">
                {a.popular.map((p, i) => (
                  <li key={p.url} className="flex items-center gap-3 text-[13.5px]">
                    <span className="w-5 font-mono text-[12px] text-mist">{i + 1}</span>
                    <Link href={p.url} className="min-w-0 flex-1 truncate text-night hover:text-cyan-deep">{p.title}</Link>
                    <span className="font-mono text-[12px] text-steel">{p.views}</span>
                  </li>
                ))}
              </ol>
            </Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">AI answers by evidence strength</h2><Donut data={a.ai.by_evidence} /></Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">AI answer generation mode</h2><Donut data={a.ai.by_mode} /></Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">Search modes used</h2><VBar data={a.search_modes} /></Card>
            <Card className="p-5">
              <h2 className="mb-2 text-lg text-night">Generated content by format</h2>
              <VBar data={a.content_formats} />
              <p className="mt-2 text-[13px] text-steel">Average review turnaround: <strong className="text-night">{a.review_turnaround_hours ?? "—"} h</strong> (submission → approval)</p>
            </Card>
            <Card className="p-5 lg:col-span-2"><h2 className="mb-2 text-lg text-night">Documents by type</h2><VBar data={a.document_types} /></Card>
          </div>
        </ErrorBoundary>
      )}
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="view_analytics" title="Analytics"><AnalyticsPage /></RequireAuth>;
}
