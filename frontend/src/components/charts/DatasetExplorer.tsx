"use client";

import clsx from "clsx";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { Button, ErrorState, Pagination, Skeleton, Tabs, inputCls } from "@/components/common/ui";
import { useApi } from "@/lib/hooks";
import type { DatasetDetail, SeriesResponse } from "@/lib/types";

const PALETTE = ["#0f7fa1", "#128a87", "#c98a1b", "#7b6cd9", "#c4553f"];

function Chart({ slug, ds }: { slug: string; ds: DatasetDetail }) {
  const groupVar = ds.variables.find((v) => ["glacier", "lake", "station"].includes(v.name))?.name;
  const xVar = ds.data_type === "Profiles" ? "depth" : ds.variables.some((v) => v.name === "year") ? "year" : "observed_at";
  const [y, setY] = useState<string | null>(null);
  const [kind, setKind] = useState<"line" | "scatter" | "geo">(ds.data_type === "Profiles" || ds.data_type === "Point observations" ? "scatter" : "line");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const { data, error, loading, reload } = useApi<SeriesResponse>(`/api/datasets/${slug}/series`, {
    y: y || undefined, x: xVar, group: groupVar, date_from: from || undefined, date_to: to || undefined,
  });
  const groups = useMemo(() => {
    if (!data) return [];
    const g = new Map<string, SeriesResponse["points"]>();
    data.points.forEach((p) => {
      const k = p.group || "all";
      if (!g.has(k)) g.set(k, []);
      g.get(k)!.push(p);
    });
    return [...g.entries()];
  }, [data]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-[12px] text-steel">
          Variable
          <select value={y || data?.y || ""} onChange={(e) => setY(e.target.value)} className={clsx(inputCls, "mt-1 w-48")}>
            {(data?.numeric_variables || []).map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
          </select>
        </label>
        {xVar === "observed_at" && (
          <>
            <label className="text-[12px] text-steel">From<input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={clsx(inputCls, "mt-1 w-40")} /></label>
            <label className="text-[12px] text-steel">To<input type="date" value={to} onChange={(e) => setTo(e.target.value)} className={clsx(inputCls, "mt-1 w-40")} /></label>
            {(from || to) && <Button size="sm" variant="ghost" onClick={() => { setFrom(""); setTo(""); }}>Reset dates</Button>}
          </>
        )}
        <Tabs
          className="ml-auto"
          value={kind}
          onChange={setKind}
          tabs={[
            { key: "line", label: "Time series" },
            { key: "scatter", label: "Scatter" },
            { key: "geo", label: "Geographic" },
          ]}
        />
      </div>
      {error ? (
        <ErrorState error={error} onRetry={reload} compact />
      ) : loading || !data ? (
        <Skeleton className="h-[320px] w-full" />
      ) : data.points.length === 0 ? (
        <p className="rounded-xl bg-snow p-8 text-center text-sm text-steel">No records in this range.</p>
      ) : (
        <>
          <div className="h-[320px] w-full">
            <ResponsiveContainer>
              {kind === "geo" ? (
                <ScatterChart margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
                  <CartesianGrid stroke="#e3eef3" />
                  <XAxis type="number" dataKey="lon" name="Longitude" unit="°" domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#5b7489" }} />
                  <YAxis type="number" dataKey="lat" name="Latitude" unit="°" domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#5b7489" }} />
                  <ZAxis type="number" dataKey="y" range={[20, 120]} name={data.y} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                  <Scatter data={data.points} fill="#0f7fa1" fillOpacity={0.55} />
                </ScatterChart>
              ) : kind === "scatter" ? (
                <ScatterChart margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
                  <CartesianGrid stroke="#e3eef3" />
                  <XAxis dataKey="y" type="number" name={data.y} unit={data.unit ? ` ${data.unit}` : ""} domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#5b7489" }} />
                  <YAxis dataKey="x" type={xVar === "observed_at" ? "category" : "number"} reversed={xVar === "depth"} name={xVar} tick={{ fontSize: 11, fill: "#5b7489" }} width={70} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                  {groups.map(([g, pts], i) => <Scatter key={g} name={g} data={pts} fill={PALETTE[i % PALETTE.length]} fillOpacity={0.7} />)}
                </ScatterChart>
              ) : (
                <LineChart margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
                  <CartesianGrid stroke="#e3eef3" />
                  <XAxis dataKey="x" type="category" allowDuplicatedCategory={false} tick={{ fontSize: 11, fill: "#5b7489" }} minTickGap={40} />
                  <YAxis tick={{ fontSize: 11, fill: "#5b7489" }} width={54} domain={["auto", "auto"]} />
                  <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #d5e6ee", fontSize: 12 }} formatter={(v) => [`${v} ${data.unit}`, data.y]} />
                  {groups.map(([g, pts], i) => (
                    <Line key={g} data={pts} dataKey="y" name={g} stroke={PALETTE[i % PALETTE.length]} strokeWidth={1.8} dot={false} isAnimationActive={false} />
                  ))}
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 font-mono text-[12px] text-steel">
            <span>n = {data.stats.count}</span>
            <span>min {data.stats.min} {data.unit}</span>
            <span>mean {data.stats.mean} {data.unit}</span>
            <span>max {data.stats.max} {data.unit}</span>
            {groups.length > 1 && <span>{groups.map(([g], i) => <span key={g} className="mr-3" style={{ color: PALETTE[i % PALETTE.length] }}>● {g}</span>)}</span>}
          </div>
          <p className="mt-2 text-[12px] text-[#8a5c0c]">Synthetic demonstration values — the chart shows how the explorer works, not real observations. No scientific conclusions should be drawn from it.</p>
        </>
      )}
    </div>
  );
}

function Records({ slug, ds }: { slug: string; ds: DatasetDetail }) {
  const [page, setPage] = useState(1);
  const numeric = ds.variables.filter((v) => !["text", "name", "id", "ISO date", "ISO datetime"].includes(v.unit) && !["latitude", "longitude", "date", "timestamp"].includes(v.name));
  const [variable, setVariable] = useState("");
  const [min, setMin] = useState("");
  const [max, setMax] = useState("");
  const [applied, setApplied] = useState({ variable: "", min: "", max: "" });
  const { data, error, loading, reload } = useApi<{ total: number; page: number; pages: number; records: Record<string, string | number | null>[] }>(
    `/api/datasets/${slug}/records`,
    { page, page_size: 15, variable: applied.variable || undefined, min_value: applied.min || undefined, max_value: applied.max || undefined },
  );
  const cols = data?.records[0] ? Object.keys(data.records[0]).filter((k) => k !== "id") : [];
  return (
    <div>
      <form
        className="mb-4 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          setApplied({ variable, min, max });
        }}
      >
        <label className="text-[12px] text-steel">Filter variable
          <select value={variable} onChange={(e) => setVariable(e.target.value)} className={clsx(inputCls, "mt-1 w-48")}>
            <option value="">— none —</option>
            {numeric.map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
          </select>
        </label>
        <label className="text-[12px] text-steel">Min<input type="number" step="any" value={min} onChange={(e) => setMin(e.target.value)} className={clsx(inputCls, "mt-1 w-28")} /></label>
        <label className="text-[12px] text-steel">Max<input type="number" step="any" value={max} onChange={(e) => setMax(e.target.value)} className={clsx(inputCls, "mt-1 w-28")} /></label>
        <Button size="sm" type="submit" disabled={!variable}>Apply</Button>
        {applied.variable && <Button size="sm" variant="ghost" type="button" onClick={() => { setVariable(""); setMin(""); setMax(""); setApplied({ variable: "", min: "", max: "" }); }}>Clear</Button>}
        {data && <span className="ml-auto text-[12px] text-steel">{data.total.toLocaleString()} records match</span>}
      </form>
      {error ? <ErrorState error={error} onRetry={reload} compact /> : loading || !data ? <Skeleton className="h-64 w-full" /> : data.records.length === 0 ? (
        <p className="rounded-xl bg-snow p-8 text-center text-sm text-steel">No records match this filter.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-frost scrollbar-thin">
          <table className="w-full min-w-[600px] text-left text-[13px]">
            <thead className="bg-snow font-mono text-[11px] uppercase tracking-wide text-steel">
              <tr>{cols.map((c) => <th key={c} className="whitespace-nowrap px-3 py-2 font-medium">{c.replace(/_/g, " ")}</th>)}</tr>
            </thead>
            <tbody>
              {data.records.map((r, i) => (
                <tr key={String(r.id ?? i)} className="border-t border-frost/70 hover:bg-snow">
                  {cols.map((c) => <td key={c} className="whitespace-nowrap px-3 py-2 font-mono text-[12.5px] text-night">{c === "observed_at" && r[c] ? String(r[c]).slice(0, 10) : String(r[c] ?? "—")}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} onPage={setPage} />}
    </div>
  );
}

export function DatasetExplorer({ ds }: { ds: DatasetDetail }) {
  const [tab, setTab] = useState<"chart" | "records" | "variables">("chart");
  return (
    <div>
      <Tabs
        className="mb-4"
        value={tab}
        onChange={setTab}
        tabs={[
          { key: "chart", label: "Visualise" },
          { key: "records", label: "Preview records" },
          { key: "variables", label: `Variables · ${ds.variables.length}` },
        ]}
      />
      {tab === "chart" && <Chart slug={ds.slug} ds={ds} />}
      {tab === "records" && <Records slug={ds.slug} ds={ds} />}
      {tab === "variables" && (
        <div className="overflow-x-auto rounded-xl border border-frost">
          <table className="w-full min-w-[480px] text-left text-[13.5px]">
            <thead className="bg-snow font-mono text-[11px] uppercase tracking-wide text-steel">
              <tr><th className="px-4 py-2">Variable</th><th className="px-4 py-2">Unit</th><th className="px-4 py-2">Description</th></tr>
            </thead>
            <tbody>
              {ds.variables.map((v) => (
                <tr key={v.name} className="border-t border-frost/70">
                  <td className="px-4 py-2.5 font-mono text-[12.5px] text-night">{v.name}</td>
                  <td className="px-4 py-2.5 text-ink-soft">{v.unit}</td>
                  <td className="px-4 py-2.5 text-ink-soft">{v.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
