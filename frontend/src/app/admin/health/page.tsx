"use client";

import clsx from "clsx";
import { Bot, Database, HardDrive, Layers, RefreshCw, Server } from "lucide-react";
import { useState } from "react";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Button, Card, ConfirmDialog, ErrorState, PageHeader, Skeleton } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { post } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Health } from "@/lib/types";

function Row({ icon: I, title, status, lines }: { icon: typeof Server; title: string; status: string; lines: (string | null)[] }) {
  const ok = ["ok", "configured"].includes(status);
  const fallback = ["fallback", "keyword-only"].includes(status);
  return (
    <Card className="flex items-start gap-4 p-5">
      <span className={clsx("rounded-xl p-2.5", ok ? "bg-[#e2f4f1] text-teal" : fallback ? "bg-[#fbf1df] text-[#8a5c0c]" : "bg-[#fbe9e5] text-coral")}><I className="h-5 w-5" /></span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="font-medium text-night">{title}</p>
          <span className={clsx("rounded-full px-2 py-0.5 font-mono text-[11px] uppercase", ok ? "bg-[#e2f4f1] text-teal" : fallback ? "bg-[#fbf1df] text-[#8a5c0c]" : "bg-[#fbe9e5] text-coral")}>{status}</span>
        </div>
        {lines.filter(Boolean).map((l) => <p key={l} className="mt-1 text-[13px] text-ink-soft">{l}</p>)}
      </div>
    </Card>
  );
}

function HealthPage() {
  const { data: h, error, loading, reload } = useApi<Health>("/api/health");
  const toast = useToast();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  return (
    <Container className="max-w-[1000px]">
      <PageHeader eyebrow="Operations" title="System Health" description="Live status of each service, and which fallbacks are active." actions={<Button variant="secondary" onClick={reload} icon={<RefreshCw className="h-4 w-4" />}>Refresh</Button>} />
      {error ? <ErrorState error={error} onRetry={reload} /> : loading || !h ? <Skeleton className="h-80 w-full rounded-2xl" /> : (
        <div className="grid gap-4 md:grid-cols-2">
          <Row icon={Server} title="API" status={h.api} lines={[`Environment: ${h.environment}`, `Demo mode: ${h.demo_mode ? "on" : "off"}`]} />
          <Row icon={Database} title="Database" status={h.database.status} lines={[`Engine: ${h.database.engine}`]} />
          <Row icon={Layers} title="Vector search" status={h.vector_search.status} lines={[`Backend: ${h.vector_search.backend}`, `Embedding model: ${h.vector_search.embedding_model || "—"}`]} />
          <Row icon={Bot} title="AI provider" status={h.ai_provider.status} lines={[h.ai_provider.model ? `Model: ${h.ai_provider.model}` : null, h.ai_provider.fallback]} />
          <Row icon={HardDrive} title="Storage" status={h.storage.status} lines={[`Backend: ${h.storage.backend}`]} />
          {h.demo_mode && (
            <Card className="p-5">
              <p className="font-medium text-night">Reset demonstration data</p>
              <p className="mt-1 text-[13px] text-ink-soft">Drops all tables and re-seeds the full demo corpus. Use before a live demonstration.</p>
              <Button variant="danger" size="sm" className="mt-3" onClick={() => setConfirm(true)}>Reset & reseed</Button>
            </Card>
          )}
        </div>
      )}
      <ConfirmDialog open={confirm} danger loading={busy} title="Reset all demo data?" confirmLabel="Reset & reseed"
        body="All uploads, drafts, reviews and changes made during this session will be erased and the demo corpus restored. You will be signed out."
        onCancel={() => setConfirm(false)}
        onConfirm={async () => {
          setBusy(true);
          try { await post("/api/admin/reset-demo", undefined, {}); toast("success", "Demo data restored", "Please sign in again."); window.location.href = "/login"; }
          catch (e) { toast("error", "Reset failed", (e as Error).message); setBusy(false); }
        }} />
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="view_analytics" title="System Health"><HealthPage /></RequireAuth>;
}
