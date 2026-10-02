"use client";

import { Cpu, Database, Layers, Search, ShieldCheck } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AskPanel } from "@/components/ai/AskPanel";
import { Card, GLOSSARY, InfoTip, PageHeader } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { BRAND } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Status {
  llm_configured: boolean;
  llm_model: string | null;
  embedding_description: string;
  vector_backend: string;
  fallback: string | null;
  examples: string[];
}

const STEPS = ["Question", "Query processing", "Embedding", "Vector search", "Keyword search", "Hybrid fusion", "Evidence", "Grounded answer", "Citations"];

function Assistant() {
  const sp = useSearchParams();
  const status = useApi<Status>("/api/ai/status");
  const s = status.data;
  return (
    <Container className="max-w-[1180px]">
      <PageHeader
        eyebrow="Intelligence"
        title={`${BRAND} AI`}
        description="Ask questions about polar science. Answers are built only from repository evidence, with citations you can open and an honest evidence rating."
      />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0">
          <AskPanel examples={s?.examples || []} initialQuestion={sp.get("q") || undefined} />
        </div>
        <aside className="space-y-4">
          <Card className="p-5">
            <p className="mb-3 flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-steel">
              How answers are made <InfoTip label="RAG" text={GLOSSARY.rag} />
            </p>
            <ol className="relative space-y-2 border-l border-frost pl-4">
              {STEPS.map((st, i) => (
                <li key={st} className="relative text-[13px] text-ink-soft">
                  <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white bg-cyan" />
                  <span className="font-mono text-[10.5px] text-mist">{String(i + 1).padStart(2, "0")}</span> {st}
                </li>
              ))}
            </ol>
          </Card>
          <Card className="p-5 text-[13px]">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Active configuration</p>
            <ul className="space-y-3 text-ink-soft">
              <li className="flex gap-2"><Cpu className="mt-0.5 h-4 w-4 shrink-0 text-cyan-deep" /><span><strong className="text-night">Generation:</strong> {s ? (s.llm_configured ? `LLM (${s.llm_model})` : "No LLM key — extractive answers and labelled demo responses") : "…"}</span></li>
              <li className="flex gap-2"><Layers className="mt-0.5 h-4 w-4 shrink-0 text-cyan-deep" /><span><strong className="text-night">Embeddings:</strong> {s?.embedding_description || "…"}</span></li>
              <li className="flex gap-2"><Database className="mt-0.5 h-4 w-4 shrink-0 text-cyan-deep" /><span><strong className="text-night">Vector store:</strong> {s?.vector_backend || "…"}</span></li>
              <li className="flex gap-2"><Search className="mt-0.5 h-4 w-4 shrink-0 text-cyan-deep" /><span><strong className="text-night">Keyword:</strong> PostgreSQL full-text search (BM25 fallback)</span></li>
              <li className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-teal" /><span>Citations are validated: a marker that doesn&apos;t match retrieved evidence is removed.</span></li>
            </ul>
          </Card>
        </aside>
      </div>
    </Container>
  );
}

export default function Page() {
  return (
    <Suspense>
      <Assistant />
    </Suspense>
  );
}
