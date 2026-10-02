"use client";

import { ArrowRight, Bot, LoaderCircle, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ErrorState } from "@/components/common/ui";
import { ApiError, post } from "@/lib/api";
import type { AskResponse } from "@/lib/types";
import { AnswerCard } from "./AnswerCard";

interface Turn {
  id: number;
  question: string;
  res?: AskResponse;
  error?: ApiError;
  loading: boolean;
}

const STAGES = ["Processing question", "Embedding query", "Vector + keyword retrieval", "Ranking evidence", "Composing grounded answer"];

function Thinking() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(STAGES.length - 1, x + 1)), 380);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="rounded-2xl border border-frost bg-white p-5 shadow-card" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-sm text-night">
        <LoaderCircle className="h-4 w-4 animate-spin text-cyan" /> {STAGES[i]}…
      </div>
      <div className="mt-3 flex gap-1.5">
        {STAGES.map((s, k) => (
          <span key={s} className={`h-1 flex-1 rounded-full ${k <= i ? "bg-cyan" : "bg-ice"}`} />
        ))}
      </div>
      <div className="mt-4 space-y-2">
        <div className="skeleton h-3.5 w-11/12 rounded" />
        <div className="skeleton h-3.5 w-4/5 rounded" />
        <div className="skeleton h-3.5 w-3/5 rounded" />
      </div>
    </div>
  );
}

export function AskPanel({ documentSlug, examples, initialQuestion, placeholder }: {
  documentSlug?: string;
  examples: string[];
  initialQuestion?: string;
  placeholder?: string;

}) {
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const asked = useRef(false);

  const ask = async (question: string, replaceId?: number) => {
    const text = question.trim();
    if (text.length < 2) return;
    const id = replaceId ?? Date.now();
    setTurns((t) => (replaceId ? t.map((x) => (x.id === id ? { ...x, loading: true, error: undefined } : x)) : [...t, { id, question: text, loading: true }]));
    setQ("");
    try {
      const res = await post<AskResponse>(documentSlug ? "/api/ai/document-question" : "/api/ai/ask", { question: text, document_slug: documentSlug || null });
      await new Promise((r) => setTimeout(r, 650)); // let the retrieval stages read clearly
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, res, loading: false } : x)));
    } catch (e) {
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, error: e as ApiError, loading: false } : x)));
    }
  };

  useEffect(() => {
    if (initialQuestion && !asked.current) {
      asked.current = true;
      ask(initialQuestion);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestion]);

  useEffect(() => {
    if (turns.length) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length]);

  return (
    <div className="flex flex-col gap-5">
      {turns.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {examples.map((e) => (
            <button
              key={e}
              onClick={() => ask(e)}
              className="group inline-flex items-center gap-1.5 rounded-full border border-frost bg-white px-3.5 py-1.5 text-left text-[13px] text-deep shadow-sm hover:border-cyan hover:bg-[#f0f9fc]"
            >
              <Sparkles className="h-3.5 w-3.5 text-cyan" /> {e}
            </button>
          ))}
        </div>
      )}
      {turns.map((t) => (
        <div key={t.id} className="space-y-3">
          <div className="flex justify-end">
            <p className="max-w-[85%] rounded-2xl rounded-br-md bg-night px-4 py-2.5 text-[14.5px] text-white">{t.question}</p>
          </div>
          {t.loading ? (
            <Thinking />
          ) : t.error ? (
            <ErrorState error={t.error} onRetry={() => ask(t.question, t.id)} compact />
          ) : t.res ? (
            <AnswerCard res={t.res} onRegenerate={() => ask(t.question, t.id)} />
          ) : null}
        </div>
      ))}
      <div ref={endRef} />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(q);
        }}
        className="sticky bottom-20 z-10 -mx-2 rounded-2xl bg-white/90 px-2 pb-1 pt-2 backdrop-blur lg:bottom-4"
      >
        <div className="flex items-end gap-2 rounded-2xl border border-frost bg-white p-2 shadow-lift focus-within:border-cyan focus-within:ring-2 focus-within:ring-cyan/20">
          <Bot className="mb-2.5 ml-2 h-5 w-5 shrink-0 text-cyan-deep" />
          <textarea
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(q);
              }
            }}
            rows={1}
            maxLength={1000}
            aria-label={documentSlug ? "Ask about this document" : "Ask PolarNexus AI"}
            placeholder={placeholder || "Ask a question about polar science…"}
            className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-1 py-2.5 text-[15px] text-night placeholder:text-mist focus:outline-none"
          />
          <button
            type="submit"
            disabled={q.trim().length < 2 || turns.some((t) => t.loading)}
            className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-xl bg-cyan-deep px-4 text-sm font-medium text-white hover:bg-[#0c6f8e] disabled:opacity-40"
          >
            Ask <ArrowRight className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-1.5 px-2 text-[11.5px] text-steel">
          Answers are grounded in the PolarNexus repository and cite their sources. If evidence is missing, the assistant says so.
        </p>
      </form>
    </div>
  );
}
