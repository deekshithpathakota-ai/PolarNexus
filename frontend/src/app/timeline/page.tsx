"use client";

import { useState } from "react";
import { Card, Field, PageHeader, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { KnowledgeTimeline } from "@/components/timeline/KnowledgeTimeline";
import { useApi } from "@/lib/hooks";

export default function TimelinePage() {
  const topics = useApi<{ results: { slug: string; name: string; count: number }[] }>("/api/topics");
  const exps = useApi<{ results: { slug: string; name: string }[] }>("/api/expeditions");
  const stations = useApi<{ results: { slug: string; name: string }[] }>("/api/stations");
  const researchers = useApi<{ results: { slug: string; name: string }[] }>("/api/researchers", { page_size: 60 });
  const [scope, setScope] = useState<{ topic?: string; expedition?: string; station?: string; researcher?: string }>({ topic: "sea-ice" });
  const pick = (k: "topic" | "expedition" | "station" | "researcher") => (e: { target: { value: string } }) =>
    setScope({ ...scope, [k]: e.target.value || undefined });
  return (
    <Container>
      <PageHeader eyebrow="Discovery" title="Knowledge Timeline"
        description="How knowledge on a topic, expedition, station or researcher has accumulated over time — observations, expeditions, datasets, papers, media, events and outreach, in order." />
      <Card className="mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Topic">
          <select className={inputCls} value={scope.topic || ""} onChange={pick("topic")}>
            <option value="">Any topic</option>
            {topics.data?.results.filter((t) => t.count).map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
          </select>
        </Field>
        <Field label="Expedition">
          <select className={inputCls} value={scope.expedition || ""} onChange={pick("expedition")}>
            <option value="">Any expedition</option>
            {exps.data?.results.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
          </select>
        </Field>
        <Field label="Station">
          <select className={inputCls} value={scope.station || ""} onChange={pick("station")}>
            <option value="">Any station</option>
            {stations.data?.results.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
          </select>
        </Field>
        <Field label="Researcher">
          <select className={inputCls} value={scope.researcher || ""} onChange={pick("researcher")}>
            <option value="">Any researcher</option>
            {researchers.data?.results.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
          </select>
        </Field>
      </Card>
      <Card className="p-5 md:p-6">
        <KnowledgeTimeline key={JSON.stringify(scope)} scope={scope} />
      </Card>
    </Container>
  );
}
