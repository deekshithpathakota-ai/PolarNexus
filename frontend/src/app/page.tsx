"use client";

import {
  ArrowRight,
  BookOpen,
  Bot,
  Building2,
  ClipboardCheck,
  Database,
  GraduationCap,
  Image as ImageIcon,
  Megaphone,
  Search,
  ShieldCheck,
  Ship,
  SquarePen,
} from "lucide-react";
import Link from "next/link";
import { PolarScene } from "@/components/art/PolarScene";
import { ResourceCard } from "@/components/cards/ResourceCard";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { CardSkeleton, DemoBadge, ErrorState, LinkButton, SectionTitle, Skeleton } from "@/components/common/ui";
import { Globe } from "@/components/maps/Globe";
import { SearchBox } from "@/components/search/SearchBox";
import { BRAND, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { SearchResponse } from "@/lib/types";

interface Stats { documents: number; datasets: number; expeditions: number; stations: number; media: number; topics: number; researchers: number; dataset_records: number; label: string }

const PIPELINE = [
  { icon: BookOpen, label: "Research", text: "Reports, papers, datasets, media" },
  { icon: Search, label: "Search", text: "Hybrid keyword + semantic" },
  { icon: Bot, label: "AI", text: "Evidence-grounded answers" },
  { icon: GraduationCap, label: "Education", text: "Learning paths & quizzes" },
  { icon: SquarePen, label: "Outreach", text: "Drafts for every audience" },
  { icon: ClipboardCheck, label: "Review", text: "Humans approve" },
  { icon: Megaphone, label: "Dissemination", text: "Web & social channels" },
];

const AREAS = [
  { href: "/documents", icon: BookOpen, title: "Research", text: "Explore scientific publications and reports." },
  { href: "/datasets", icon: Database, title: "Datasets", text: "Discover structured polar datasets." },
  { href: "/expeditions", icon: Ship, title: "Expeditions", text: "Explore India's polar expedition history." },
  { href: "/media", icon: ImageIcon, title: "Media", text: "Discover photographs, videos and visual stories." },
  { href: "/stations", icon: Building2, title: "Stations", text: "Explore polar research stations." },
  { href: "/assistant", icon: Bot, title: "AI Knowledge Assistant", text: "Ask questions and receive evidence-grounded answers." },
];

const REGIONS = [
  { title: "Antarctic", scene: "iceshelf", href: "/explore?region=Antarctic", text: "Maitri, Bharati and the East Antarctic coast" },
  { title: "Arctic", scene: "fjord", href: "/explore?region=Arctic", text: "Himadri, Ny-Ålesund and Kongsfjorden" },
  { title: "Southern Ocean", scene: "ocean", href: "/explore?region=Southern%20Ocean", text: "Fronts, carbon and the food web" },
  { title: "Himalaya — the third pole", scene: "mountains", href: "/explore?region=Himalaya", text: "Himansh and the Chandra basin glaciers" },
];

export default function Home() {
  const stats = useApi<Stats>("/api/stats");
  const featured = useApi<SearchResponse>("/api/resources", { kind: "document", sort: "views", page_size: 6 });

  const statItems = stats.data
    ? [
        [stats.data.documents, "Research documents"],
        [stats.data.datasets, "Datasets"],
        [stats.data.dataset_records, "Data records"],
        [stats.data.expeditions, "Expeditions"],
        [stats.data.stations, "Stations & locations"],
        [stats.data.media, "Media assets"],
        [stats.data.topics, "Scientific topics"],
      ]
    : [];

  return (
    <div>
      {/* ------------------------------------------------------------ HERO */}
      <section className="relative overflow-hidden bg-night text-white">
        <div className="absolute inset-0 opacity-50">
          <PolarScene scene="aurora" seed="hero" className="h-full w-full" />
        </div>
        <div className="absolute inset-0 bg-gradient-to-r from-night via-night/90 to-night/40" />
        <div className="grain absolute inset-0" />
        <div className="relative mx-auto grid max-w-[1280px] items-center gap-8 px-4 pb-14 pt-12 md:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:pb-20 lg:pt-16">
          <div className="animate-fade-up">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-glacier">
              <span className="h-1.5 w-1.5 rounded-full bg-aurora" /> Polar knowledge · discovery · outreach
            </p>
            <h1 className="text-[40px] font-semibold leading-[1.05] tracking-tight sm:text-[52px] lg:text-[60px]">
              Explore India&apos;s
              <br />
              <span className="bg-gradient-to-r from-glacier via-white to-aurora bg-clip-text text-transparent">Polar Science</span>
            </h1>
            <p className="mt-5 max-w-xl text-[16.5px] leading-relaxed text-frost/85">
              Discover research, expeditions, datasets, media and evidence-grounded insights from India&apos;s polar knowledge ecosystem.
            </p>
            <div className="mt-7 max-w-xl">
              <SearchBox dark placeholder="Try “Antarctic sea ice” or “Maitri station”" />
              <div className="mt-3 flex flex-wrap gap-2 text-[12.5px]">
                {["Antarctic climate research", "Maitri station", "Arctic expeditions", "sea-ice research", "polar atmospheric studies"].map((s) => (
                  <Link key={s} href={`/explore?q=${encodeURIComponent(s)}`} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-frost/80 hover:border-glacier/50 hover:text-white">
                    {s}
                  </Link>
                ))}
              </div>
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <LinkButton href="/explore" size="lg" icon={<Search className="h-4 w-4" />}>Explore Knowledge</LinkButton>
              <Link href="/assistant" className="inline-flex h-12 items-center gap-2 rounded-lg border border-white/20 bg-white/5 px-5 text-[15px] font-medium text-white hover:bg-white/10">
                <Bot className="h-4 w-4 text-aurora" /> Ask {BRAND} AI
              </Link>
            </div>
          </div>
          <div className="relative mx-auto hidden aspect-square w-full max-w-[440px] lg:block">
            <ErrorBoundary label="globe" fallback={<div className="h-full w-full rounded-full bg-deep/60" />}>
              <Globe size={440} />
            </ErrorBoundary>
          </div>
        </div>
        {/* stats band */}
        <div className="relative border-t border-white/10 bg-abyss/40 backdrop-blur">
          <div className="mx-auto max-w-[1280px] px-4 py-5 md:px-8">
            {stats.error ? (
              <p className="text-sm text-frost/70">Repository statistics are temporarily unavailable.</p>
            ) : (
              <div className="grid grid-cols-2 gap-y-4 sm:grid-cols-4 lg:grid-cols-7">
                {(statItems.length ? statItems : Array.from({ length: 7 }).map(() => [null, ""])).map(([n, l], i) => (
                  <div key={i} className="px-1">
                    {n === null ? <Skeleton className="h-7 w-14 opacity-20" /> : <p className="font-display text-[28px] leading-none text-white">{fmtNum(n as number)}</p>}
                    <p className="mt-1.5 text-[12px] text-frost/70">{l}</p>
                  </div>
                ))}
              </div>
            )}
            <p className="mt-3 font-mono text-[10.5px] uppercase tracking-wider text-mist">Prototype demonstration repository — counts describe the demo corpus, not institutional holdings.</p>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------ ONE KNOWLEDGE LAYER */}
      <section className="border-b border-frost bg-white">
        <div className="mx-auto max-w-[1280px] px-4 py-12 md:px-8">
          <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-cyan-deep">The idea in one line</p>
              <h2 className="mt-2 text-[28px] leading-tight text-night md:text-[32px]">One Knowledge Layer. Multiple Ways to Discover, Understand and Share Polar Science.</h2>
              <dl className="mt-6 grid gap-4 sm:grid-cols-2">
                {[
                  ["Problem", "Polar knowledge is spread across reports, datasets, expeditions and media."],
                  ["Solution", `${BRAND} unifies discovery, intelligence and outreach on one metadata-rich repository.`],
                  ["Innovation", "Evidence-grounded AI + content studio + human review, all source-linked."],
                  ["Impact", "Better access, understanding and dissemination of polar science."],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-xl border border-frost bg-snow p-4">
                    <dt className="font-mono text-[10.5px] uppercase tracking-wider text-cyan-deep">{k}</dt>
                    <dd className="mt-1 text-[14px] leading-relaxed text-ink-soft">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <ol className="relative grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
              {PIPELINE.map((s, i) => {
                const I = s.icon;
                return (
                  <li key={s.label} className="flex items-center gap-4 rounded-xl border border-frost bg-white px-4 py-3 shadow-card" style={{ marginLeft: `min(${i * 18}px, 6vw)` }}>
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-night text-aurora">
                      <I className="h-4.5 w-4.5" />
                    </span>
                    <span className="font-mono text-[11px] text-mist">0{i + 1}</span>
                    <span className="min-w-0">
                      <span className="block font-medium text-night">{s.label}</span>
                      <span className="block text-[13px] text-steel">{s.text}</span>
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-[1280px] space-y-16 px-4 py-14 md:px-8">
        {/* ------------------------------------------------------------ FEATURED AREAS */}
        <section>
          <SectionTitle eyebrow="Discover" title="Everything polar, connected" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {AREAS.map((a) => {
              const I = a.icon;
              return (
                <Link key={a.href} href={a.href} className="group flex items-start gap-4 rounded-2xl border border-frost bg-white p-5 shadow-card transition-all hover:-translate-y-0.5 hover:border-glacier hover:shadow-lift">
                  <span className="rounded-xl bg-ice p-3 text-cyan-deep transition-colors group-hover:bg-night group-hover:text-aurora">
                    <I className="h-5 w-5" />
                  </span>
                  <span>
                    <span className="block font-display text-[18px] text-night">{a.title}</span>
                    <span className="mt-1 block text-[14px] text-ink-soft">{a.text}</span>
                  </span>
                </Link>
              );
            })}
          </div>
        </section>

        {/* ------------------------------------------------------------ FEATURED RESEARCH */}
        <section>
          <SectionTitle
            eyebrow="Repository"
            title="Featured Research"
            action={<LinkButton href="/documents" variant="secondary" size="sm">All documents <ArrowRight className="h-3.5 w-3.5" /></LinkButton>}
          />
          {featured.error ? (
            <ErrorState error={featured.error} onRetry={featured.reload} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {featured.loading || !featured.data
                ? Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)
                : featured.data.results.map((r) => <ResourceCard key={r.id} item={r} />)}
            </div>
          )}
        </section>

        {/* ------------------------------------------------------------ POLAR EXPLORATION */}
        <section>
          <SectionTitle eyebrow="Polar exploration" title="Where the science happens" action={<LinkButton href="/map" variant="secondary" size="sm">Open Polar Map</LinkButton>} />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {REGIONS.map((r) => (
              <Link key={r.title} href={r.href} className="group relative aspect-[4/5] overflow-hidden rounded-2xl shadow-card">
                <PolarScene scene={r.scene} seed={r.title} title={r.title} className="absolute inset-0 h-full w-full transition-transform duration-700 group-hover:scale-105" />
                <div className="absolute inset-0 bg-gradient-to-t from-abyss via-abyss/50 to-transparent" />
                <div className="absolute inset-x-0 bottom-0 p-5 text-white">
                  <p className="font-display text-[22px] leading-tight">{r.title}</p>
                  <p className="mt-1 text-[13px] text-frost/85">{r.text}</p>
                  <span className="mt-3 inline-flex items-center gap-1 text-[13px] text-aurora">Explore <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" /></span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------------------ AI */}
        <section className="grid gap-6 overflow-hidden rounded-3xl bg-night p-6 text-white md:p-10 lg:grid-cols-2">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-aurora">Evidence-grounded AI</p>
            <h2 className="mt-2 text-[30px] leading-tight">Ask {BRAND} AI</h2>
            <p className="mt-3 max-w-md text-[15px] leading-relaxed text-frost/80">
              Questions are answered only from passages retrieved from the repository. Every claim carries a citation you can open — and when the evidence isn&apos;t there, the assistant says so.
            </p>
            <ul className="mt-5 space-y-2 text-[14px] text-frost/85">
              {["Hybrid retrieval: keyword + vector search", "Numbered citations linked to source passages", "Evidence strength shown with every answer", "Ask about the whole repository or one document"].map((t) => (
                <li key={t} className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-aurora" /> {t}</li>
              ))}
            </ul>
            <LinkButton href="/assistant?q=What%20factors%20influence%20Antarctic%20sea-ice%20variability%3F" className="mt-6" icon={<Bot className="h-4 w-4" />}>Ask the AI</LinkButton>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-[13px] text-glacier">Example question</p>
            <p className="mt-1 font-display text-[19px]">“What factors influence Antarctic sea-ice variability?”</p>
            <div className="mt-4 rounded-xl bg-white p-4 text-ink">
              <div className="mb-2 flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1 rounded-full bg-[#e2f4f1] px-2 py-0.5 text-[11.5px] font-medium text-teal"><ShieldCheck className="h-3 w-3" /> Strong repository evidence</span>
                <DemoBadge label="Example" />
              </div>
              <p className="text-[14px] leading-relaxed">
                The study identifies interacting factors — <strong>wind patterns</strong>, <strong>ocean heat below the ice</strong> and the <strong>timing of autumn freeze-up</strong> — with large-scale atmospheric variability modulating regional winds
                <span className="mx-0.5 rounded bg-[#e3f4fa] px-1 font-mono text-[10.5px] text-cyan-deep">1</span>.
              </p>
              <p className="mt-3 border-t border-frost pt-2 text-[12px] text-steel"><span className="font-mono">[1]</span> Antarctic Sea Ice Variability Study — Key Findings</p>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------ OUTREACH */}
        <section className="grid gap-8 lg:grid-cols-[1fr_1fr] lg:items-center">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-cyan-deep">Content Studio</p>
            <h2 className="mt-2 text-[30px] leading-tight text-night">Turn Research Into Understanding</h2>
            <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-ink-soft">
              Researchers turn a scientific resource into audience-ready drafts. Each draft keeps its source passages attached, passes an automated evidence check, and is published only after an editor approves it.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <LinkButton href="/studio" icon={<SquarePen className="h-4 w-4" />}>Open Content Studio</LinkButton>
              <LinkButton href="/outreach" variant="secondary">See published outreach</LinkButton>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["Student-friendly explanations", "Simple words, a glossary of key terms"],
              ["Public summaries", "Plain language with the caveats kept"],
              ["Social-media posts", "LinkedIn and Instagram, source-linked"],
              ["Educational content", "Learning paths and quizzes"],
              ["Research highlights", "Website-ready summaries"],
              ["Media briefs", "Press-style, no invented quotes"],
            ].map(([t, d]) => (
              <div key={t} className="rounded-xl border border-frost bg-white p-4 shadow-card">
                <p className="font-medium text-night">{t}</p>
                <p className="mt-0.5 text-[13px] text-steel">{d}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* ------------------------------------------------------------ CLOSING */}
      <section className="relative overflow-hidden bg-night">
        <div className="absolute inset-0 opacity-40">
          <PolarScene scene="seaice" seed="closing" className="h-full w-full" />
        </div>
        <div className="absolute inset-0 bg-gradient-to-t from-night via-night/85 to-night/60" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center text-white">
          <h2 className="text-[34px] leading-tight md:text-[42px]">From Research to Reach</h2>
          <p className="mx-auto mt-4 max-w-xl text-[16px] leading-relaxed text-frost/85">
            {BRAND} connects scientific knowledge with the people who need to discover, understand and share it.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <LinkButton href="/explore" size="lg">Explore Knowledge</LinkButton>
            <Link href="/assistant" className="inline-flex h-12 items-center gap-2 rounded-lg border border-white/25 bg-white/5 px-5 text-[15px] font-medium text-white hover:bg-white/10">
              <Bot className="h-4 w-4 text-aurora" /> Ask {BRAND} AI
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
