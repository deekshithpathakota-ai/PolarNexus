"use client";

import clsx from "clsx";
import { ArrowRight, Ship, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { CardSkeleton, DemoBadge, ErrorState, PageHeader, Tabs, Badge } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useApi } from "@/lib/hooks";
import type { Expedition } from "@/lib/types";

const PROGRAM_COLOR: Record<string, string> = { Antarctic: "bg-cyan", Arctic: "bg-[#7b6cd9]", "Southern Ocean": "bg-teal", Himalayan: "bg-amber" };

export default function ExpeditionsPage() {
  const [program, setProgram] = useState<string>("all");
  const { data, error, loading, reload } = useApi<{ results: Expedition[]; programs: string[] }>("/api/expeditions", { program: program === "all" ? undefined : program });
  const items = data?.results || [];
  const decades = Array.from(new Set(items.map((e) => Math.floor(e.year / 10) * 10)));

  return (
    <Container>
      <PageHeader
        eyebrow="History"
        title="Expedition Explorer"
        description="India's Antarctic, Arctic, Southern Ocean and Himalayan expeditions — each linked to the stations visited, the data collected and the reports produced."
      >
        <p className="mt-3 max-w-2xl text-[12.5px] text-steel">
          Records marked <DemoBadge label="Demo" /> use illustrative objectives and highlights. Records without the mark carry only widely published facts (season, significance); verify against official NCPOR sources before external use.
        </p>
      </PageHeader>
      <Tabs
        className="mb-6 w-fit"
        value={program}
        onChange={setProgram}
        tabs={[{ key: "all", label: "All programmes" }, ...(data?.programs || ["Antarctic", "Arctic", "Southern Ocean", "Himalayan"]).map((p) => ({ key: p, label: p }))]}
      />
      {error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : loading ? (
        <div className="grid gap-4 md:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}</div>
      ) : (
        <div className="relative">
          <div className="absolute bottom-0 left-[15px] top-0 w-px bg-frost md:left-1/2" aria-hidden />
          {decades.map((d) => (
            <section key={d} className="relative mb-6">
              <div className="sticky top-[72px] z-10 mb-4 flex md:justify-center">
                <span className="rounded-full bg-night px-3 py-1 font-mono text-[12px] text-white shadow-card">{d}s</span>
              </div>
              <ol className="space-y-4">
                {items.filter((e) => Math.floor(e.year / 10) * 10 === d).map((e, i) => (
                  <li key={e.slug} className={clsx("relative pl-10 md:w-1/2 md:pl-0", i % 2 === 0 ? "md:pr-10" : "md:ml-auto md:pl-10")}>
                    <span className={clsx("absolute left-[9px] top-6 h-3.5 w-3.5 rounded-full border-2 border-white shadow", PROGRAM_COLOR[e.program] || "bg-cyan", i % 2 === 0 ? "md:left-auto md:-right-[7px]" : "md:-left-[7px]")} />
                    <Link href={`/expeditions/${e.slug}`} className="group block rounded-2xl border border-frost bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:border-glacier hover:shadow-lift">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Badge tone="amber" icon={<Ship className="h-3 w-3" />}>{e.program}</Badge>
                        <span className="font-mono text-[12px] text-steel">{e.season}</span>
                        {e.is_demo ? <DemoBadge label="Demo" className="ml-auto" /> : <Badge tone="teal" className="ml-auto">Published facts</Badge>}
                      </div>
                      <h3 className="font-display text-[19px] text-night group-hover:text-cyan-deep">{e.name}</h3>
                      <p className="mt-1.5 line-clamp-2 text-[13.5px] text-ink-soft">{e.objective}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-1.5">
                        {e.themes.slice(0, 3).map((t) => <span key={t} className="rounded-full bg-snow px-2 py-0.5 text-[11.5px] text-ink-soft ring-1 ring-frost">{t}</span>)}
                        <span className="ml-auto inline-flex items-center gap-1 text-[12px] text-steel"><Users className="h-3.5 w-3.5" /> {e.participants}</span>
                        <ArrowRight className="h-4 w-4 text-mist group-hover:text-cyan-deep" />
                      </div>
                    </Link>
                  </li>
                ))}
              </ol>
            </section>
          ))}
        </div>
      )}
    </Container>
  );
}
