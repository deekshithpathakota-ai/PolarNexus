"use client";

import clsx from "clsx";
import { FlaskConical, Radio } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardSkeleton, ErrorState, PageHeader, SectionTitle } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { FORMAT_LABEL, fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Row { view: number; click: number; share: number; complete: number; engagement_rate: number | null; completion_rate: number | null }
interface Analytics {
  basis: { label: string; demo_events: number; live_events: number; include_demo: boolean; note: string };
  window_days: number;
  totals: Row;
  campaigns: (Row & { id: number; name: string; slug: string | null })[];
  content: (Row & { id: number; title: string; format: string; audience: string })[];
  audiences: (Row & { key: string; label: string })[];
  channels: (Row & { key: string; label: string; live: boolean })[];
  formats: (Row & { key: string })[];
  months: { month: string; view: number; click: number; share: number; complete: number }[];
  weeks: { week: string; view: number; click: number; share: number; complete: number }[];
  popular_topics: { topic: string; views: number }[];
  conversion: { research_records: number; records_with_outreach: number; rate: number | null; drafts_generated: number; published: number; publish_rate: number | null; note: string };
}

const pct = (v: number | null) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card className="p-4">
      <p className="font-mono text-[10.5px] uppercase tracking-wider text-steel">{label}</p>
      <p className="mt-1 font-display text-[28px] leading-tight text-night">{value}</p>
      {sub && <p className="text-[12px] text-steel">{sub}</p>}
    </Card>
  );
}

/** Single-hue magnitude bars; the value is always printed, so the bar never carries meaning alone. */
function Bars({ rows }: { rows: { label: string; value: number; note?: string }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (!rows.length) return <p className="text-[13px] text-steel">No events in this window.</p>;
  return (
    <ul className="space-y-2">
      {rows.map((r) => (
        <li key={r.label} className="grid grid-cols-[minmax(0,160px)_1fr_56px] items-center gap-3 text-[13px]" title={`${r.label}: ${fmtNum(r.value)} views${r.note ? ` · ${r.note}` : ""}`}>
          <span className="truncate text-ink-soft">{r.label}{r.note && <span className="ml-1 text-[11px] text-mist">{r.note}</span>}</span>
          <span className="h-2.5 rounded-full bg-ice" aria-hidden><span className="block h-full rounded-full bg-cyan-deep" style={{ width: `${(r.value / max) * 100}%` }} /></span>
          <span className="text-right font-mono text-[12px] text-night">{fmtNum(r.value)}</span>
        </li>
      ))}
    </ul>
  );
}

export default function OutreachAnalyticsPage() {
  const [includeDemo, setIncludeDemo] = useState(true);
  const { user, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (ready && !user) router.replace("/login?next=/outreach-analytics");
  }, [ready, user, router]);
  const { data: d, error, loading, reload } = useApi<Analytics>(user ? "/api/outreach-analytics" : null, { include_demo: includeDemo });
  const demo = d && d.basis.label !== "LIVE METRICS";
  return (
    <Container>
      <PageHeader eyebrow="Measure" title="Outreach Impact Analytics" description="How published outreach performs — by campaign, content, audience, channel and format — and how much research turns into outreach.">
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {d && (
            <span className={clsx("inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-mono text-[11px] uppercase tracking-wide",
              demo ? "border border-dashed border-[#e2c58f] bg-[#fdf8ee] text-[#8a5c0c]" : "border border-[#bfe5df] bg-[#e2f4f1] text-teal")}>
              {demo ? <FlaskConical className="h-3.5 w-3.5" aria-hidden /> : <Radio className="h-3.5 w-3.5" aria-hidden />} {d.basis.label}
            </span>
          )}
          <label className="inline-flex items-center gap-2 text-[13px] text-ink-soft">
            <input type="checkbox" checked={includeDemo} onChange={(e) => setIncludeDemo(e.target.checked)} /> Include demonstration metrics
          </label>
        </div>
      </PageHeader>
      {error ? <ErrorState error={error} onRetry={reload} /> : loading && !d ? (
        <div className="grid gap-4 md:grid-cols-4">{[0, 1, 2, 3].map((i) => <CardSkeleton key={i} rows={2} />)}</div>
      ) : d && (
        <div className="space-y-6">
          <p role="note" className={clsx("rounded-xl px-4 py-2.5 text-[13px]", demo ? "bg-[#fdf8ee] text-[#7a520b]" : "bg-ice text-deep")}>
            {d.basis.note} ({fmtNum(d.basis.demo_events)} demo · {fmtNum(d.basis.live_events)} live events in the last {d.window_days} days.)
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="Views" value={fmtNum(d.totals.view)} />
            <Stat label="Clicks" value={fmtNum(d.totals.click)} />
            <Stat label="Shares" value={fmtNum(d.totals.share)} />
            <Stat label="Engagement" value={pct(d.totals.engagement_rate)} sub="(clicks + shares) / views" />
            <Stat label="Completion" value={pct(d.totals.completion_rate)} sub="read to the end / views" />
          </div>
          {d.weeks.length > 1 && (
            <Card className="p-5">
              <SectionTitle title="Views per week" />
              <div className="h-[220px]" role="img" aria-label={`Views per week: ${d.weeks.map((m) => `week of ${m.week} ${m.view}`).join(", ")}`}>
                <ResponsiveContainer>
                  <LineChart data={d.weeks} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="#eaf3f7" vertical={false} />
                    <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#5b7489" }} tickFormatter={(v: string) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 11, fill: "#5b7489" }} width={44} />
                    <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #d5e6ee", fontSize: 12 }} formatter={(v) => [fmtNum(Number(v)), "Views"]} labelFormatter={(l) => `Week of ${l}`} />
                    <Line type="monotone" dataKey="view" stroke="#0f7fa1" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-5"><SectionTitle title="Campaign performance (views)" /><Bars rows={d.campaigns.map((c) => ({ label: c.name, value: c.view, note: pct(c.engagement_rate) }))} /></Card>
            <Card className="p-5"><SectionTitle title="Audience engagement (views)" /><Bars rows={d.audiences.map((a) => ({ label: a.label, value: a.view, note: pct(a.engagement_rate) }))} /></Card>
            <Card className="p-5"><SectionTitle title="Channels (views)" /><Bars rows={d.channels.map((c) => ({ label: c.label, value: c.view, note: c.live ? "live" : "simulated" }))} /></Card>
            <Card className="p-5"><SectionTitle title="Best-performing formats (views)" /><Bars rows={d.formats.map((f) => ({ label: FORMAT_LABEL[f.key] || f.key, value: f.view, note: pct(f.completion_rate) }))} /></Card>
            <Card className="p-5"><SectionTitle title="Popular topics (views)" /><Bars rows={d.popular_topics.map((t) => ({ label: t.topic, value: t.views }))} /></Card>
            <Card className="p-5">
              <SectionTitle title="Research-to-content conversion" />
              <div className="grid grid-cols-2 gap-4">
                <Stat label="Research with outreach" value={pct(d.conversion.rate)} sub={`${d.conversion.records_with_outreach} of ${d.conversion.research_records} records`} />
                <Stat label="Drafts published" value={pct(d.conversion.publish_rate)} sub={`${d.conversion.published} of ${d.conversion.drafts_generated}`} />
              </div>
              <p className="mt-3 text-[12px] text-steel">{d.conversion.note}</p>
            </Card>
          </div>
          <Card className="overflow-hidden">
            <div className="px-5 pt-5"><SectionTitle title="Content performance" /></div>
            <div className="scrollbar-thin overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-[13px]">
                <thead className="bg-snow text-[11px] uppercase tracking-wide text-steel">
                  <tr>{["Content", "Format", "Views", "Clicks", "Shares", "Engagement", "Completion"].map((h) => <th key={h} className="px-4 py-2 font-medium">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-frost">
                  {d.content.map((c) => (
                    <tr key={c.id}>
                      <td className="max-w-[280px] truncate px-4 py-2 text-night">{c.title}</td>
                      <td className="px-4 py-2 text-ink-soft">{FORMAT_LABEL[c.format] || c.format}</td>
                      <td className="px-4 py-2 font-mono">{fmtNum(c.view)}</td>
                      <td className="px-4 py-2 font-mono">{fmtNum(c.click)}</td>
                      <td className="px-4 py-2 font-mono">{fmtNum(c.share)}</td>
                      <td className="px-4 py-2 font-mono">{pct(c.engagement_rate)}</td>
                      <td className="px-4 py-2 font-mono">{pct(c.completion_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </Container>
  );
}
