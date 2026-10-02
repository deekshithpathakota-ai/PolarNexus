"use client";

import { BookOpenText, FlaskConical, Plus } from "lucide-react";
import Link from "next/link";
import { PolarScene } from "@/components/art/PolarScene";
import { Badge, CardSkeleton, EmptyState, ErrorState, LinkButton, PageHeader } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Story } from "@/lib/types";

export default function StoriesPage() {
  const { can } = useAuth();
  const { data, error, loading, reload } = useApi<{ results: Story[] }>("/api/stories");
  return (
    <Container>
      <PageHeader
        eyebrow="Research Stories"
        title="Research, connected end to end"
        description="Each story links a research topic to its papers, datasets, expeditions, places, photographs, videos and people — with scientific, public and student explanations that cite their evidence."
        actions={can("generate_content") ? <LinkButton href="/stories/new" icon={<Plus className="h-4 w-4" />}>New story</LinkButton> : undefined}
      />
      {error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : loading || !data ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <CardSkeleton key={i} rows={4} />)}</div>
      ) : data.results.length === 0 ? (
        <EmptyState icon={<BookOpenText className="h-6 w-6" />} title="No research stories yet" body="Open any paper, dataset or expedition and choose “Build Research Story”." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.results.map((s) => (
            <Link key={s.slug} href={`/stories/${s.slug}`} className="group overflow-hidden rounded-2xl border border-frost bg-white shadow-card transition hover:-translate-y-0.5 hover:border-glacier hover:shadow-lift">
              <div className="relative aspect-[16/8] overflow-hidden bg-night">
                {s.cover?.extra?.thumbnail ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={s.cover.extra.thumbnail} alt="" className="h-full w-full object-cover opacity-90 transition duration-500 group-hover:scale-[1.03]" />
                ) : (
                  <PolarScene scene={s.cover?.extra?.scene || "aurora"} seed={s.slug} title={s.title} className="h-full w-full" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-night/80 to-transparent" />
                <p className="absolute bottom-3 left-4 right-4 font-mono text-[10.5px] uppercase tracking-wider text-glacier">{s.roles.slice(0, 4).join(" → ")}</p>
              </div>
              <div className="p-5">
                <div className="mb-2 flex flex-wrap items-center gap-1.5">
                  <Badge tone={s.status === "published" ? "teal" : s.status === "draft" ? "slate" : "amber"}>{s.status}</Badge>
                  {s.is_demo && <Badge tone="amber" icon={<FlaskConical className="h-3 w-3" />}>Demo</Badge>}
                  <span className="text-[12px] text-steel">{s.item_count} connected records · {fmtDate(s.updated_at)}</span>
                </div>
                <h2 className="font-display text-[19px] leading-snug text-night group-hover:text-cyan-deep">{s.title}</h2>
                <p className="mt-2 text-[12.5px] text-steel">{s.basis.authoritative} public/verified · {s.basis.demonstration} demonstration</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </Container>
  );
}
