"use client";

import { Archive, ArchiveRestore, Pencil, Plus, Star, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Field, Modal, PageHeader, Skeleton, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { VerificationBadge } from "@/components/provenance/Provenance";
import { ApiError, api, del, patch, post, put } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Activity } from "@/lib/types";

interface Opt { slug: string; name: string }
interface Options { stations: Opt[]; expeditions: Opt[]; researchers: Opt[]; topics: Opt[] }
const EMPTY = { title: "", description: "", activity_type: "workshop", date: "", end_date: "", location: "", organisation: "", department: "",
  audience: "", outcomes: "", status: "completed", visibility: "public", featured: false, region: "India", topics: [] as string[],
  researchers: [] as string[], expeditions: [] as string[], stations: [] as string[], documents: "", datasets: "", media: "" };
type Form = typeof EMPTY;

function Multi({ label, options, value, onChange }: { label: string; options: Opt[]; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <Field label={label} hint="Ctrl/Cmd-click to choose several">
      <select multiple className={`${inputCls} h-24`} value={value} onChange={(e) => onChange(Array.from(e.target.selectedOptions).map((o) => o.value))}>
        {options.map((o) => <option key={o.slug} value={o.slug}>{o.name}</option>)}
      </select>
    </Field>
  );
}

function ActivityForm({ initial, editing, onClose, onSaved }: { initial: Form; editing: string | null; onClose: () => void; onSaved: () => void }) {
  const toast = useToast();
  const types = useApi<{ types: { key: string; label: string }[] }>("/api/activities/types");
  const opts = useApi<Options>("/api/media-options");
  const [f, setF] = useState<Form>(initial);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k: keyof Form) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
  const save = async () => {
    setBusy(true);
    setErr("");
    const body = { ...f, end_date: f.end_date || null, outcomes: f.outcomes.split("\n").map((x) => x.trim()).filter(Boolean),
      documents: list(f.documents), datasets: list(f.datasets), media: list(f.media) };
    try {
      if (editing) await put(`/api/activities/${editing}`, body);
      else await post("/api/activities", body);
      toast("success", editing ? "Activity updated" : "Activity created", "Indexed for search and recorded in the audit log.");
      onSaved();
      onClose();
    } catch (e) {
      setErr((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open onClose={onClose} title={editing ? "Edit activity" : "New institutional activity"} wide>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="md:col-span-2"><Field label="Title"><input className={inputCls} value={f.title} onChange={set("title")} /></Field></div>
        <div className="md:col-span-2"><Field label="Description"><textarea className={inputCls} rows={3} value={f.description} onChange={set("description")} /></Field></div>
        <Field label="Activity type">
          <select className={inputCls} value={f.activity_type} onChange={set("activity_type")}>{types.data?.types.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</select>
        </Field>
        <Field label="Status">
          <select className={inputCls} value={f.status} onChange={set("status")}><option value="upcoming">Upcoming</option><option value="ongoing">Ongoing</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select>
        </Field>
        <Field label="Start date"><input type="date" className={inputCls} value={f.date} onChange={set("date")} /></Field>
        <Field label="End date (optional)"><input type="date" className={inputCls} value={f.end_date} onChange={set("end_date")} /></Field>
        <Field label="Organisation"><input className={inputCls} value={f.organisation} onChange={set("organisation")} /></Field>
        <Field label="Department"><input className={inputCls} value={f.department} onChange={set("department")} /></Field>
        <Field label="Location"><input className={inputCls} value={f.location} onChange={set("location")} /></Field>
        <Field label="Region">
          <select className={inputCls} value={f.region} onChange={set("region")}>{["India", "Antarctic", "Arctic", "Southern Ocean", "Himalaya"].map((r) => <option key={r}>{r}</option>)}</select>
        </Field>
        <Field label="Audience"><input className={inputCls} value={f.audience} onChange={set("audience")} /></Field>
        <Field label="Visibility">
          <select className={inputCls} value={f.visibility} onChange={set("visibility")}><option value="public">Public</option><option value="internal">Internal</option></select>
        </Field>
        <div className="md:col-span-2"><Field label="Outcomes (one per line)"><textarea className={inputCls} rows={2} value={f.outcomes} onChange={set("outcomes")} /></Field></div>
        <Multi label="Researchers" options={opts.data?.researchers || []} value={f.researchers} onChange={(v) => setF({ ...f, researchers: v })} />
        <Multi label="Expeditions" options={opts.data?.expeditions || []} value={f.expeditions} onChange={(v) => setF({ ...f, expeditions: v })} />
        <Multi label="Stations" options={opts.data?.stations || []} value={f.stations} onChange={(v) => setF({ ...f, stations: v })} />
        <Multi label="Topics" options={opts.data?.topics || []} value={f.topics} onChange={(v) => setF({ ...f, topics: v })} />
        <Field label="Document slugs" hint="Comma separated"><input className={inputCls} value={f.documents} onChange={set("documents")} /></Field>
        <Field label="Dataset slugs" hint="Comma separated"><input className={inputCls} value={f.datasets} onChange={set("datasets")} /></Field>
        <Field label="Media slugs" hint="Comma separated"><input className={inputCls} value={f.media} onChange={set("media")} /></Field>
        <label className="flex items-center gap-2 self-end pb-2 text-[13.5px]"><input type="checkbox" checked={f.featured} onChange={(e) => setF({ ...f, featured: e.target.checked })} /> Featured</label>
      </div>
      {err && <p role="alert" className="mt-3 rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
      <div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save}>{editing ? "Save changes" : "Create activity"}</Button></div>
    </Modal>
  );
}

function ManageActivities() {
  const toast = useToast();
  const [tick, setTick] = useState(0);
  const [form, setForm] = useState<{ initial: Form; editing: string | null } | null>(null);
  const [confirm, setConfirm] = useState<Activity | null>(null);
  const { data, error, loading, reload } = useApi<{ results: Activity[] }>("/api/activities", { page_size: 60, sort: "newest" }, [tick]);
  const archived = useApi<{ results: Activity[] }>("/api/activities", { page_size: 60, status: "archived" }, [tick]);
  const refresh = () => setTick((t) => t + 1);
  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try { await fn(); toast("success", ok); refresh(); } catch (e) { toast("error", "Action failed", (e as ApiError).message); }
  };
  const openEdit = async (a: Activity) => {
    const d = await api<Activity & { related: { groups: Record<string, { slug: string }[]> }; topics: { slug: string }[] }>(`/api/activities/${a.slug}`);
    const g = (k: string) => (d.related.groups[k] || []).map((x) => x.slug);
    setForm({ editing: a.slug, initial: { ...EMPTY, title: d.title, description: d.description, activity_type: d.activity_type, date: d.date || "",
      end_date: d.end_date || "", location: d.location, organisation: d.organisation, department: d.department, audience: d.audience,
      outcomes: d.outcomes.join("\n"), status: d.status === "archived" ? "completed" : d.status, visibility: d.visibility, featured: d.featured,
      region: d.region, topics: d.topics.map((t) => t.slug), researchers: g("researcher"), expeditions: g("expedition"), stations: g("station"),
      documents: g("document").join(", "), datasets: g("dataset").join(", "), media: g("media").join(", ") } });
  };
  const rows = [...(data?.results || []), ...(archived.data?.results || []).filter((a) => !data?.results.some((x) => x.id === a.id))];
  return (
    <Container className="max-w-[1300px]">
      <PageHeader eyebrow="Governance" title="Manage Institutional Activities" description="Create, edit, feature, archive and delete activities. Every action is audit-logged; verification is handled in the Provenance Centre."
        actions={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setForm({ initial: EMPTY, editing: null })}>New activity</Button>} />
      {error ? <ErrorState error={error} onRetry={reload} /> : loading && !data ? <Skeleton className="h-96 w-full" /> : !rows.length ? <EmptyState title="No activities yet" /> : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-[13px]">
            <thead className="border-b border-frost bg-snow font-mono text-[10.5px] uppercase tracking-wider text-steel">
              <tr><th scope="col" className="px-4 py-2.5">Activity</th><th scope="col" className="px-4 py-2.5">Date</th><th scope="col" className="px-4 py-2.5">Status</th><th scope="col" className="px-4 py-2.5">Verification</th><th scope="col" className="px-4 py-2.5 text-right">Actions</th></tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className="border-b border-frost/70 last:border-0">
                  <td className="max-w-[380px] px-4 py-2.5"><Link href={a.url} className="font-medium text-night hover:text-cyan-deep">{a.title}</Link><span className="block text-[11.5px] text-steel">{a.activity_type_label} · {a.organisation}</span></td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-ink-soft">{fmtDate(a.date)}</td>
                  <td className="px-4 py-2.5"><span className="flex flex-wrap gap-1"><Badge tone={a.status === "archived" ? "slate" : a.status === "upcoming" ? "teal" : "cyan"}>{a.status}</Badge>{a.featured && <Badge tone="amber">featured</Badge>}</span></td>
                  <td className="px-4 py-2.5"><VerificationBadge status={a.verification} label={a.verification_label} /></td>
                  <td className="px-4 py-2.5">
                    <div className="flex justify-end gap-1">
                      <Button size="sm" variant="ghost" aria-label={`Edit ${a.title}`} onClick={() => openEdit(a)} icon={<Pencil className="h-3.5 w-3.5" />} />
                      <Button size="sm" variant="ghost" aria-label={a.featured ? "Unfeature" : "Feature"} onClick={() => act(() => patch(`/api/activities/${a.slug}`, { featured: !a.featured }), a.featured ? "Unfeatured" : "Featured")} icon={<Star className={`h-3.5 w-3.5 ${a.featured ? "fill-current text-amber" : ""}`} />} />
                      {a.status === "archived"
                        ? <Button size="sm" variant="ghost" aria-label="Restore" onClick={() => act(() => patch(`/api/activities/${a.slug}`, { status: "completed" }), "Restored")} icon={<ArchiveRestore className="h-3.5 w-3.5" />} />
                        : <Button size="sm" variant="ghost" aria-label="Archive" onClick={() => act(() => patch(`/api/activities/${a.slug}`, { status: "archived" }), "Archived")} icon={<Archive className="h-3.5 w-3.5" />} />}
                      <Button size="sm" variant="ghost" className="text-coral" aria-label={`Delete ${a.title}`} onClick={() => setConfirm(a)} icon={<Trash2 className="h-3.5 w-3.5" />} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {form && <ActivityForm initial={form.initial} editing={form.editing} onClose={() => setForm(null)} onSaved={refresh} />}
      <ConfirmDialog open={!!confirm} title="Delete this activity?" body={<>“{confirm?.title}” and its links will be permanently removed. Archiving keeps it restorable.</>}
        confirmLabel="Delete permanently" danger onCancel={() => setConfirm(null)}
        onConfirm={() => { const a = confirm!; setConfirm(null); act(() => del(`/api/activities/${a.slug}`), "Activity deleted"); }} />
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="manage_repository" title="Manage Activities"><ManageActivities /></RequireAuth>;
}
