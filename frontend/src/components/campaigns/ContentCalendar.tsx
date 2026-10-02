"use client";

import clsx from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo } from "react";
import type { CampaignItemT } from "@/lib/types";

export const ITEM_STATUS_STYLE: Record<string, string> = {
  planned: "border-frost bg-snow text-ink-soft",
  scheduled: "border-[#c2e6f2] bg-[#e3f4fa] text-cyan-deep",
  published: "border-[#bfe5df] bg-[#e2f4f1] text-teal",
  cancelled: "border-[#f2cfc6] bg-[#fdf6f4] text-coral line-through",
};

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Month grid on wide screens, an agenda list on small screens. Status is always written, never colour-only. */
export function ContentCalendar({ month, onMonth, items, onSelect }: {
  month: Date; onMonth: (d: Date) => void; items: CampaignItemT[]; onSelect?: (i: CampaignItemT) => void;
}) {
  const days = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [month]);
  const byDay = useMemo(() => {
    const m = new Map<string, CampaignItemT[]>();
    items.forEach((i) => {
      if (!i.scheduled_for) return;
      const k = i.scheduled_for.slice(0, 10);
      m.set(k, [...(m.get(k) || []), i]);
    });
    return m;
  }, [items]);
  const label = month.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  const today = iso(new Date());
  const inMonth = items.filter((i) => i.scheduled_for && i.scheduled_for.slice(0, 7) === iso(month).slice(0, 7))
    .sort((a, b) => (a.scheduled_for! < b.scheduled_for! ? -1 : 1));

  const Pill = ({ i }: { i: CampaignItemT }) => (
    <button type="button" onClick={() => onSelect?.(i)}
      className={clsx("block w-full truncate rounded-md border px-1.5 py-0.5 text-left text-[11.5px] leading-snug hover:ring-1 hover:ring-cyan", ITEM_STATUS_STYLE[i.status])}
      title={`${i.title} — ${i.status} · ${i.channel_label}`}>
      {i.title}
    </button>
  );

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <button className="rounded-lg p-1.5 text-steel hover:bg-ice" aria-label="Previous month" onClick={() => onMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}><ChevronLeft className="h-5 w-5" /></button>
        <h3 className="font-display text-[18px] text-night" aria-live="polite">{label}</h3>
        <button className="rounded-lg p-1.5 text-steel hover:bg-ice" aria-label="Next month" onClick={() => onMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}><ChevronRight className="h-5 w-5" /></button>
      </div>
      <div className="hidden md:block">
        <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-frost bg-frost" role="grid" aria-label={`Content calendar, ${label}`}>
          {WEEKDAYS.map((d) => <div key={d} role="columnheader" className="bg-snow py-1.5 text-center font-mono text-[10.5px] uppercase tracking-wider text-steel">{d}</div>)}
          {days.map((d) => {
            const k = iso(d);
            const list = byDay.get(k) || [];
            const other = d.getMonth() !== month.getMonth();
            return (
              <div key={k} role="gridcell" aria-label={`${d.toDateString()}: ${list.length} item(s)`} className={clsx("min-h-[92px] space-y-1 bg-white p-1.5", other && "bg-snow/70")}>
                <span className={clsx("inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 font-mono text-[11px]", k === today ? "bg-cyan-deep text-white" : other ? "text-mist" : "text-steel")}>{d.getDate()}</span>
                {list.slice(0, 3).map((i) => <Pill key={i.id} i={i} />)}
                {list.length > 3 && <span className="block text-[11px] text-steel">+{list.length - 3} more</span>}
              </div>
            );
          })}
        </div>
      </div>
      <ul className="space-y-2 md:hidden" aria-label={`Agenda, ${label}`}>
        {inMonth.length === 0 && <li className="rounded-xl bg-snow p-4 text-center text-[13px] text-steel">Nothing scheduled this month.</li>}
        {inMonth.map((i) => (
          <li key={i.id} className="flex items-start gap-3">
            <span className="w-14 shrink-0 pt-1 font-mono text-[12px] text-steel">{new Date(i.scheduled_for! + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
            <div className="min-w-0 flex-1"><Pill i={i} /><span className="mt-0.5 block text-[11.5px] text-steel">{i.status} · {i.channel_label}</span></div>
          </li>
        ))}
      </ul>
      <p className="mt-2 flex flex-wrap gap-3 text-[11.5px] text-steel">
        {Object.keys(ITEM_STATUS_STYLE).map((k) => <span key={k} className={clsx("rounded border px-1.5", ITEM_STATUS_STYLE[k])}>{k}</span>)}
      </p>
    </div>
  );
}
