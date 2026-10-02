"use client";

import { Activity, Bot, ClipboardCheck, Database, Eye, Layers, Megaphone, Search, Users } from "lucide-react";
import Link from "next/link";
import { Donut, GrowthChart, HBar, UsageChart, VBar, type Analytics } from "@/components/charts/AdminCharts";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { RequireAuth } from "@/components/common/RequireAuth";
import { Card, DemoBadge, ErrorState, PageHeader, Skeleton } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Health } from "@/lib/types";
import { PlatformHealth } from "@/components/admin/PlatformHealth";

function Kpi({ icon: I, label, value, href }: { icon: typeof Eye; label: string; value: string | number; href?: string }) {
  const inner = (
    <Card className="flex items-center gap-4 p-4 transition hover:border-glacier">
      <span className="rounded-xl bg-ice p-2.5 text-cyan-deep"><I className="h-5 w-5" /></span>
      <span>
        <span className="block font-display text-[26px] leading-none text-night">{typeof value === "number" ? fmtNum(value) : value}</span>
        <span className="mt-1 block text-[12.5px] text-steel">{label}</span>
      </span>
    </Card>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

function Dashboard() {
  const { data: a, error, loading, reload } = useApi<Analytics>("/api/analytics", { days: 60 });
  const health = useApi<Health>("/api/health");
  return (
    <Container className="max-w-[1400px]">
      <PageHeader eyebrow="Administration" title="Dashboard" description="Repository, discovery, AI and outreach activity at a glance.">
        <div className="mt-3"><DemoBadge label="Prototype demonstration analytics" /></div>
      </PageHeader>
      {error ? <ErrorState error={error} onRetry={reload} /> : loading || !a ? <Skeleton className="h-[600px] w-full rounded-2xl" /> : (
        <ErrorBoundary label="dashboard">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi icon={Database} label="Total resources" value={a.totals.resources} href="/admin/repository" />
            <Kpi icon={Layers} label="Indexed passages" value={a.totals.indexed_passages} href="/admin/health" />
            <Kpi icon={ClipboardCheck} label="Pending reviews" value={a.totals.pending_reviews} href="/review" />
            <Kpi icon={Megaphone} label="Published content" value={a.totals.published} href="/outreach" />
            <Kpi icon={Users} label="Active users (60 d)" value={a.totals.active_users} href="/admin/users" />
            <Kpi icon={Search} label="Searches (60 d)" value={a.totals.searches} href="/admin/analytics" />
            <Kpi icon={Bot} label="AI questions (60 d)" value={a.totals.ai_questions} href="/admin/analytics" />
            <Kpi icon={Activity} label="System" value={health.data ? (health.data.status === "ok" ? "Healthy" : "Degraded") : "…"} href="/admin/health" />
          </div>
          <div className="mt-5"><PlatformHealth /></div>
          <div className="mt-5 grid gap-5 xl:grid-cols-3">
            <Card className="p-5 xl:col-span-2"><h2 className="mb-2 text-lg text-night">Usage trends</h2><UsageChart data={a.timeline} /></Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">Resource types</h2><Donut data={a.resource_types} height={280} /></Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">Content workflow</h2><VBar data={a.content_workflow} /></Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">Repository growth</h2><GrowthChart data={a.growth} /></Card>
            <Card className="p-5"><h2 className="mb-2 text-lg text-night">Top topics</h2><HBar data={a.topics.slice(0, 7).map((t) => ({ name: t.name, value: t.count }))} height={240} color="#128a87" /></Card>
          </div>
        </ErrorBoundary>
      )}
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="view_analytics" title="Admin Dashboard"><Dashboard /></RequireAuth>;
}
