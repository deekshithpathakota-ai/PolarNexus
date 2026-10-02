"use client";

import { Megaphone, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Markdown } from "@/components/common/Markdown";
import { Badge, CardSkeleton, EmptyState, ErrorState, PageHeader, Pagination, Tabs } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { FORMAT_LABEL, fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { ContentItem, Paged } from "@/lib/types";
import Link from "next/link";

export default function OutreachPage() {
  const [format, setFormat] = useState("all");
  const [page, setPage] = useState(1);
  const { data, error, loading, reload } = useApi<Paged<ContentItem>>("/api/outreach", { format: format === "all" ? undefined : format, page, page_size: 6 });
  return (
    <Container className="max-w-[1100px]">
      <PageHeader eyebrow="Dissemination" title="Outreach Feed" description="Polar science explained for everyone — every item here was drafted from repository sources and approved by an editor before publication." />
      <Tabs className="mb-6" value={format} onChange={(f) => { setFormat(f); setPage(1); }} tabs={[{ key: "all", label: "All" }, ...Object.entries(FORMAT_LABEL).map(([k, v]) => ({ key: k, label: v.split(" · ")[0] }))]} />
      {error ? <ErrorState error={error} onRetry={reload} /> : loading || !data ? <div className="space-y-4"><CardSkeleton rows={5} /><CardSkeleton rows={5} /></div> : data.results.length === 0 ? (
        <EmptyState icon={<Megaphone className="h-6 w-6" />} title="Nothing published in this format yet" body="Approved content appears here once an editor publishes it." />
      ) : (
        <div className="space-y-5">
          {data.results.map((c) => (
            <article key={c.id} className="overflow-hidden rounded-2xl border border-frost bg-white shadow-card">
              <div className="flex flex-wrap items-center gap-2 border-b border-frost bg-snow/60 px-6 py-3">
                <Badge tone="teal">{FORMAT_LABEL[c.format]}</Badge>
                <span className="text-[12.5px] text-steel">Published {fmtDate(c.published_at)}</span>
                <span className="ml-auto inline-flex items-center gap-1 text-[12px] text-teal"><ShieldCheck className="h-3.5 w-3.5" /> Reviewed by {c.reviewer || "editor"}</span>
              </div>
              <div className="px-6 py-5">
                <h2 className="mb-2 text-[24px] leading-tight text-night">{c.title}</h2>
                <Markdown text={c.body || ""} onCite={(n) => document.getElementById(`c${c.id}-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" })} />
              </div>
              <footer className="border-t border-frost px-6 py-4">
                <p className="mb-1.5 font-mono text-[10.5px] uppercase tracking-wider text-steel">Sources</p>
                <ol className="space-y-1 text-[13px]">
                  {c.citations?.map((s) => (
                    <li key={s.n} id={`c${c.id}-${s.n}`} className="text-ink-soft">
                      <span className="font-mono text-cyan-deep">[{s.n}]</span>{" "}
                      {s.url ? <Link href={s.url} className="text-night hover:text-cyan-deep hover:underline">{s.label}</Link> : s.label} — {s.section}
                    </li>
                  ))}
                </ol>
                <p className="mt-3 text-[12px] text-steel">Channels: {c.channels.join(", ")}{c.channels.some((x) => x !== "website") ? " (social dispatch simulated in prototype)" : ""}</p>
              </footer>
            </article>
          ))}
          <Pagination page={data.page} pages={data.pages} onPage={setPage} />
        </div>
      )}
    </Container>
  );
}
