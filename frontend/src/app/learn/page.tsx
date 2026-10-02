"use client";

import clsx from "clsx";
import { CircleCheck, CircleX, GraduationCap, Lightbulb, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { TypeBadge } from "@/components/cards/ResourceCard";
import { Button, Card, ErrorState, PageHeader, Skeleton, Tabs } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useApi } from "@/lib/hooks";

interface Lesson { title: string; summary: string; resources: { type: string; slug: string; title: string; kind: string; url: string }[] }
interface Quiz { q: string; options: string[]; answer: number; explain: string; source_title: string; source_url: string }
interface Path { level: string; title: string; description: string; lessons: Lesson[]; quiz: Quiz[] }

function QuizBlock({ quiz }: { quiz: Quiz[] }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const score = Object.entries(answers).filter(([i, a]) => quiz[Number(i)].answer === a).length;
  return (
    <div className="space-y-4">
      {quiz.map((q, i) => {
        const chosen = answers[i];
        return (
          <fieldset key={q.q} className="rounded-xl border border-frost p-4">
            <legend className="px-1 text-[14.5px] font-medium text-night">{i + 1}. {q.q}</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {q.options.map((o, k) => {
                const isRight = chosen !== undefined && k === q.answer;
                const isWrong = chosen === k && k !== q.answer;
                return (
                  <button key={o} disabled={chosen !== undefined} onClick={() => setAnswers((a) => ({ ...a, [i]: k }))}
                    className={clsx("flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-[13.5px] transition",
                      isRight ? "border-teal bg-[#e2f4f1] text-teal" : isWrong ? "border-coral bg-[#fbe9e5] text-coral" : "border-frost hover:border-glacier disabled:opacity-60")}>
                    {isRight ? <CircleCheck className="h-4 w-4 shrink-0" /> : isWrong ? <CircleX className="h-4 w-4 shrink-0" /> : <span className="h-4 w-4 shrink-0 rounded-full border border-mist" />}
                    {o}
                  </button>
                );
              })}
            </div>
            {chosen !== undefined && (
              <p className="mt-3 rounded-lg bg-snow p-3 text-[13px] text-ink-soft">
                {q.explain} <Link href={q.source_url} className="text-cyan-deep hover:underline">Source: {q.source_title}</Link>
              </p>
            )}
          </fieldset>
        );
      })}
      <div className="flex items-center justify-between rounded-xl bg-night px-4 py-3 text-white">
        <span>Score: <strong>{score}</strong> / {quiz.length}{Object.keys(answers).length < quiz.length ? " (in progress)" : ""}</span>
        <Button size="sm" variant="secondary" onClick={() => setAnswers({})} icon={<RotateCcw className="h-3.5 w-3.5" />}>Restart</Button>
      </div>
    </div>
  );
}

export default function LearnPage() {
  const { data, error, loading, reload } = useApi<{ paths: Path[] }>("/api/education");
  const [level, setLevel] = useState("beginner");
  const [view, setView] = useState<"lessons" | "quiz">("lessons");
  const path = data?.paths.find((p) => p.level === level);
  return (
    <Container className="max-w-[1100px]">
      <PageHeader eyebrow="Smart Education" title="Learn Polar Science" description="Guided learning paths from first questions to real research — every lesson links to repository records, and every quiz answer cites its source." />
      <Tabs className="mb-6 w-fit" value={level} onChange={(l) => { setLevel(l); setView("lessons"); }} tabs={[{ key: "beginner", label: "Beginner" }, { key: "intermediate", label: "Intermediate" }, { key: "advanced", label: "Advanced" }]} />
      {error ? <ErrorState error={error} onRetry={reload} /> : loading || !path ? <Skeleton className="h-96 w-full rounded-2xl" /> : (
        <>
          <Card className="mb-6 flex flex-wrap items-center gap-4 bg-night p-6 text-white">
            <GraduationCap className="h-10 w-10 text-aurora" />
            <div className="min-w-0 flex-1">
              <h2 className="text-[24px]">{path.title}</h2>
              <p className="text-frost/80">{path.description}</p>
            </div>
            <Tabs value={view} onChange={setView} tabs={[{ key: "lessons", label: `Lessons · ${path.lessons.length}` }, { key: "quiz", label: `Quiz · ${path.quiz.length}` }]} />
          </Card>
          {view === "lessons" ? (
            <ol className="grid gap-4 md:grid-cols-2">
              {path.lessons.map((l, i) => (
                <li key={l.title}>
                  <Card className="h-full p-5">
                    <p className="font-mono text-[11px] text-cyan-deep">LESSON {i + 1}</p>
                    <h3 className="mt-1 font-display text-[20px] text-night">{l.title}</h3>
                    <p className="mt-2 flex gap-2 text-[14px] leading-relaxed text-ink-soft"><Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber" /> {l.summary}</p>
                    <div className="mt-4 space-y-1.5 border-t border-frost pt-3">
                      {l.resources.map((r) => (
                        <Link key={r.url} href={r.url} className="flex items-center gap-2 rounded-lg px-1 py-1 text-[13.5px] text-night hover:bg-snow hover:text-cyan-deep">
                          <TypeBadge type={r.type} kind={r.kind} /> <span className="truncate">{r.title}</span>
                        </Link>
                      ))}
                    </div>
                  </Card>
                </li>
              ))}
            </ol>
          ) : (
            <QuizBlock key={level} quiz={path.quiz} />
          )}
        </>
      )}
    </Container>
  );
}
