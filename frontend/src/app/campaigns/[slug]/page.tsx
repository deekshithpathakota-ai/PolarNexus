"use client";

import { Archive, CalendarCheck, CircleAlert, FlaskConical, Globe2, Plus, Send, X } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ContentCalendar, ITEM_STATUS_STYLE } from "@/components/campaigns/ContentCalendar";
import { CAMPAIGN_TONE, type CampaignOptions } from "@/components/campaigns/shared";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { Badge, Button, Card, Field, Modal, StatusBadge, Tabs, inputCls } from "@/components/common/ui";
import { useToast } from "@/components/common/Toast";
import { Container } from "@/components/layout/AppShell";
import { ApiError, del, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { CampaignItemT, CampaignT } from "@/lib/types";

function ItemEditor({ campaign, item, opts, onClose, onSaved }: {
  campaign: CampaignT; item: CampaignItemT | null; opts: CampaignOptions; onClose: () => void; onSaved: () => void;
}) {
  const toast = useToast();
  const { can } = useAuth();
  const [f, setF] = useState({
    title: item?.title || "", content_id: item?.content?.id ? String(item.content.id) : "", channel: item?.channel || campaign.channels[0]?.key || "website",
    audience: item?.audience || campaign.audiences[0]?.key || "", scheduled_for: item?.scheduled_for || campaign.start_date || "", notes: item?.notes || "",
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const body = { ...f, content_id: f.content_id ? Number(f.content_id) : null, scheduled_for: f.scheduled_for || null };
  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label);
    setErr("");
    try {
      await fn();
      toast("success", label);
      onSaved();
      onClose();
    } catch (e) {
      setErr((e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };
  const content = opts.content.find((c) => String(c.id) === f.content_id);
  const ready = content && ["approved", "published"].includes(content.status);
  return (
    <Modal open onClose={onClose} title={item ? "Calendar item" : "Add calendar item"} wide>
      <div className="space-y-4">
        <Field label="Title"><input className={inputCls} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Sea Ice Explainer" /></Field>
        <Field label="Outreach content" hint="Only content approved by an editor can be scheduled or published.">
          <select className={inputCls} value={f.content_id} onChange={(e) => setF({ ...f, content_id: e.target.value })}>
            <option value="">— none yet (planning only) —</option>
            {opts.content.map((c) => <option key={c.id} value={c.id}>{c.title} · {c.status.replace(/_/g, " ")}</option>)}
          </select>
        </Field>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Date"><input type="date" className={inputCls} value={f.scheduled_for} onChange={(e) => setF({ ...f, scheduled_for: e.target.value })} /></Field>
          <Field label="Channel">
            <select className={inputCls} value={f.channel} onChange={(e) => setF({ ...f, channel: e.target.value })}>
              {opts.channels.map((c) => <option key={c.key} value={c.key}>{c.label}{c.live ? "" : " (simulated)"}</option>)}
            </select>
          </Field>
          <Field label="Audience">
            <select className={inputCls} value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })}>
              <option value="">—</option>
              {opts.audiences.map((a) => <option key={a.key} value={a.key}>{a.label}</option>)}
            </select>
          </Field>
        </div>
        <Field label="Notes"><textarea className={`${inputCls} h-16 py-2`} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        {content && !ready && (
          <p className="flex items-start gap-2 rounded-lg bg-[#fbf1df] px-3 py-2 text-[13px] text-[#7a520b]"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            This content is “{content.status.replace(/_/g, " ")}”. Submit it for review in the <Link href="/studio" className="underline">Content Studio</Link>; it can be scheduled after an editor approves it.</p>
        )}
        {f.channel !== "website" && <p className="text-[12.5px] text-[#8a5c0c]">Publishing to {opts.channels.find((c) => c.key === f.channel)?.label} is a prototype simulation — no external account is connected. The website feed is live.</p>}
        {err && <p role="alert" className="rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
        <div className="flex flex-wrap justify-end gap-2">
          {item && item.status !== "published" && item.status !== "cancelled" && (
            <Button variant="ghost" loading={busy === "Item cancelled"} icon={<X className="h-4 w-4" />} onClick={() => run("Item cancelled", () => patch(`/api/campaigns/${campaign.slug}/items/${item.id}`, { status: "cancelled" }))}>Cancel item</Button>
          )}
          <Button variant="secondary" loading={busy === "Saved"} onClick={() => run("Saved", () => item ? patch(`/api/campaigns/${campaign.slug}/items/${item.id}`, body) : post(`/api/campaigns/${campaign.slug}/items`, body))}>Save</Button>
          {item && item.status === "planned" && (
            <Button loading={busy === "Scheduled"} disabled={!ready || !f.scheduled_for} icon={<CalendarCheck className="h-4 w-4" />}
              onClick={() => run("Scheduled", () => patch(`/api/campaigns/${campaign.slug}/items/${item.id}`, { ...body, status: "scheduled" }))}>Schedule</Button>
          )}
          {item && item.status === "scheduled" && can("publish") && (
            <Button variant="dark" loading={busy === "Published"} icon={<Send className="h-4 w-4" />}
              onClick={() => run("Published", () => post(`/api/campaigns/${campaign.slug}/items/${item.id}/publish`))}>Publish now</Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

export default function CampaignPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: c, error, loading, reload } = useApi<CampaignT>(`/api/campaigns/${slug}`);
  const opts = useApi<CampaignOptions>("/api/campaigns/options");
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [month, setMonth] = useState<Date | null>(null);
  const [editing, setEditing] = useState<CampaignItemT | "new" | null>(null);
  const toast = useToast();
  const { can } = useAuth();
  if (loading && !c) return <DetailSkeleton />;
  if (error || !c) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/campaigns", label: "Back to campaigns" }} />;
  const m = month || new Date(`${(c.start_date || new Date().toISOString()).slice(0, 7)}-01T00:00:00`);
  const setStatus = async (status: string) => {
    try {
      await patch(`/api/campaigns/${c.slug}`, { status });
      toast("success", `Campaign ${status}`);
      reload();
    } catch (e) {
      toast("error", "Status not changed", (e as ApiError).message);
    }
  };
  return (
    <Container>
      <BackLink href="/campaigns" label="Back to campaigns" />
      <header className="mb-6">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <Badge tone={CAMPAIGN_TONE[c.status]}>{c.status}</Badge>
          {c.is_demo && <Badge tone="amber" icon={<FlaskConical className="h-3 w-3" />}>Demonstration campaign</Badge>}
          <span className="text-[13px] text-steel">{c.start_date ? `${fmtDate(c.start_date)} – ${fmtDate(c.end_date)}` : "Dates not set"}</span>
        </div>
        <h1 className="text-[30px] leading-tight text-night md:text-[38px]">{c.name}</h1>
        <p className="mt-2 max-w-3xl text-[15px] text-ink-soft">{c.description}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {c.status !== "archived" && <Button size="sm" icon={<Plus className="h-4 w-4" />} onClick={() => setEditing("new")}>Add item</Button>}
          {c.status === "draft" && <Button size="sm" variant="secondary" icon={<CalendarCheck className="h-4 w-4" />} onClick={() => setStatus("scheduled")}>Mark scheduled</Button>}
          {c.status === "scheduled" && can("publish") && <Button size="sm" variant="secondary" icon={<Globe2 className="h-4 w-4" />} onClick={() => setStatus("published")}>Mark published</Button>}
          {c.status !== "archived" && <Button size="sm" variant="ghost" icon={<Archive className="h-4 w-4" />} onClick={async () => { await del(`/api/campaigns/${c.slug}`); toast("success", "Campaign archived"); reload(); }}>Archive</Button>}
        </div>
      </header>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <Card className="min-w-0 p-5">
          <div className="mb-3 flex justify-end"><Tabs value={view} onChange={setView} tabs={[{ key: "calendar", label: "Calendar" }, { key: "list", label: "List" }]} /></div>
          {view === "calendar" ? (
            <ContentCalendar month={m} onMonth={setMonth} items={c.items || []} onSelect={(i) => setEditing(i)} />
          ) : (
            <ul className="divide-y divide-frost">
              {(c.items || []).length === 0 && <li className="py-6 text-center text-[14px] text-steel">No items yet — add the first piece of outreach.</li>}
              {(c.items || []).map((i) => (
                <li key={i.id} className="flex flex-wrap items-center gap-3 py-3">
                  <span className="w-24 font-mono text-[12px] text-steel">{i.scheduled_for ? fmtDate(i.scheduled_for) : "No date"}</span>
                  <button className="min-w-0 flex-1 text-left" onClick={() => setEditing(i)}>
                    <span className="block truncate text-[14px] font-medium text-night hover:text-cyan-deep">{i.title}</span>
                    <span className="text-[12px] text-steel">{i.channel_label}{i.simulated_channels.length ? " (simulated)" : ""} · {i.audience || "any audience"}{i.content ? "" : " · no content linked"}</span>
                  </button>
                  {i.content && <StatusBadge status={i.content.status} />}
                  <span className={`rounded border px-1.5 py-0.5 text-[11.5px] ${ITEM_STATUS_STYLE[i.status]}`}>{i.status}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <aside className="space-y-4">
          <SideCard title="Audience & channels">
            <p className="text-[13px] text-ink-soft">{c.audiences.map((a) => a.label).join(", ") || "No audience set"}</p>
            <ul className="mt-2 space-y-1 text-[13px]">
              {c.channels.map((ch) => <li key={ch.key}>{ch.label} <span className={ch.simulated ? "text-[#8a5c0c]" : "text-teal"}>· {ch.simulated ? "prototype simulation" : "live"}</span></li>)}
            </ul>
          </SideCard>
          <SideCard title="Progress">
            <dl className="grid grid-cols-2 gap-2 text-[13px]">
              {Object.entries(c.item_counts).map(([k, v]) => <div key={k}><dt className="text-steel">{k}</dt><dd className="font-display text-[22px] text-night">{v}</dd></div>)}
            </dl>
          </SideCard>
          <SideCard title="Workflow">
            <p className="text-[12.5px] leading-relaxed text-ink-soft">Content → evidence check → editor review → schedule → publish → <Link href="/outreach-analytics" className="text-cyan-deep hover:underline">measure</Link>. Scheduling and publishing never bypass approval.</p>
          </SideCard>
        </aside>
      </div>
      {editing && opts.data && (
        <ItemEditor campaign={c} item={editing === "new" ? null : editing} opts={opts.data} onClose={() => setEditing(null)} onSaved={reload} />
      )}
    </Container>
  );
}
