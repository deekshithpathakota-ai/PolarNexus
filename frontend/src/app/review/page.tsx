"use client";

import clsx from "clsx";
import { CircleCheck, CircleX, Megaphone, PenLine, RotateCcw, Save } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { CitationList, EvidenceCheckView, History } from "@/components/content/EvidencePanel";
import { Markdown } from "@/components/common/Markdown";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Badge, Button, Card, EmptyState, ErrorState, Modal, PageHeader, Skeleton, StatusBadge, Tabs, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { post, put } from "@/lib/api";
import { FORMAT_LABEL, STATUS_LABEL, genModeLabel, timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { ContentItem, ContentStatus } from "@/lib/types";

const ORDER: ContentStatus[] = ["under_review", "changes_requested", "approved", "published", "rejected", "draft", "evidence_checked"];
const CHANNELS = ["website", "linkedin", "instagram", "newsletter"] as const;

function Detail({ id, onChanged }: { id: number; onChanged: () => void }) {
  const { data: item, error, loading, reload, setData } = useApi<ContentItem>(`/api/content/${id}`);
  const toast = useToast();
  const [active, setActive] = useState<number | null>(null);
  const [dialog, setDialog] = useState<null | "reject" | "request_changes" | "publish" | "approve_warn">(null);
  const [comment, setComment] = useState("");
  const [channels, setChannels] = useState<string[]>(["website"]);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState("");
  const [side, setSide] = useState<"check" | "sources" | "history">("check");
  useEffect(() => { if (item) setBody(item.body || ""); }, [item]);

  if (loading && !item) return <Skeleton className="h-[520px] w-full rounded-2xl" />;
  if (error || !item) return <ErrorState error={error || "Not found"} onRetry={reload} />;

  const act = async (action: string, extra: Record<string, unknown> = {}) => {
    setBusy(true);
    try {
      const path = action === "approve" ? `/api/reviews/${id}/approve` : action === "reject" ? `/api/reviews/${id}/reject` : action === "request_changes" ? `/api/reviews/${id}/request-changes` : `/api/reviews/${id}/publish`;
      const r = await post<ContentItem>(path, { comment, channels, ...extra });
      setData(r);
      setDialog(null);
      setComment("");
      onChanged();
      toast("success", `Content ${STATUS_LABEL[r.status].toLowerCase()}`, r.status === "published" ? `Disseminated to ${r.channels.join(", ")}.` : undefined);
    } catch (e) {
      const msg = (e as Error).message;
      if (msg.includes("evidence check reported failures")) setDialog("approve_warn");
      else toast("error", "Action failed", msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_380px]">
      <Card className="min-w-0 overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 border-b border-frost bg-snow/70 px-5 py-3">
          <StatusBadge status={item.status} />
          <Badge>{FORMAT_LABEL[item.format]}</Badge>
          <span className="font-mono text-[10.5px] uppercase text-steel">{genModeLabel(item.generation_mode)} · v{item.version}</span>
          <span className="ml-auto text-[12px] text-steel">by {item.created_by} · {timeAgo(item.submitted_at || item.created_at)}</span>
        </div>
        <div className="p-5">
          <p className="mb-1 text-[12px] text-steel">Source resource: <span className="text-night">{item.resource_title}</span></p>
          <h2 className="mb-3 text-[24px] leading-tight text-night">{item.title}</h2>
          {editing ? (
            <>
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={16} className={clsx(inputCls, "font-mono text-[13px]")} aria-label="Edit content" />
              <div className="mt-2 flex gap-2">
                <Button size="sm" icon={<Save className="h-3.5 w-3.5" />} loading={busy} onClick={async () => {
                  setBusy(true);
                  try { setData(await put<ContentItem>(`/api/content/${id}`, { body })); setEditing(false); toast("success", "Edits saved", "Evidence check re-run."); onChanged(); }
                  catch (e) { toast("error", "Could not save", (e as Error).message); } finally { setBusy(false); }
                }}>Save edits</Button>
                <Button size="sm" variant="ghost" onClick={() => { setEditing(false); setBody(item.body || ""); }}>Cancel</Button>
              </div>
            </>
          ) : (
            <Markdown text={item.body || ""} onCite={(n) => { setActive(n); setSide("sources"); }} citeTitle={(n) => item.citations?.find((c) => c.n === n)?.label} />
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-frost bg-snow/50 px-5 py-3">
          {item.status === "under_review" && (
            <>
              <Button size="sm" loading={busy} icon={<CircleCheck className="h-3.5 w-3.5" />} onClick={() => act("approve")}>Approve</Button>
              <Button size="sm" variant="secondary" icon={<RotateCcw className="h-3.5 w-3.5" />} onClick={() => setDialog("request_changes")}>Request changes</Button>
              <Button size="sm" variant="secondary" className="text-coral" icon={<CircleX className="h-3.5 w-3.5" />} onClick={() => setDialog("reject")}>Reject</Button>
              {!editing && <Button size="sm" variant="ghost" icon={<PenLine className="h-3.5 w-3.5" />} onClick={() => setEditing(true)}>Edit</Button>}
            </>
          )}
          {item.status === "approved" && (
            <>
              <Button size="sm" icon={<Megaphone className="h-3.5 w-3.5" />} onClick={() => setDialog("publish")}>Publish / Disseminate</Button>
              <Button size="sm" variant="secondary" icon={<RotateCcw className="h-3.5 w-3.5" />} onClick={() => setDialog("request_changes")}>Request changes</Button>
            </>
          )}
          {item.status === "published" && (
            <p className="flex items-center gap-2 text-[13.5px] text-teal"><Megaphone className="h-4 w-4" /> Published to {item.channels.join(", ")}{item.channels.some((x) => x !== "website") ? " (social channels: prototype simulation)" : ""} · <Link href={`/outreach/${item.id}`} className="underline">view</Link></p>
          )}
          {["draft", "changes_requested", "rejected"].includes(item.status) && <p className="text-[13px] text-steel">Waiting on the author — no reviewer action needed.</p>}
        </div>
      </Card>
      <Card className="h-fit p-5">
        <Tabs className="mb-4" value={side} onChange={setSide} tabs={[{ key: "check", label: "Evidence check" }, { key: "sources", label: `Sources · ${item.citations?.length || 0}` }, { key: "history", label: "History" }]} />
        {side === "check" && <EvidenceCheckView item={item} />}
        {side === "sources" && <CitationList item={item} active={active} onActive={setActive} />}
        {side === "history" && <History item={item} />}
      </Card>

      <Modal open={dialog === "reject" || dialog === "request_changes"} onClose={() => setDialog(null)} title={dialog === "reject" ? "Reject content" : "Request changes"}>
        <label className="block text-[13px] font-medium text-night" htmlFor="rv-comment">Comment for the author (required)</label>
        <textarea id="rv-comment" value={comment} onChange={(e) => setComment(e.target.value)} rows={4} className={clsx(inputCls, "mt-1.5")} placeholder="Explain what needs to change and why…" />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Cancel</Button>
          <Button variant={dialog === "reject" ? "danger" : "primary"} disabled={comment.trim().length < 5} loading={busy} onClick={() => act(dialog!)}>{dialog === "reject" ? "Reject" : "Send back to author"}</Button>
        </div>
      </Modal>
      <Modal open={dialog === "publish"} onClose={() => setDialog(null)} title="Publish & disseminate">
        <p className="text-[13.5px] text-ink-soft">Choose channels. Publishing to the <strong>website</strong> places the content on the public PolarNexus Outreach Feed. Social channels are <strong>simulated in this prototype</strong> — they are recorded as dispatched but no external post is made.</p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          {CHANNELS.map((c) => (
            <label key={c} className={clsx("flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13.5px] capitalize", channels.includes(c) ? "border-cyan bg-[#f0f9fc]" : "border-frost")}>
              <input type="checkbox" className="accent-[#0f7fa1]" checked={channels.includes(c)} onChange={() => setChannels((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c]))} />
              {c}
              <span className={clsx("ml-auto rounded px-1.5 py-px font-mono text-[9.5px] uppercase tracking-wide", c === "website" ? "bg-[#e2f4f1] text-teal" : "bg-[#fbf1df] text-[#8a5c0c]")}>
                {c === "website" ? "Live" : "Connector ready"}
              </span>
            </label>
          ))}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Cancel</Button>
          <Button disabled={!channels.length} loading={busy} onClick={() => act("publish")} icon={<Megaphone className="h-4 w-4" />}>Publish</Button>
        </div>
      </Modal>
      <Modal open={dialog === "approve_warn"} onClose={() => setDialog(null)} title="Evidence check reported failures">
        <p className="text-[13.5px] text-ink-soft">The automated check flagged failures (for example unsupported sentences or invalid citations). Approve only if you have verified the content against the sources yourself.</p>
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} className={clsx(inputCls, "mt-3")} placeholder="Reviewer note (recommended)" />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Go back</Button>
          <Button loading={busy} onClick={() => act("approve", { acknowledge_warnings: true })}>I verified it — approve</Button>
        </div>
      </Modal>
    </div>
  );
}

function Review() {
  const sp = useSearchParams();
  const router = useRouter();
  const selected = sp.get("item") ? Number(sp.get("item")) : null;
  const [tab, setTab] = useState<ContentStatus>("under_review");
  const [tick, setTick] = useState(0);
  const { data, error, loading, reload } = useApi<{ groups: Record<ContentStatus, ContentItem[]>; counts: Record<ContentStatus, number> }>("/api/reviews/queue", undefined, [tick]);

  useEffect(() => {
    if (selected && data) {
      const found = ORDER.find((s) => data.groups[s]?.some((c) => c.id === selected));
      if (found) setTab(found);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, data?.counts]);

  return (
    <Container className="max-w-[1500px]">
      <PageHeader eyebrow="Human-in-the-loop" title="Review Center" description="Editors verify AI-assisted drafts against their sources, then approve, request changes, reject or publish. Nothing reaches the public without this step." />
      {error ? <ErrorState error={error} onRetry={reload} /> : (
        <>
          <Tabs className="mb-5" value={tab} onChange={setTab} tabs={ORDER.map((s) => ({ key: s, label: <span>{STATUS_LABEL[s]} <span className="ml-1 rounded-full bg-white/70 px-1.5 font-mono text-[11px]">{data?.counts[s] ?? "·"}</span></span> }))} />
          <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
            <Card className="h-fit p-2">
              {loading && !data ? <Skeleton className="m-2 h-40" /> : !data?.groups[tab]?.length ? (
                <p className="px-4 py-10 text-center text-[13px] text-steel">Nothing {STATUS_LABEL[tab].toLowerCase()}.</p>
              ) : (
                <ul>
                  {data.groups[tab].map((c) => (
                    <li key={c.id}>
                      <button onClick={() => router.push(`/review?item=${c.id}`, { scroll: false })} className={clsx("block w-full rounded-xl px-3 py-2.5 text-left hover:bg-snow", selected === c.id && "bg-ice")}>
                        <span className="line-clamp-2 text-[13.5px] font-medium text-night">{c.title}</span>
                        <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11.5px] text-steel">
                          <span>{c.format}</span>·<span>{c.created_by}</span>·<span>{timeAgo(c.submitted_at || c.updated_at)}</span>
                          {c.evidence_overall && <span className={clsx("ml-auto rounded px-1.5 font-mono text-[10px] uppercase", c.evidence_overall === "pass" ? "bg-[#e2f4f1] text-teal" : c.evidence_overall === "warn" ? "bg-[#fbf1df] text-[#8a5c0c]" : "bg-[#fbe9e5] text-coral")}>check {c.evidence_overall}</span>}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <div className="min-w-0">
              {selected ? <Detail key={selected} id={selected} onChanged={() => setTick((t) => t + 1)} /> : (
                <EmptyState title="Select an item to review" body="Open an item from the queue to see the draft, its source passages and the automated evidence check." />
              )}
            </div>
          </div>
        </>
      )}
    </Container>
  );
}

export default function Page() {
  return (
    <RequireAuth permission="review" title="Review Center">
      <Suspense>
        <Review />
      </Suspense>
    </RequireAuth>
  );
}
