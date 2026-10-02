"use client";

import { CircleCheck, Link2, Megaphone, ShieldCheck, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { post } from "@/lib/api";
import { LineageView } from "@/components/provenance/Trust";
import Link from "next/link";
import { useParams } from "next/navigation";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { Markdown } from "@/components/common/Markdown";
import { Badge, Card, MetaRow } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { ProvenancePanel } from "@/components/provenance/Provenance";
import { AUDIENCE_LABEL, FORMAT_LABEL, fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { ContentItem } from "@/lib/types";

export default function OutreachItem() {
  const { id } = useParams<{ id: string }>();
  const { data: c, error, loading, reload } = useApi<ContentItem & { evidence_summary?: { overall: string | null; checks: { label: string; status: string }[] } }>(`/api/outreach/${id}`);
  // Live engagement tracking (view on open, completion when the end of the article is reached, share on copy)
  const sent = useRef<Set<string>>(new Set());
  const endRef = useRef<HTMLDivElement>(null);
  const [shared, setShared] = useState(false);
  const track = (event: "view" | "click" | "share" | "complete") => {
    if (sent.current.has(event)) return;
    sent.current.add(event);
    post(`/api/outreach/${id}/track`, { event, channel: "website" }).catch(() => {});
  };
  useEffect(() => {
    if (!c) return;
    track("view");
    const el = endRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver((es) => es.some((e) => e.isIntersecting) && track("complete"), { threshold: 1 });
    io.observe(el);
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [c?.id]);
  if (loading && !c) return <DetailSkeleton />;
  if (error || !c) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/outreach", label: "Back to Outreach Feed" }} />;
  return (
    <Container className="max-w-[1150px]">
      <BackLink href="/outreach" label="Back to Outreach Feed" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <article className="min-w-0 space-y-5">
          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center gap-2 border-b border-frost bg-snow/60 px-6 py-3">
              <Badge tone="teal">{FORMAT_LABEL[c.format] || c.format}</Badge>
              {c.audience && <Badge tone="slate">For {AUDIENCE_LABEL[c.audience] || c.audience}</Badge>}
              {c.language && c.language !== "English" && <Badge tone="violet">{c.language}</Badge>}
              <span className="ml-auto inline-flex items-center gap-1 text-[12px] text-teal"><ShieldCheck className="h-3.5 w-3.5" aria-hidden /> Approved by {c.reviewer || "an editor"}</span>
            </div>
            <div className="px-6 py-5">
              <h1 className="mb-3 text-[28px] leading-tight text-night">{c.title}</h1>
              <Markdown text={c.body || ""} onCite={(n) => { track("click"); document.getElementById(`src-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" }); }} citeTitle={(n) => c.citations?.find((x) => x.n === n)?.label} />
              <div ref={endRef} aria-hidden className="h-px" />
              <button
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(window.location.href);
                    setShared(true);
                    track("share");
                  } catch {
                    /* clipboard blocked */
                  }
                }}
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-frost px-3 py-1.5 text-[13px] text-deep hover:bg-ice"
              >
                <Link2 className="h-4 w-4" aria-hidden /> {shared ? "Link copied" : "Copy link to share"}
              </button>
            </div>
          </Card>
          <Card className="p-5">
            <h2 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">Evidence — every [n] marker maps to one of these passages</h2>
            <ol className="space-y-3">
              {c.citations?.map((s) => (
                <li key={s.n} id={`src-${s.n}`} className="rounded-xl border border-frost p-3">
                  <p className="text-[13.5px]"><span className="font-mono text-cyan-deep">[{s.n}]</span>{" "}
                    {s.url ? <Link href={s.url} className="font-medium text-night hover:text-cyan-deep hover:underline">{s.label}</Link> : <span className="font-medium">{s.label}</span>}
                    <span className="text-steel"> — {s.section}{s.page ? `, p. ${s.page}` : ""}</span></p>
                  <blockquote className="mt-1.5 border-l-2 border-glacier pl-3 text-[13px] leading-relaxed text-ink-soft">{s.quote}</blockquote>
                </li>
              ))}
            </ol>
          </Card>
        </article>
        <aside className="space-y-4">
          <SideCard title="Dissemination">
            <ul className="space-y-2">
              {(c.channel_status || []).map((ch) => (
                <li key={ch.channel} className="flex items-start justify-between gap-2 text-[13px]">
                  <span><span className="font-medium text-night">{ch.label}</span><span className="block text-[11.5px] text-steel">{ch.note}</span></span>
                  <Badge tone={ch.status === "live" ? "teal" : "amber"}>{ch.status === "live" ? "Live" : "Simulated"}</Badge>
                </li>
              ))}
            </ul>
            <dl className="mt-3">
              <MetaRow label="Published">{fmtDate(c.published_at)}</MetaRow>
              <MetaRow label="Approved">{fmtDate(c.approved_at)}</MetaRow>
              <MetaRow label="Source">{c.resource_title}</MetaRow>
            </dl>
          </SideCard>
          {c.evidence_summary?.checks?.length ? (
            <SideCard title="Automated evidence check">
              <ul className="space-y-1.5">
                {c.evidence_summary.checks.map((x) => (
                  <li key={x.label} className="flex items-center gap-2 text-[13px]">
                    {x.status === "pass" ? <CircleCheck className="h-4 w-4 text-teal" aria-hidden /> : <TriangleAlert className="h-4 w-4 text-amber" aria-hidden />}
                    {x.label}<span className="sr-only">: {x.status}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11.5px] text-steel">Heuristic check run before human approval — not a scientific verification.</p>
            </SideCard>
          ) : null}
          <ProvenancePanel p={c.provenance} compact />
          <SideCard title="Provenance pipeline">
            <LineageView path={`/api/lineage/content/${c.id}`} />
          </SideCard>
          <Link href="/outreach" className="inline-flex items-center gap-1.5 text-[13px] text-cyan-deep hover:underline"><Megaphone className="h-3.5 w-3.5" /> More outreach</Link>
        </aside>
      </div>
    </Container>
  );
}
