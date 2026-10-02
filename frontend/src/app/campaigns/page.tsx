"use client";

import { CalendarDays, FlaskConical, Megaphone, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge, Button, CardSkeleton, EmptyState, ErrorState, Field, LinkButton, Modal, PageHeader, inputCls } from "@/components/common/ui";
import { useToast } from "@/components/common/Toast";
import { Container } from "@/components/layout/AppShell";
import { ApiError, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { CampaignT } from "@/lib/types";
import { CAMPAIGN_TONE, type CampaignOptions } from "@/components/campaigns/shared";

function CreateCampaign({ open, onClose }: { open: boolean; onClose: () => void }) {
  const opts = useApi<CampaignOptions>(open ? "/api/campaigns/options" : null);
  const router = useRouter();
  const toast = useToast();
  const [f, setF] = useState({ name: "", description: "", start_date: "", end_date: "", audiences: [] as string[], topics: [] as string[], channels: ["website"] as string[] });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const toggle = (k: "audiences" | "topics" | "channels", v: string) => setF((x) => ({ ...x, [k]: x[k].includes(v) ? x[k].filter((y) => y !== v) : [...x[k], v] }));
  return (
    <Modal open={open} onClose={onClose} title="New outreach campaign" wide>
      <form className="space-y-4" onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setErr("");
        try {
          const c = await post<CampaignT>("/api/campaigns", { ...f, start_date: f.start_date || null, end_date: f.end_date || null });
          toast("success", "Campaign created");
          router.push(`/campaigns/${c.slug}`);
        } catch (e2) {
          setErr((e2 as ApiError).message);
          setBusy(false);
        }
      }}>
        <Field label="Campaign name"><input required minLength={3} className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Antarctic Science Week 2026" /></Field>
        <Field label="Description"><textarea className={`${inputCls} h-20 py-2`} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Start date"><input type="date" className={inputCls} value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></Field>
          <Field label="End date"><input type="date" className={inputCls} value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></Field>
        </div>
        {opts.data && (
          <>
            <fieldset><legend className="mb-1.5 text-[13px] font-medium text-night">Target audience</legend>
              <div className="flex flex-wrap gap-2">{opts.data.audiences.map((a) => (
                <label key={a.key} className="inline-flex items-center gap-1.5 rounded-full border border-frost px-3 py-1 text-[13px]"><input type="checkbox" checked={f.audiences.includes(a.key)} onChange={() => toggle("audiences", a.key)} />{a.label}</label>
              ))}</div>
            </fieldset>
            <fieldset><legend className="mb-1.5 text-[13px] font-medium text-night">Channels</legend>
              <div className="flex flex-wrap gap-2">{opts.data.channels.map((c) => (
                <label key={c.key} title={c.note} className="inline-flex items-center gap-1.5 rounded-full border border-frost px-3 py-1 text-[13px]">
                  <input type="checkbox" checked={f.channels.includes(c.key)} onChange={() => toggle("channels", c.key)} />{c.label}
                  <span className={c.live ? "text-teal" : "text-[#8a5c0c]"}>· {c.live ? "live" : "simulated"}</span>
                </label>
              ))}</div>
            </fieldset>
            <fieldset><legend className="mb-1.5 text-[13px] font-medium text-night">Topics</legend>
              <div className="flex max-h-28 flex-wrap gap-1.5 overflow-auto">{opts.data.topics.map((t) => (
                <label key={t.slug} className="inline-flex items-center gap-1 rounded-full bg-snow px-2.5 py-0.5 text-[12.5px] ring-1 ring-frost"><input type="checkbox" checked={f.topics.includes(t.slug)} onChange={() => toggle("topics", t.slug)} />{t.name}</label>
              ))}</div>
            </fieldset>
          </>
        )}
        {err && <p role="alert" className="rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" loading={busy}>Create campaign</Button></div>
      </form>
    </Modal>
  );
}

export default function CampaignsPage() {
  const { can, ready, user } = useAuth();
  const router = useRouter();
  const allowed = can("generate_content") || can("review");
  const { data, error, loading, reload } = useApi<{ results: CampaignT[] }>(allowed ? "/api/campaigns" : null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (ready && !user) router.replace("/login?next=/campaigns");
  }, [ready, user, router]);
  return (
    <Container>
      <PageHeader eyebrow="Outreach" title="Campaign Planner"
        description="Plan outreach campaigns around research. Items can be scheduled only after an editor approves their content, and publishing uses the same review workflow as the Review Center."
        actions={<div className="flex gap-2"><LinkButton href="/calendar" variant="secondary" icon={<CalendarDays className="h-4 w-4" />}>Content calendar</LinkButton>{can("generate_content") && <Button onClick={() => setOpen(true)} icon={<Plus className="h-4 w-4" />}>New campaign</Button>}</div>} />
      {ready && user && !allowed ? (
        <EmptyState title="Campaign planning is for staff roles" body="Sign in as a researcher, editor or administrator." />
      ) : error ? <ErrorState error={error} onRetry={reload} /> : loading || !data ? (
        <div className="grid gap-4 md:grid-cols-2">{[0, 1].map((i) => <CardSkeleton key={i} rows={4} />)}</div>
      ) : data.results.length === 0 ? (
        <EmptyState icon={<Megaphone className="h-6 w-6" />} title="No campaigns yet" body="Create a campaign, then add approved outreach content to its calendar." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.results.map((c) => (
            <Link key={c.slug} href={`/campaigns/${c.slug}`} className="rounded-2xl border border-frost bg-white p-5 shadow-card transition hover:border-glacier hover:shadow-lift">
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <Badge tone={CAMPAIGN_TONE[c.status]}>{c.status}</Badge>
                {c.is_demo && <Badge tone="amber" icon={<FlaskConical className="h-3 w-3" />}>Demo</Badge>}
                <span className="text-[12.5px] text-steel">{c.start_date ? `${fmtDate(c.start_date)} – ${fmtDate(c.end_date)}` : "No dates yet"}</span>
              </div>
              <h2 className="font-display text-[20px] text-night">{c.name}</h2>
              <p className="mt-1 line-clamp-2 text-[13.5px] text-ink-soft">{c.description}</p>
              <p className="mt-3 text-[12.5px] text-steel">
                {c.items_total} items · {c.item_counts.scheduled || 0} scheduled · {c.item_counts.published || 0} published · {c.audiences.map((a) => a.label).join(", ") || "no audience set"}
              </p>
            </Link>
          ))}
        </div>
      )}
      <CreateCampaign open={open} onClose={() => setOpen(false)} />
    </Container>
  );
}
