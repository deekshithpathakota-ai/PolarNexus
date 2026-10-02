"use client";

import Link from "next/link";
import { useState } from "react";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Button, Card, EmptyState, ErrorState, Field, Modal, PageHeader, Pagination, Skeleton, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { ProvenancePanel, VerificationBadge } from "@/components/provenance/Provenance";
import { ApiError, patch } from "@/lib/api";
import { useApi, useDebounced } from "@/lib/hooks";
import type { Provenance, VerificationStatus } from "@/lib/types";

type Row = Provenance & { resource_type: string; resource_id: number; title: string; url: string; kind: string; slug: string; is_demo: boolean };
interface Queue { total: number; page: number; pages: number; results: Row[]; counts: Record<string, number>; by_type: Record<string, number>; statuses: { key: string; label: string }[] }
const TYPES = ["document", "dataset", "media", "expedition", "station", "researcher", "activity"];

function Editor({ row, onClose, onSaved }: { row: Row; onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const [f, setF] = useState({ verification_status: row.verification_status as string, source_organisation: row.source_organisation, source_type: row.source_type,
    source_url: row.source_url, license: row.license, data_quality: row.data_quality, provenance_notes: row.provenance_notes, comment: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const demo = row.verification_status === "demo_data" || row.verification_status === "synthetic_demo";
  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      await patch(`/api/admin/provenance/${row.resource_type}/${row.resource_id}`, f);
      toast("success", "Provenance updated", "The change is recorded in the audit log.");
      onSaved();
      onClose();
    } catch (e) {
      setErr((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <Modal open onClose={onClose} title={`Provenance · ${row.title}`} wide>
      <div className="grid gap-5 md:grid-cols-2">
        <div className="space-y-3">
          <Field label="Verification status" hint={demo ? "Demonstration and synthetic records cannot be marked Verified or Partner source." : undefined}>
            <select className={inputCls} value={f.verification_status} onChange={set("verification_status")}>
              {[["verified", "Verified"], ["partner_source", "Partner source"], ["user_uploaded", "User uploaded"], ["pending_review", "Pending review"],
                ["demo_data", "Demo data"], ["synthetic_demo", "Synthetic demonstration"], ["unverified", "Unverified (reject)"]].map(([k, l]) => (
                <option key={k} value={k} disabled={demo && (k === "verified" || k === "partner_source")}>{l}</option>
              ))}
            </select>
          </Field>
          <Field label="Source organisation"><input className={inputCls} value={f.source_organisation} onChange={set("source_organisation")} /></Field>
          <Field label="Source type"><input className={inputCls} value={f.source_type} onChange={set("source_type")} /></Field>
          <Field label="Source URL"><input className={inputCls} value={f.source_url} onChange={set("source_url")} placeholder="https://…" /></Field>
          <Field label="Licence"><input className={inputCls} value={f.license} onChange={set("license")} /></Field>
          <Field label="Data quality"><input className={inputCls} value={f.data_quality} onChange={set("data_quality")} /></Field>
          <Field label="Notes"><textarea className={inputCls} rows={3} value={f.provenance_notes} onChange={set("provenance_notes")} /></Field>
          <Field label="Reason (audit log)"><input className={inputCls} value={f.comment} onChange={set("comment")} placeholder="e.g. Checked against the source PDF" /></Field>
          {err && <p role="alert" className="rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
          <div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save}>Save</Button></div>
        </div>
        <ProvenancePanel p={row} />
      </div>
    </Modal>
  );
}

function ProvenanceCentre() {
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const [edit, setEdit] = useState<Row | null>(null);
  const dq = useDebounced(q);
  const { data, error, loading, reload } = useApi<Queue>("/api/admin/provenance", { status, type, q: dq, page, page_size: 20 }, [tick]);
  return (
    <Container className="max-w-[1300px]">
      <PageHeader eyebrow="Governance" title="Provenance & Verification Centre"
        description="Every knowledge object records where it came from, its licence and how far it has been verified. Demonstration and synthetic records stay labelled — the API refuses to mark them verified." />
      {data && (
        <div className="mb-5 flex flex-wrap gap-2">
          {data.statuses.map((s) => (
            <button key={s.key} aria-pressed={status === s.key} onClick={() => { setStatus(status === s.key ? "" : s.key); setPage(1); }}
              className={`rounded-xl border px-3 py-2 text-left ${status === s.key ? "border-cyan bg-[#f0f9fc]" : "border-frost bg-white hover:border-glacier"}`}>
              <VerificationBadge status={s.key as VerificationStatus} label={s.label} />
              <span className="mt-1 block font-display text-xl text-night">{data.counts[s.key] ?? 0}</span>
            </button>
          ))}
        </div>
      )}
      <div className="mb-4 flex flex-wrap gap-3">
        <select value={type} onChange={(e) => { setType(e.target.value); setPage(1); }} className="h-10 rounded-lg border border-frost bg-white px-3 text-[13px] capitalize" aria-label="Resource type">
          <option value="">All resource types</option>{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Search titles…" className={`${inputCls} max-w-sm`} aria-label="Search records" />
        {data && <span className="ml-auto self-center text-[13px] text-steel">{data.total} records</span>}
      </div>
      {error ? <ErrorState error={error} onRetry={reload} /> : loading && !data ? <Skeleton className="h-96 w-full" /> : !data?.results.length ? <EmptyState title="No records match" /> : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-[13px]">
            <thead className="border-b border-frost bg-snow font-mono text-[10.5px] uppercase tracking-wider text-steel">
              <tr><th scope="col" className="px-4 py-2.5">Record</th><th scope="col" className="px-4 py-2.5">Verification</th><th scope="col" className="px-4 py-2.5">Source</th><th scope="col" className="px-4 py-2.5">Licence</th><th scope="col" className="px-4 py-2.5">Last verified</th><th scope="col" className="px-4 py-2.5"><span className="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              {data.results.map((r) => (
                <tr key={`${r.resource_type}${r.resource_id}`} className="border-b border-frost/70 last:border-0">
                  <td className="max-w-[320px] px-4 py-2.5"><Link href={r.url} className="font-medium text-night hover:text-cyan-deep">{r.title}</Link><span className="block text-[11.5px] capitalize text-steel">{r.resource_type} · {r.kind}</span></td>
                  <td className="px-4 py-2.5"><VerificationBadge status={r.verification_status} label={r.verification_label} official={r.official} /></td>
                  <td className="max-w-[240px] truncate px-4 py-2.5 text-ink-soft" title={r.source_organisation}>{r.source_organisation || "—"}</td>
                  <td className="max-w-[180px] truncate px-4 py-2.5 text-ink-soft" title={r.license}>{r.license || "—"}</td>
                  <td className="px-4 py-2.5 text-ink-soft">{r.last_verified_at ? new Date(r.last_verified_at).toLocaleDateString("en-IN") : "—"}</td>
                  <td className="px-4 py-2.5 text-right"><Button size="sm" variant="secondary" onClick={() => setEdit(r)}>Review</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {data && <Pagination page={data.page} pages={data.pages} onPage={setPage} />}
      {edit && <Editor row={edit} onClose={() => setEdit(null)} onSaved={() => setTick((t) => t + 1)} />}
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="manage_repository" title="Provenance & Verification"><ProvenanceCentre /></RequireAuth>;
}
