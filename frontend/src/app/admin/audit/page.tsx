"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/common/RequireAuth";
import { Badge, Card, EmptyState, ErrorState, PageHeader, Pagination, Skeleton, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useApi, useDebounced } from "@/lib/hooks";

interface Log { id: number; user: string; action: string; resource_type: string; resource_id: string; detail: string; status: string; at: string }

function Audit() {
  const [action, setAction] = useState("");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, error, loading, reload } = useApi<{ total: number; page: number; pages: number; actions: string[]; results: Log[] }>("/api/admin/audit-logs", { action, status, q: dq, page, page_size: 20 });
  return (
    <Container className="max-w-[1300px]">
      <PageHeader eyebrow="Governance" title="Audit Logs" description="Every sign-in, upload, edit, deletion, AI generation, approval, rejection, publication and role change is recorded." />
      <div className="mb-4 flex flex-wrap gap-3">
        <select value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} className="h-10 rounded-lg border border-frost bg-white px-3 text-[13px]" aria-label="Action">
          <option value="">All actions</option>{data?.actions.map((a) => <option key={a}>{a}</option>)}
        </select>
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="h-10 rounded-lg border border-frost bg-white px-3 text-[13px]" aria-label="Status">
          <option value="">Any status</option><option value="success">Success</option><option value="failure">Failure</option>
        </select>
        <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Search user, resource or detail…" className={`${inputCls} max-w-sm`} aria-label="Search logs" />
        {data && <span className="ml-auto self-center text-[13px] text-steel">{data.total} entries</span>}
      </div>
      {error ? <ErrorState error={error} onRetry={reload} /> : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-[13px]">
              <thead className="bg-snow font-mono text-[11px] uppercase tracking-wide text-steel">
                <tr><th className="px-4 py-3">Time</th><th className="px-3 py-3">User</th><th className="px-3 py-3">Action</th><th className="px-3 py-3">Resource</th><th className="px-3 py-3">Detail</th><th className="px-3 py-3">Status</th></tr>
              </thead>
              <tbody>
                {loading && !data ? Array.from({ length: 8 }).map((_, i) => <tr key={i}><td colSpan={6} className="px-4 py-2.5"><Skeleton className="h-5" /></td></tr>) :
                  data?.results.length === 0 ? <tr><td colSpan={6} className="p-6"><EmptyState title="No log entries" body="Adjust the filters." /></td></tr> :
                  data?.results.map((l) => (
                    <tr key={l.id} className="border-t border-frost/70">
                      <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[12px] text-steel">{new Date(l.at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                      <td className="px-3 py-2.5 text-night">{l.user}</td>
                      <td className="px-3 py-2.5"><span className="rounded bg-ice px-1.5 py-0.5 font-mono text-[11.5px] text-deep">{l.action}</span></td>
                      <td className="px-3 py-2.5 text-ink-soft">{l.resource_type}{l.resource_id ? ` · ${l.resource_id}` : ""}</td>
                      <td className="max-w-[340px] truncate px-3 py-2.5 text-ink-soft" title={l.detail}>{l.detail}</td>
                      <td className="px-3 py-2.5"><Badge tone={l.status === "success" ? "teal" : "coral"}>{l.status}</Badge></td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {data && <Pagination page={data.page} pages={data.pages} onPage={setPage} />}
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="view_audit" title="Audit Logs"><Audit /></RequireAuth>;
}
