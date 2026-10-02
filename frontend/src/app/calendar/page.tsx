"use client";

import { Megaphone } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ContentCalendar } from "@/components/campaigns/ContentCalendar";
import { Card, ErrorState, LinkButton, PageHeader, Skeleton } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useApi } from "@/lib/hooks";
import type { CampaignItemT } from "@/lib/types";

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function CalendarPage() {
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const start = new Date(month.getFullYear(), month.getMonth(), 1);
  start.setDate(start.getDate() - 7);
  const end = new Date(month.getFullYear(), month.getMonth() + 1, 7);
  const [selected, setSelected] = useState<CampaignItemT | null>(null);
  const { data, error, loading, reload } = useApi<{ events: CampaignItemT[] }>("/api/calendar", { start: iso(start), end: iso(end) });
  return (
    <Container>
      <PageHeader eyebrow="Outreach" title="Content Calendar" description="Every planned, scheduled and published outreach item across campaigns."
        actions={<LinkButton href="/campaigns" variant="secondary" icon={<Megaphone className="h-4 w-4" />}>Campaigns</LinkButton>} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <Card className="min-w-0 p-5">
          {error ? <ErrorState error={error} onRetry={reload} /> : loading && !data ? <Skeleton className="h-[480px] w-full" /> : (
            <ContentCalendar month={month} onMonth={setMonth} items={data?.events || []} onSelect={setSelected} />
          )}
        </Card>
        <Card className="h-fit p-5">
          {selected ? (
            <div>
              <p className="font-mono text-[10.5px] uppercase tracking-wider text-steel">{selected.campaign?.name}</p>
              <h2 className="mt-1 font-display text-[18px] text-night">{selected.title}</h2>
              <p className="mt-1 text-[13px] text-ink-soft">{selected.scheduled_for} · {selected.channel_label}{selected.simulated_channels.length ? " (simulated)" : ""} · {selected.status}</p>
              {selected.blockers.length > 0 && <p className="mt-2 rounded-lg bg-[#fbf1df] px-3 py-2 text-[12.5px] text-[#7a520b]">{selected.blockers[0]}</p>}
              {selected.campaign && <Link href={`/campaigns/${selected.campaign.slug}`} className="mt-3 inline-block text-[13px] text-cyan-deep hover:underline">Open campaign →</Link>}
            </div>
          ) : <p className="text-[13.5px] text-steel">Select an item to see its status and what it still needs.</p>}
        </Card>
      </div>
    </Container>
  );
}
