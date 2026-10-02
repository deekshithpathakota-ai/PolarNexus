"use client";

import { Bot, FileText, Lock, MapPin, Sparkles, SquarePen } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { AskPanel } from "@/components/ai/AskPanel";
import { SummaryPanel } from "@/components/ai/SummaryPanel";
import { RelatedKnowledge } from "@/components/cards/RelatedKnowledge";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { BackLink, DetailError, DetailSkeleton, SideCard } from "@/components/common/DetailLayout";
import { ResourceActions } from "@/components/common/ResourceActions";
import { Badge, Button, Card, DemoBadge, MetaRow, Tabs } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { BRAND, fmtDate, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { DocumentDetail } from "@/lib/types";

type Tab = "overview" | "ask" | "summaries" | "fulltext";

function ResourceDetail() {
  const { slug } = useParams<{ slug: string }>();
  const sp = useSearchParams();
  const router = useRouter();
  const { can } = useAuth();
  const { data: doc, error, loading, reload } = useApi<DocumentDetail>(`/api/resources/${slug}`);
  const [tab, setTab] = useState<Tab>((sp.get("tab") as Tab) || "overview");
  const [askSeed, setAskSeed] = useState<string | undefined>(sp.get("ask") || undefined);
  const tabsRef = useRef<HTMLDivElement>(null);
  const ai = useApi<{ document_examples: string[] }>("/api/ai/status");

  useEffect(() => {
    const t = sp.get("tab") as Tab | null;
    if (t) setTab(t);
  }, [sp]);

  if (loading && !doc) return <DetailSkeleton />;
  if (error || !doc) return <DetailError error={error || { message: "Not found", status: 404 }} onRetry={reload} back={{ href: "/documents", label: "Back to Documents" }} />;

  const go = (t: Tab, question?: string) => {
    if (question) setAskSeed(question);
    setTab(t);
    setTimeout(() => tabsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };
  const sections = doc.sections.filter((s) => s.section !== "Abstract");
  const findings = doc.sections.find((s) => s.section === "Key Findings");

  return (
    <Container>
      <BackLink href="/documents" label="Back to Documents" />
      <header className="mb-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <TypeBadge type="document" kind={doc.doc_type} />
          <span className="inline-flex items-center gap-1 text-[13px] text-steel"><MapPin className="h-3.5 w-3.5" /> {doc.region}</span>
          <span className="font-mono text-[13px] text-steel">· {doc.year}</span>
          {doc.visibility === "internal" && <Badge tone="amber" icon={<Lock className="h-3 w-3" />}>Internal</Badge>}
          {doc.is_demo && <DemoBadge label="Prototype demonstration document" />}
        </div>
        <h1 className="max-w-4xl text-[30px] leading-tight text-night md:text-[40px]">{doc.title}</h1>
        <p className="mt-3 text-[15px] text-ink-soft">
          {doc.authors.join(", ")} <span className="text-mist">·</span> {doc.institution}
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={() => go("ask")} icon={<Bot className="h-4 w-4" />}>Ask {BRAND} AI</Button>
          <Button variant="secondary" onClick={() => go("summaries")} icon={<Sparkles className="h-4 w-4 text-cyan-deep" />}>Generate Summary</Button>
          <Button
            variant="dark"
            onClick={() => (can("generate_content") ? router.push(`/studio?type=document&slug=${doc.slug}`) : router.push(`/login?next=${encodeURIComponent(`/studio?type=document&slug=${doc.slug}`)}`))}
            icon={<SquarePen className="h-4 w-4" />}
          >
            Generate Outreach Content
          </Button>
          <div className="flex flex-wrap gap-2 sm:ml-auto">
            <ResourceActions itemType="document" slug={doc.slug} label={doc.title} citation={doc.citation} download={`/api/resources/${doc.slug}/download`} />
          </div>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          <div ref={tabsRef} className="scroll-mt-20">
            <Tabs
              value={tab}
              onChange={setTab}
              tabs={[
                { key: "overview", label: "Overview" },
                { key: "ask", label: <span className="inline-flex items-center gap-1.5"><Bot className="h-3.5 w-3.5" /> Ask about this document</span> },
                { key: "summaries", label: "AI Summaries" },
                { key: "fulltext", label: `Full text · ${doc.sections.length} passages` },
              ]}
            />
          </div>

          {tab === "overview" && (
            <>
              <Card className="p-6">
                <h2 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">Abstract</h2>
                <p className="text-[16px] leading-[1.75] text-ink">{doc.abstract}</p>
              </Card>
              {findings && (
                <Card className="p-6">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h2 className="font-mono text-[11px] uppercase tracking-wider text-steel">Key findings · from the source</h2>
                    <span className="text-[12px] text-steel">p. {findings.page}</span>
                  </div>
                  <p className="text-[15px] leading-[1.75] text-ink-soft">{findings.text}</p>
                </Card>
              )}
              <Card className="p-6">
                <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Ask about this document</h2>
                <div className="flex flex-wrap gap-2">
                  {(ai.data?.document_examples || []).map((q) => (
                    <button key={q} onClick={() => go("ask", q)} className="rounded-full border border-frost bg-white px-3.5 py-1.5 text-[13px] text-deep hover:border-cyan hover:bg-[#f0f9fc]">
                      {q}
                    </button>
                  ))}
                </div>
              </Card>
              <RelatedKnowledge related={doc.related} graph={{ type: "document", slug: doc.slug }} />
            </>
          )}

          {tab === "ask" && (
            <Card className="p-5">
              <p className="mb-4 text-[14px] text-ink-soft">
                Questions here are answered from <strong className="text-night">{doc.title}</strong> first. Citations point to the document&apos;s own sections and pages.
              </p>
              <AskPanel key={askSeed || "ask"} documentSlug={doc.slug} examples={ai.data?.document_examples || []} initialQuestion={askSeed} placeholder="Ask about this document — methodology, findings, figures, limitations…" />
            </Card>
          )}

          {tab === "summaries" && (
            <Card className="p-5">
              <SummaryPanel slug={doc.slug} />
            </Card>
          )}

          {tab === "fulltext" && (
            <Card className="divide-y divide-frost">
              {[doc.sections.find((s) => s.section === "Abstract"), ...sections].filter(Boolean).map((s) => (
                <section key={s!.chunk_id} id={`chunk-${s!.chunk_id}`} className="p-6">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <h3 className="flex items-center gap-2 font-sans text-[15px] font-semibold text-night"><FileText className="h-4 w-4 text-mist" /> {s!.section}</h3>
                    <span className="font-mono text-[11px] text-mist">page {s!.page} · passage #{s!.chunk_id}</span>
                  </div>
                  <p className="text-[15px] leading-[1.75] text-ink-soft">{s!.text}</p>
                </section>
              ))}
            </Card>
          )}
        </div>

        <aside className="space-y-4">
          <SideCard title="Metadata">
            <dl>
              <MetaRow label="Type">{doc.doc_type}</MetaRow>
              <MetaRow label="Authors">{doc.authors.join(", ")}</MetaRow>
              <MetaRow label="Institution">{doc.institution}</MetaRow>
              <MetaRow label="Region">{doc.region}</MetaRow>
              <MetaRow label="Year">{doc.year}</MetaRow>
              <MetaRow label="Language">{doc.language}</MetaRow>
              <MetaRow label="Pages">{doc.page_count}</MetaRow>
              <MetaRow label="File">{doc.file_name || "—"}</MetaRow>
              <MetaRow label="Status"><Badge tone="teal">{doc.status === "indexed" ? "Indexed & searchable" : doc.status}</Badge></MetaRow>
              <MetaRow label="Added">{fmtDate(doc.created_at)}</MetaRow>
              <MetaRow label="Views">{fmtNum(doc.views)}</MetaRow>
              <MetaRow label="Source">{doc.source}</MetaRow>
            </dl>
          </SideCard>
          <SideCard title="Topics">
            <div className="flex flex-wrap gap-1.5">
              {doc.topics.map((t) => (
                <Link key={t.slug} href={`/explore?topic=${t.slug}`} className="rounded-full bg-ice px-2.5 py-1 text-[12.5px] text-deep hover:bg-frost">{t.name}</Link>
              ))}
            </div>
            {doc.keywords.length > 0 && (
              <>
                <h3 className="mb-1.5 mt-4 font-mono text-[11px] uppercase tracking-wider text-steel">Keywords</h3>
                <p className="text-[13px] text-ink-soft">{doc.keywords.join(" · ")}</p>
              </>
            )}
          </SideCard>
          <SideCard title="Linked">
            <ul className="space-y-1.5 text-[13.5px]">
              {(["station", "expedition", "dataset", "researcher"] as const).flatMap((k) =>
                (doc.related.groups[k] || []).slice(0, 3).map((r) => (
                  <li key={`${k}${r.id}`}>
                    <Link href={r.url} className="text-cyan-deep hover:underline">{r.title}</Link>
                    <span className="text-mist"> · {r.kind}</span>
                  </li>
                )),
              )}
            </ul>
          </SideCard>
        </aside>
      </div>
    </Container>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <ResourceDetail />
    </Suspense>
  );
}
