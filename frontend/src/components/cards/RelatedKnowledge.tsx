"use client";

import { Network } from "lucide-react";
import { useState } from "react";
import { Card, Tabs } from "@/components/common/ui";
import type { Related } from "@/lib/types";
import { KnowledgeGraph } from "./KnowledgeGraph";
import { ResourceRow } from "./ResourceCard";

const LABELS: Record<string, string> = {
  document: "Documents",
  dataset: "Datasets",
  expedition: "Expeditions",
  station: "Stations",
  media: "Media",
  researcher: "Researchers",
  activity: "Institutional Activities",
  content: "Published Outreach",
};

export function RelatedKnowledge({ related, graph }: { related: Related; graph?: { type: string; slug: string } }) {
  const groups = Object.entries(related.groups).filter(([, v]) => v.length);
  const [view, setView] = useState<"list" | "graph">("list");
  return (
    <Card className="p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg text-night">
          <Network className="h-4.5 w-4.5 text-cyan-deep" /> Related Knowledge
        </h2>
        {graph && (
          <Tabs
            value={view}
            onChange={setView}
            tabs={[
              { key: "list", label: "Linked records" },
              { key: "graph", label: "Graph view" },
            ]}
          />
        )}
      </div>
      {view === "graph" && graph ? (
        <KnowledgeGraph type={graph.type} slug={graph.slug} />
      ) : groups.length === 0 && related.similar.length === 0 ? (
        <p className="text-sm text-steel">No linked records yet.</p>
      ) : (
        <div className="grid gap-x-6 gap-y-4 md:grid-cols-2">
          {groups.map(([type, items]) => (
            <div key={type}>
              <p className="mb-1 font-mono text-[10.5px] uppercase tracking-wider text-steel">
                {LABELS[type] || type} · {items.length}
              </p>
              <div className="-mx-2.5">
                {items.slice(0, 5).map((i) => <ResourceRow key={`${i.type}${i.id}`} item={i} />)}
              </div>
            </div>
          ))}
          {related.similar.length > 0 && (
            <div className="md:col-span-2">
              <p className="mb-1 font-mono text-[10.5px] uppercase tracking-wider text-steel">Similar by topic</p>
              <div className="-mx-2.5 grid md:grid-cols-2">
                {related.similar.slice(0, 4).map((i) => <ResourceRow key={`s${i.type}${i.id}`} item={i} />)}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
