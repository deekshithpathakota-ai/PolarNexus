"use client";

import clsx from "clsx";
import { Archive, ArrowRight, BookOpenText, CalendarClock, CheckCircle2, ExternalLink, FlaskConical, Globe2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { PolarScene } from "@/components/art/PolarScene";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { Markdown } from "@/components/common/Markdown";
import { Badge, Button, Card, Tabs } from "@/components/common/ui";
import { useToast } from "@/components/common/Toast";
import { Container } from "@/components/layout/AppShell";
import { PolarMap, type MapView } from "@/components/maps/PolarMap";
import { VerificationBadge } from "@/components/provenance/Provenance";
import { ApiError, del, patch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Story, StoryItem } from "@/lib/types";

type Mode = "scientific" | "public" | "student";

function ItemCard({ i }: { i: StoryItem }) {
  const thumb = i.extra?.thumbnail;
  return (
    <Link href={i.url} className="group flex min-w-0 gap-3 rounded-xl border border-frost bg-white p-2.5 shadow-card transition hover:border-glacier">
      {i.type === "media" && (
        <span className="h-14 w-20 shrink-0 overflow-hidden rounded-lg bg-ice">
          {thumb ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={thumb} alt="" className="h-full w-full object-cover" />
          ) : (
            <PolarScene scene={i.extra?.scene || "ice"} seed={i.slug} title={i.title} className="h-full w-full" />
          )}
        </span>
      )}
      <span className="min-w-0">
        <span className="mb-1 flex flex-wrap items-center gap-1.5">
          <TypeBadge type={i.type} kind={i.kind} />
          <VerificationBadge status={i.verification} label={i.verification_label} />
        </span>
        <span className="line-clamp-2 block text-[13.5px] font-medium leading-snug text-night group-hover:text-cyan-deep">{i.title}</span>
      </span>
    </Link>
  );
}

export default function StoryPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: s, error, loading, reload, setData } = useApi<Story>(`/api/stories/${slug}`);
  const [mode, setMode] = useState<Mode>("public");
  const [active, setActive] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [view, setView] = useState<MapView>("antarctic");
  const [sel, setSel] = useState<string | null>(null);
  const evRef = useRef<HTMLOListElement>(null);
  const { can } = useAuth();
  const toast = useToast();
  if (loading && !s) return <DetailSkeleton />;
  if (error || !s) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/stories", label: "Back to Research Stories" }} />;

  const summary = s.summaries?.[mode];
  const act = async (label: string, fn: () => Promise<Story | unknown>) => {
    setBusy(label);
    try {
      const out = await fn();
      if (out && typeof out === "object" && "slug" in (out as Story)) setData(out as Story);
      else reload();
      toast("success", label);
    } catch (e) {
      toast("error", "Could not update the story", (e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };
  const points = (s.map_points || []).map((p) => ({
    key: p.url, kind: (p.type === "station" || p.type === "expedition" || p.type === "media" || p.type === "activity" ? p.type : "station") as "station",
    name: p.title, lat: p.lat, lon: p.lon, verified: p.verification === "verified" || p.verification === "public_source",
  }));
  const hasArctic = points.some((p) => p.lat > 50);
  const hasAntarctic = points.some((p) => p.lat < -40);

  return (
    <Container>
      <BackLink href="/stories" label="Back to Research Stories" />
      <header className="mb-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge tone="cyan" icon={<BookOpenText className="h-3 w-3" />}>Research Story</Badge>
          <Badge tone={s.status === "published" ? "teal" : "slate"}>{s.status}</Badge>
          {s.is_demo && <Badge tone="amber" icon={<FlaskConical className="h-3 w-3" />}>Demonstration story</Badge>}
          <span className="text-[12.5px] text-steel">Updated {fmtDate(s.updated_at)}</span>
        </div>
        <h1 className="max-w-4xl text-[30px] leading-tight text-night md:text-[40px]">{s.title}</h1>
        {s.notice && <p role="note" className="mt-3 max-w-3xl rounded-xl border border-dashed border-[#e2c58f] bg-[#fdf8ee] px-4 py-2.5 text-[13.5px] text-[#7a520b]">{s.notice}</p>}
        {s.can_edit && (
          <div className="mt-4 flex flex-wrap gap-2">
            {s.status !== "published" && can("publish") && (
              <Button size="sm" loading={busy === "Story published"} icon={<Globe2 className="h-4 w-4" />} onClick={() => act("Story published", () => patch(`/api/stories/${s.slug}`, { status: "published" }))}>Publish</Button>
            )}
            {s.status === "published" && can("publish") && (
              <Button size="sm" variant="secondary" onClick={() => act("Moved back to draft", () => patch(`/api/stories/${s.slug}`, { status: "draft" }))}>Unpublish</Button>
            )}
            <Button size="sm" variant="secondary" loading={busy === "Summaries regenerated"} icon={<RefreshCw className="h-4 w-4" />} onClick={() => act("Summaries regenerated", () => patch(`/api/stories/${s.slug}`, { regenerate: true }))}>Regenerate explanations</Button>
            {s.status !== "archived" && <Button size="sm" variant="ghost" icon={<Archive className="h-4 w-4" />} onClick={() => act("Story archived", () => del(`/api/stories/${s.slug}`))}>Archive</Button>}
          </div>
        )}
      </header>

      <section aria-labelledby="chain-h" className="mb-6">
        <h2 id="chain-h" className="sr-only">Story chain</h2>
        <ol className="scrollbar-thin flex gap-2 overflow-x-auto pb-2">
          {(s.chain || []).map((c, i) => (
            <li key={c.role} className="flex shrink-0 items-center gap-2">
              <a href={`#role-${i}`} className="rounded-full border border-frost bg-white px-3 py-1.5 text-[12.5px] text-deep shadow-sm hover:border-cyan">
                <span className="mr-1.5 font-mono text-[10.5px] text-mist">{i + 1}</span>{c.role}<span className="ml-1.5 text-mist">· {c.items.length}</span>
              </a>
              {i < (s.chain || []).length - 1 && <ArrowRight className="h-3.5 w-3.5 text-mist" aria-hidden />}
            </li>
          ))}
          <li className="flex shrink-0 items-center"><span className="rounded-full bg-night px-3 py-1.5 text-[12.5px] text-white">Explanation</span></li>
        </ol>
      </section>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          <Card className="p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-mono text-[11px] uppercase tracking-wider text-steel">Explanation</h2>
              <Tabs value={mode} onChange={(m) => { setMode(m); setActive(null); }} tabs={[
                { key: "scientific", label: "Scientific summary" }, { key: "public", label: "Public explanation" }, { key: "student", label: "Student explanation" },
              ]} />
            </div>
            {summary?.text ? (
              <Markdown text={summary.text} onCite={(n) => { setActive(n); evRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }}
                citeTitle={(n) => summary.sources.find((x) => x.n === n)?.title} />
            ) : (
              <p className="text-[14px] text-steel">{summary?.notice || "No explanation could be grounded in this story's evidence."}</p>
            )}
            {summary && (
              <p className="mt-3 text-[12px] text-steel">
                {summary.mode === "llm" ? "Generated by the configured language model from the cited passages." : summary.notice}
                {summary.based_on && <> Based on <Link className="text-cyan-deep hover:underline" href={`/resources/${summary.based_on.slug}`}>{summary.based_on.title}</Link>.</>}
              </p>
            )}
            {summary && summary.sources.length > 0 && (
              <ol ref={evRef} className="mt-4 space-y-1.5 border-t border-frost pt-3">
                {summary.sources.map((src) => (
                  <li key={src.n} className={clsx("rounded-lg px-2 py-1.5 text-[12.5px]", active === src.n && "bg-[#f0f9fc] ring-1 ring-cyan")}>
                    <span className="mr-2 font-mono text-cyan-deep">[{src.n}]</span>
                    <Link href={src.url} className="text-night hover:text-cyan-deep hover:underline">{src.title}</Link>
                    <span className="text-steel"> — {src.section}{src.resource_type === "document" ? `, p. ${src.page}` : ""}</span>
                    {active === src.n && <blockquote className="mt-1 border-l-2 border-glacier pl-2 text-ink-soft">{src.snippet}</blockquote>}
                  </li>
                ))}
              </ol>
            )}
          </Card>

          {(s.chain || []).map((c, i) => (
            <section key={c.role} id={`role-${i}`} aria-labelledby={`role-h-${i}`} className="scroll-mt-20">
              <h2 id={`role-h-${i}`} className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-steel">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-night text-[10px] text-white">{i + 1}</span>{c.role}
              </h2>
              <div className="grid gap-2 sm:grid-cols-2">{c.items.map((it) => <ItemCard key={`${it.type}${it.id}`} i={it} />)}</div>
            </section>
          ))}
        </div>

        <aside className="space-y-4">
          {points.length > 0 && (
            <SideCard title="Map">
              {hasArctic && hasAntarctic && (
                <div className="mb-2"><Tabs value={view} onChange={setView} tabs={[{ key: "antarctic", label: "Antarctic" }, { key: "arctic", label: "Arctic" }, { key: "world", label: "World" }]} /></div>
              )}
              <div className="overflow-hidden rounded-xl">
                <PolarMap view={hasAntarctic ? view : hasArctic ? "arctic" : "world"} points={points} selected={sel} onSelect={setSel} />
              </div>
              <p className="mt-2 text-[11.5px] text-steel">Only records with stored coordinates are mapped.</p>
            </SideCard>
          )}
          {(s.timeline || []).length > 0 && (
            <SideCard title="Timeline">
              <ol className="relative space-y-2.5 border-l border-frost pl-4">
                {s.timeline!.map((t, n) => (
                  <li key={n} className="relative text-[13px]">
                    <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-cyan" aria-hidden />
                    <span className="flex items-center gap-1 font-mono text-[11px] text-steel"><CalendarClock className="h-3 w-3" aria-hidden />{t.date.slice(0, 4)} · {t.label || t.kind}</span>
                    <Link href={t.url} className="text-night hover:text-cyan-deep hover:underline">{t.title}</Link>
                  </li>
                ))}
              </ol>
            </SideCard>
          )}
          <SideCard title="Evidence basis">
            <p className="flex items-center gap-2 text-[13px] text-ink-soft"><CheckCircle2 className="h-4 w-4 text-teal" aria-hidden />{s.basis.authoritative} public-source or verified record(s)</p>
            <p className="mt-1 flex items-center gap-2 text-[13px] text-ink-soft"><FlaskConical className="h-4 w-4 text-[#8a5c0c]" aria-hidden />{s.basis.demonstration} demonstration record(s)</p>
            <p className="mt-2 text-[12px] text-steel">Every explanation sentence cites a passage from these records. Nothing outside them is added.</p>
          </SideCard>
          {(s.topics || []).length > 0 && (
            <SideCard title="Related topics">
              <div className="flex flex-wrap gap-1.5">
                {s.topics!.map((t) => <Link key={t.slug} href={t.url} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.title}</Link>)}
              </div>
            </SideCard>
          )}
          <SideCard title="Share">
            <p className="text-[12.5px] text-ink-soft">Published stories are public at this address.</p>
            <a href={`/stories/${s.slug}`} className="mt-1 inline-flex items-center gap-1 break-all text-[12.5px] text-cyan-deep hover:underline">/stories/{s.slug} <ExternalLink className="h-3 w-3" aria-hidden /></a>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}
