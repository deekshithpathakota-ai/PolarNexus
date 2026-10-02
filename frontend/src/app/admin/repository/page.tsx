"use client";

import clsx from "clsx";
import { Archive, Pencil, Plus, RefreshCw, RotateCcw, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Badge, Button, Card, ConfirmDialog, DemoBadge, EmptyState, ErrorState, Field, LinkButton, Modal, PageHeader, Pagination, Skeleton, Tabs, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { del, post, patch } from "@/lib/api";
import { fmtNum, timeAgo } from "@/lib/format";
import { useApi, useDebounced } from "@/lib/hooks";

type Kind = "document" | "dataset" | "media" | "expedition" | "station";
interface Row { id: number; slug: string; title: string; region: string; year: number | null; status: string; visibility: string; kind: string; is_demo: boolean; views: number; chunks: number; updated_at: string; abstract: string; keywords: string[] }
const PATH: Record<Kind, string> = { document: "/resources", dataset: "/datasets", media: "/media", expedition: "/expeditions", station: "/stations" };

function EditModal({ kind, row, onClose, onSaved }: { kind: Kind; row: Row; onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const [f, setF] = useState({ title: row.title, text: row.abstract || "", region: row.region, year: row.year ? String(row.year) : "", keywords: (row.keywords || []).join(", "), visibility: row.visibility });
  const [busy, setBusy] = useState(false);
  const textField = kind === "document" ? "abstract" : "description";
  return (
    <Modal open onClose={onClose} title={`Edit metadata — ${kind}`} wide>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="md:col-span-2"><Field label="Title"><input className={inputCls} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field></div>
        {(kind === "document" || kind === "dataset" || kind === "media" || kind === "station") && (
          <div className="md:col-span-2"><Field label={kind === "document" ? "Abstract" : "Description"} hint="Saving re-indexes this record for search and AI."><textarea rows={5} className={inputCls} value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} /></Field></div>
        )}
        <Field label="Region">
          <select className={inputCls} value={f.region} onChange={(e) => setF({ ...f, region: e.target.value })}>
            {["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"].map((r) => <option key={r}>{r}</option>)}
          </select>
        </Field>
        {row.year !== null && <Field label="Year"><input className={inputCls} inputMode="numeric" value={f.year} onChange={(e) => setF({ ...f, year: e.target.value.replace(/\D/g, "").slice(0, 4) })} /></Field>}
        {(kind === "document" || kind === "dataset") && <Field label="Keywords" hint="Comma separated"><input className={inputCls} value={f.keywords} onChange={(e) => setF({ ...f, keywords: e.target.value })} /></Field>}
        {(kind === "document" || kind === "dataset" || kind === "media") && (
          <Field label="Visibility"><select className={inputCls} value={f.visibility} onChange={(e) => setF({ ...f, visibility: e.target.value })}><option value="public">Public</option><option value="internal">Internal</option></select></Field>
        )}
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button loading={busy} onClick={async () => {
          setBusy(true);
          try {
            const body: Record<string, unknown> = { title: f.title, region: f.region };
            if (row.year !== null && f.year) body.year = Number(f.year);
            if (f.text && f.text !== row.abstract) body[textField] = f.text;
            if (kind === "document" || kind === "dataset") body.keywords = f.keywords.split(",").map((k) => k.trim()).filter(Boolean);
            if (kind === "document" || kind === "dataset" || kind === "media") body.visibility = f.visibility;
            await patch(`/api/admin/resources/${kind}/${row.id}`, body);
            toast("success", "Metadata saved", "The record was re-indexed.");
            onSaved();
          } catch (e) { toast("error", "Could not save", (e as Error).message); } finally { setBusy(false); }
        }}>Save metadata</Button>
      </div>
    </Modal>
  );
}

function CreateDoc({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const topics = useApi<{ results: { slug: string; name: string }[] }>("/api/topics");
  const [f, setF] = useState({ title: "", doc_type: "Technical Report", abstract: "", content: "", region: "Antarctic", year: String(new Date().getFullYear()), authors: "", keywords: "", topics: [] as string[] });
  const [busy, setBusy] = useState(false);
  return (
    <Modal open onClose={onClose} title="Add resource (metadata + text)" wide>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="md:col-span-2"><Field label="Title"><input className={inputCls} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field></div>
        <Field label="Type"><select className={inputCls} value={f.doc_type} onChange={(e) => setF({ ...f, doc_type: e.target.value })}>{["Research Paper", "Technical Report", "Expedition Report", "Educational Resource", "News / Outreach"].map((t) => <option key={t}>{t}</option>)}</select></Field>
        <Field label="Region"><select className={inputCls} value={f.region} onChange={(e) => setF({ ...f, region: e.target.value })}>{["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"].map((t) => <option key={t}>{t}</option>)}</select></Field>
        <Field label="Year"><input className={inputCls} value={f.year} onChange={(e) => setF({ ...f, year: e.target.value.replace(/\D/g, "").slice(0, 4) })} /></Field>
        <Field label="Authors" hint="Comma separated"><input className={inputCls} value={f.authors} onChange={(e) => setF({ ...f, authors: e.target.value })} /></Field>
        <div className="md:col-span-2"><Field label="Abstract" hint="At least 20 characters"><textarea rows={3} className={inputCls} value={f.abstract} onChange={(e) => setF({ ...f, abstract: e.target.value })} /></Field></div>
        <div className="md:col-span-2"><Field label="Full text (optional)" hint="Use '## Heading' lines to mark sections."><textarea rows={6} className={clsx(inputCls, "font-mono text-[12.5px]")} value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })} /></Field></div>
        <Field label="Keywords"><input className={inputCls} value={f.keywords} onChange={(e) => setF({ ...f, keywords: e.target.value })} /></Field>
        <Field label="Topic"><select className={inputCls} value={f.topics[0] || ""} onChange={(e) => setF({ ...f, topics: e.target.value ? [e.target.value] : [] })}><option value="">—</option>{topics.data?.results.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}</select></Field>
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button loading={busy} disabled={f.title.length < 3 || f.abstract.length < 20} onClick={async () => {
          setBusy(true);
          try {
            const r = await post<{ slug: string; chunks: number }>("/api/resources", { ...f, year: Number(f.year), authors: f.authors.split(",").map((s) => s.trim()).filter(Boolean), keywords: f.keywords.split(",").map((s) => s.trim()).filter(Boolean) });
            toast("success", "Resource added", `Indexed as ${r.chunks} passages.`);
            onSaved();
          } catch (e) { toast("error", "Could not add resource", (e as Error).message); } finally { setBusy(false); }
        }}>Add & index</Button>
      </div>
    </Modal>
  );
}

function Repository() {
  const [kind, setKind] = useState<Kind>("document");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const dq = useDebounced(q);
  const { data, error, loading, reload } = useApi<{ total: number; page: number; pages: number; results: Row[] }>("/api/admin/repository", { kind, q: dq, status, page, page_size: 15 }, [tick]);
  const toast = useToast();
  const [edit, setEdit] = useState<Row | null>(null);
  const [create, setCreate] = useState(false);
  const [confirm, setConfirm] = useState<{ row: Row; hard: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = () => setTick((t) => t + 1);

  return (
    <Container className="max-w-[1400px]">
      <PageHeader eyebrow="Administration" title="Repository Management" description="Add, edit, archive and re-index knowledge records. Destructive actions always ask for confirmation and are written to the audit log."
        actions={<>
          <LinkButton href="/workspace" variant="secondary" icon={<Upload className="h-4 w-4" />}>Upload document</LinkButton>
          <Button variant="secondary" loading={busy} icon={<RefreshCw className="h-4 w-4" />} onClick={async () => {
            setBusy(true);
            try { const r = await post<{ chunks: number; embedding_model: string }>("/api/admin/reindex"); toast("success", "Index rebuilt", `${r.chunks} passages · ${r.embedding_model}`); refresh(); }
            catch (e) { toast("error", "Re-index failed", (e as Error).message); } finally { setBusy(false); }
          }}>Rebuild index</Button>
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreate(true)}>Add resource</Button>
        </>} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Tabs value={kind} onChange={(k) => { setKind(k); setPage(1); }} tabs={(["document", "dataset", "media", "expedition", "station"] as Kind[]).map((k) => ({ key: k, label: `${k[0].toUpperCase()}${k.slice(1)}s` }))} />
        <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Filter by title…" className={clsx(inputCls, "max-w-xs")} aria-label="Filter by title" />
        {(kind === "document" || kind === "dataset") && (
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="h-9 rounded-lg border border-frost bg-white px-2.5 text-[13px]" aria-label="Status">
            <option value="">All statuses</option><option value="indexed">Indexed</option><option value="archived">Archived</option><option value="processing">Processing</option><option value="failed">Failed</option>
          </select>
        )}
        {data && <span className="ml-auto text-[13px] text-steel">{fmtNum(data.total)} records</span>}
      </div>
      {error ? <ErrorState error={error} onRetry={reload} /> : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-[13.5px]">
              <thead className="bg-snow font-mono text-[11px] uppercase tracking-wide text-steel">
                <tr><th className="px-4 py-3">Title</th><th className="px-3 py-3">Type</th><th className="px-3 py-3">Region</th><th className="px-3 py-3">Year</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Passages</th><th className="px-3 py-3">Views</th><th className="px-3 py-3">Updated</th><th className="px-4 py-3 text-right">Actions</th></tr>
              </thead>
              <tbody>
                {loading && !data ? Array.from({ length: 6 }).map((_, i) => <tr key={i}><td colSpan={9} className="px-4 py-3"><Skeleton className="h-5" /></td></tr>) :
                  data?.results.length === 0 ? <tr><td colSpan={9} className="p-6"><EmptyState title="No records" body="Try another filter." /></td></tr> :
                  data?.results.map((r) => (
                    <tr key={r.id} className="border-t border-frost/70 hover:bg-snow/60">
                      <td className="max-w-[360px] px-4 py-3">
                        <Link href={`${PATH[kind]}/${r.slug}`} className="line-clamp-1 font-medium text-night hover:text-cyan-deep">{r.title}</Link>
                        <span className="mt-0.5 flex gap-1.5">{r.is_demo && <DemoBadge label="Demo" />}{r.visibility === "internal" && <Badge tone="amber">Internal</Badge>}</span>
                      </td>
                      <td className="px-3 py-3 text-ink-soft">{r.kind}</td>
                      <td className="px-3 py-3 text-ink-soft">{r.region}</td>
                      <td className="px-3 py-3 font-mono text-[12.5px]">{r.year ?? "—"}</td>
                      <td className="px-3 py-3"><Badge tone={r.status === "indexed" ? "teal" : r.status === "archived" ? "slate" : r.status === "failed" ? "coral" : "cyan"}>{r.status}</Badge></td>
                      <td className="px-3 py-3 font-mono text-[12.5px]">{r.chunks}</td>
                      <td className="px-3 py-3 font-mono text-[12.5px]">{fmtNum(r.views)}</td>
                      <td className="px-3 py-3 text-[12.5px] text-steel">{timeAgo(r.updated_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1">
                          <button aria-label={`Edit ${r.title}`} onClick={() => setEdit(r)} className="rounded-lg p-1.5 text-steel hover:bg-ice hover:text-night"><Pencil className="h-4 w-4" /></button>
                          {r.status === "archived" ? (
                            <button aria-label="Restore" title="Restore" onClick={async () => { try { await post(`/api/admin/resources/${kind}/${r.id}/restore`); toast("success", "Restored and re-indexed"); refresh(); } catch (e) { toast("error", "Restore failed", (e as Error).message); } }} className="rounded-lg p-1.5 text-steel hover:bg-ice hover:text-teal"><RotateCcw className="h-4 w-4" /></button>
                          ) : (kind === "document" || kind === "dataset") && (
                            <button aria-label="Archive" title="Archive" onClick={() => setConfirm({ row: r, hard: false })} className="rounded-lg p-1.5 text-steel hover:bg-ice hover:text-amber"><Archive className="h-4 w-4" /></button>
                          )}
                          <button aria-label="Delete permanently" title="Delete permanently" onClick={() => setConfirm({ row: r, hard: true })} className="rounded-lg p-1.5 text-steel hover:bg-[#fbe9e5] hover:text-coral"><Trash2 className="h-4 w-4" /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {data && <Pagination page={data.page} pages={data.pages} onPage={setPage} />}
      {edit && <EditModal kind={kind} row={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); refresh(); }} />}
      {create && <CreateDoc onClose={() => setCreate(false)} onSaved={() => { setCreate(false); setKind("document"); refresh(); }} />}
      <ConfirmDialog open={!!confirm} danger={confirm?.hard} loading={busy}
        title={confirm?.hard ? "Delete permanently?" : "Archive this record?"}
        body={confirm?.hard ? <>“{confirm?.row.title}” and its passages, links and topic tags will be removed. This cannot be undone.</> : <>“{confirm?.row.title}” will be hidden from search and the AI assistant. You can restore it later.</>}
        confirmLabel={confirm?.hard ? "Delete permanently" : "Archive"}
        onCancel={() => setConfirm(null)}
        onConfirm={async () => {
          if (!confirm) return;
          setBusy(true);
          try { await del(`/api/admin/resources/${kind}/${confirm.row.id}${confirm.hard ? "?hard=true" : ""}`); toast("success", confirm.hard ? "Deleted" : "Archived"); setConfirm(null); refresh(); }
          catch (e) { toast("error", "Action failed", (e as Error).message); } finally { setBusy(false); }
        }} />
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="manage_repository" title="Repository Management"><Repository /></RequireAuth>;
}
