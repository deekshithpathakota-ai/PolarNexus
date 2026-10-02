"use client";

import clsx from "clsx";
import { CircleCheck, CircleX, FileSpreadsheet, LoaderCircle, Table2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Button, Card, Field, inputCls } from "@/components/common/ui";
import { useToast } from "@/components/common/Toast";
import { api, ApiError, post } from "@/lib/api";
import { fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { DatasetUploadState } from "@/lib/types";
import { DuplicateNotice } from "./DuplicateNotice";
import { IssueList } from "./DatasetQuality";

const FLOW = ["Upload", "Validate", "Detect format", "Detect schema", "Infer column types", "Preview", "Validation", "Metadata", "Confirm", "Register", "Index", "Visualise"];

interface Opts { formats: string[]; planned_formats: string[]; max_mb: number; max_rows: number; regions: string[]; topics: { slug: string; name: string }[] }

export function DatasetUploader() {
  const toast = useToast();
  const opts = useApi<Opts>("/api/datasets/ingest/options");
  const [file, setFile] = useState<File | null>(null);
  const [up, setUp] = useState<DatasetUploadState | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [meta, setMeta] = useState({ title: "", description: "", region: "Antarctic", license: "", source: "", source_url: "", doi: "", creator: "", keywords: "", topics: [] as string[], visibility: "public" });
  const [units, setUnits] = useState<Record<string, string>>({});
  const [dropDup, setDropDup] = useState(false);
  const [ack, setAck] = useState(false);
  const [dupOk, setDupOk] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const a = up?.analysis;
  const analyse = async () => {
    if (!file) return;
    setErr("");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await post<DatasetUploadState>("/api/datasets/ingest/analyze", fd, {});
      setUp(r);
      setDupOk(!r.analysis?.duplicates?.length);
      setMeta((m) => ({ ...m, title: r.analysis?.suggested_title || m.title, region: r.analysis?.spatial.suggested_region || m.region }));
    } catch (e) {
      setErr((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!up) return;
    setErr("");
    setBusy(true);
    try {
      const r = await post<DatasetUploadState>(`/api/datasets/ingest/${up.token}/confirm`, {
        ...meta, keywords: meta.keywords.split(",").map((k) => k.trim()).filter(Boolean), units, drop_duplicates: dropDup, acknowledge_errors: ack,
      });
      setUp(r);
      timer.current = setInterval(async () => {
        try {
          const cur = await api<DatasetUploadState>(`/api/datasets/ingest/${up.token}`);
          setUp(cur);
          if (cur.status !== "registering") {
            if (timer.current) clearInterval(timer.current);
            setBusy(false);
            if (cur.status === "registered") toast("success", "Dataset registered", "It is indexed, searchable and ready to explore.");
          }
        } catch {
          /* keep polling */
        }
      }, 700);
    } catch (e) {
      setErr((e as ApiError).message);
      setBusy(false);
    }
  };

  const reset = () => { setUp(null); setFile(null); setErr(""); setAck(false); setUnits({}); };

  return (
    <Card className="p-5 md:p-6">
      <h2 className="flex items-center gap-2 text-xl text-night"><FileSpreadsheet className="h-5 w-5 text-cyan-deep" aria-hidden /> Ingest a scientific dataset</h2>
      <p className="mt-1 text-[13.5px] text-ink-soft">
        {opts.data ? `${opts.data.formats.join(", ")} up to ${opts.data.max_mb} MB / ${fmtNum(opts.data.max_rows)} rows.` : "CSV, TSV, JSON or GeoJSON."} Nothing is registered until you review the preview and confirm. NetCDF support is planned.
      </p>
      <ol className="mt-3 flex flex-wrap gap-1 text-[11px] text-steel" aria-label="Pipeline">
        {FLOW.map((s, i) => <li key={s} className="rounded-full bg-snow px-2 py-0.5 ring-1 ring-frost">{i + 1}. {s}</li>)}
      </ol>

      {!up && (
        <div className="mt-5">
          <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-frost px-4 py-8 text-center hover:border-glacier">
            <Table2 className="mb-2 h-8 w-8 text-cyan-deep" aria-hidden />
            <span className="text-[14px] font-medium text-night">{file ? file.name : "Choose a CSV or JSON file"}</span>
            <span className="mt-1 text-[12px] text-steel">{file ? `${(file.size / 1024).toFixed(0)} KB` : "Lat/lon, dates and numeric columns are detected automatically"}</span>
            <input type="file" accept=".csv,.tsv,.json,.geojson,text/csv,application/json" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>
          {err && <p role="alert" className="mt-3 rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
          <Button className="mt-4 w-full" size="lg" disabled={!file} loading={busy} onClick={analyse}>Analyse file</Button>
        </div>
      )}

      {up && a && up.status === "analyzed" && (
        <div className="mt-5 space-y-5">
          <div className="grid gap-3 sm:grid-cols-4">
            {[["Format", a.format], ["Rows", fmtNum(a.rows)], ["Columns", String(a.columns)], ["Verdict", a.summary.verdict.toUpperCase()]].map(([k, v]) => (
              <div key={k} className="rounded-xl bg-snow p-3"><p className="font-mono text-[10.5px] uppercase tracking-wider text-steel">{k}</p>
                <p className={clsx("font-display text-[20px]", k === "Verdict" && (a.summary.verdict === "pass" ? "text-teal" : a.summary.verdict === "warn" ? "text-[#8a5c0c]" : "text-coral"))}>{v}</p></div>
            ))}
          </div>
          {a.duplicates.length > 0 && !dupOk && (
            <DuplicateNotice uploaded={up.filename} candidates={a.duplicates} onKeepBoth={() => setDupOk(true)} onCancel={async () => { await post(`/api/datasets/ingest/${up.token}/cancel`); reset(); }} />
          )}
          <section aria-labelledby="schema-h">
            <h3 id="schema-h" className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">Detected schema</h3>
            <div className="scrollbar-thin overflow-x-auto rounded-xl ring-1 ring-frost">
              <table className="w-full min-w-[640px] text-left text-[13px]">
                <thead className="bg-snow text-[11px] uppercase tracking-wide text-steel">
                  <tr><th className="px-3 py-2 font-medium">Column</th><th className="px-3 font-medium">Type</th><th className="px-3 font-medium">Role</th><th className="px-3 font-medium">Missing</th><th className="px-3 font-medium">Range / examples</th><th className="px-3 font-medium">Unit</th></tr>
                </thead>
                <tbody className="divide-y divide-frost">
                  {a.schema.map((c) => (
                    <tr key={c.name}>
                      <td className="px-3 py-1.5 font-mono text-[12px] text-night">{c.name}</td>
                      <td className="px-3">{c.type}</td>
                      <td className="px-3 text-steel">{c.role || "—"}</td>
                      <td className="px-3 font-mono text-[12px]">{c.missing ? `${c.missing} (${c.missing_pct}%)` : "0"}</td>
                      <td className="max-w-[200px] truncate px-3 font-mono text-[11.5px] text-steel">{c.stats && "min" in c.stats ? `${c.stats.min} … ${c.stats.max}` : c.examples.join(", ")}</td>
                      <td className="px-3">
                        {(c.type === "number" || c.type === "integer") && !c.role ? (
                          <input aria-label={`Unit for ${c.name}`} className={clsx(inputCls, "h-8 w-28 text-[12.5px]")} placeholder="e.g. °C" value={units[c.name] || ""} onChange={(e) => setUnits({ ...units, [c.name]: e.target.value })} />
                        ) : <span className="text-mist">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-1.5 text-[12px] text-steel">Units are never guessed — leave blank if the file does not state them. Charts offered: {a.suggested_charts.join(", ") || "table only (no numeric/time/coordinate columns)"}.</p>
          </section>
          <section aria-labelledby="val-h">
            <h3 id="val-h" className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">Validation</h3>
            <IssueList issues={a.issues} />
          </section>
          <section aria-labelledby="prev-h">
            <h3 id="prev-h" className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">Preview (first {Math.min(10, a.preview.length)} rows)</h3>
            <div className="scrollbar-thin overflow-x-auto rounded-xl ring-1 ring-frost">
              <table className="w-full text-left font-mono text-[11.5px]">
                <thead className="bg-snow text-steel"><tr>{a.schema.map((c) => <th key={c.name} className="whitespace-nowrap px-2 py-1.5 font-medium">{c.name}</th>)}</tr></thead>
                <tbody className="divide-y divide-frost">
                  {a.preview.slice(0, 10).map((r, i) => <tr key={i}>{a.schema.map((c) => <td key={c.name} className="whitespace-nowrap px-2 py-1 text-ink-soft">{r[c.name]}</td>)}</tr>)}
                </tbody>
              </table>
            </div>
          </section>
          <section aria-labelledby="meta-h" className="grid gap-3 sm:grid-cols-2">
            <h3 id="meta-h" className="font-mono text-[11px] uppercase tracking-wider text-steel sm:col-span-2">Scientific metadata</h3>
            <Field label="Title"><input className={inputCls} value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} /></Field>
            <Field label="Region">
              <select className={inputCls} value={meta.region} onChange={(e) => setMeta({ ...meta, region: e.target.value })}>
                {(opts.data?.regions || ["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India", "Global"]).map((r) => <option key={r}>{r}</option>)}
              </select>
            </Field>
            <div className="sm:col-span-2"><Field label="Description"><textarea className={`${inputCls} h-20 py-2`} value={meta.description} onChange={(e) => setMeta({ ...meta, description: e.target.value })} /></Field></div>
            <Field label="Creator"><input className={inputCls} value={meta.creator} onChange={(e) => setMeta({ ...meta, creator: e.target.value })} placeholder="Person or institution" /></Field>
            <Field label="Licence"><input className={inputCls} value={meta.license} onChange={(e) => setMeta({ ...meta, license: e.target.value })} placeholder="e.g. CC BY 4.0" /></Field>
            <Field label="Source"><input className={inputCls} value={meta.source} onChange={(e) => setMeta({ ...meta, source: e.target.value })} /></Field>
            <Field label="Original URL"><input className={inputCls} value={meta.source_url} onChange={(e) => setMeta({ ...meta, source_url: e.target.value })} placeholder="https://…" /></Field>
            <Field label="DOI (if any)"><input className={inputCls} value={meta.doi} onChange={(e) => setMeta({ ...meta, doi: e.target.value })} placeholder="10.xxxx/…" /></Field>
            <Field label="Keywords"><input className={inputCls} value={meta.keywords} onChange={(e) => setMeta({ ...meta, keywords: e.target.value })} placeholder="Comma separated" /></Field>
            <fieldset className="sm:col-span-2"><legend className="mb-1 text-[13px] font-medium text-night">Topics</legend>
              <div className="flex max-h-24 flex-wrap gap-1.5 overflow-auto">
                {(opts.data?.topics || []).map((t) => (
                  <label key={t.slug} className="inline-flex items-center gap-1 rounded-full bg-snow px-2.5 py-0.5 text-[12.5px] ring-1 ring-frost">
                    <input type="checkbox" checked={meta.topics.includes(t.slug)} onChange={() => setMeta({ ...meta, topics: meta.topics.includes(t.slug) ? meta.topics.filter((x) => x !== t.slug) : [...meta.topics, t.slug] })} />{t.name}
                  </label>
                ))}
              </div>
            </fieldset>
          </section>
          <div className="space-y-2 text-[13px]">
            {a.issues.some((i) => i.code === "duplicate_rows") && <label className="flex items-center gap-2"><input type="checkbox" checked={dropDup} onChange={(e) => setDropDup(e.target.checked)} /> Remove duplicate rows when registering</label>}
            {a.summary.errors > 0 && <label className="flex items-center gap-2 text-coral"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> I have reviewed the validation errors and want to register the dataset anyway (invalid values are kept as text / unmapped).</label>}
          </div>
          {err && <p role="alert" className="rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
          <div className="flex flex-wrap gap-2">
            <Button size="lg" onClick={confirm} loading={busy} disabled={!dupOk || meta.title.trim().length < 3 || (a.summary.errors > 0 && !ack)}>Confirm & register dataset</Button>
            <Button size="lg" variant="ghost" onClick={async () => { await post(`/api/datasets/ingest/${up.token}/cancel`).catch(() => {}); reset(); }}>Cancel</Button>
          </div>
        </div>
      )}

      {up && up.status !== "analyzed" && (
        <div className="mt-5 rounded-2xl bg-snow p-5">
          <ol className="space-y-2">
            {up.steps.map((s) => (
              <li key={s.key} className="flex items-start gap-3">
                <span className={clsx("mt-0.5 flex h-6 w-6 items-center justify-center rounded-full", s.status === "done" ? "bg-[#e2f4f1] text-teal" : s.status === "running" ? "bg-[#e3f4fa] text-cyan-deep" : s.status === "failed" ? "bg-[#fbe9e5] text-coral" : "bg-ice text-mist")}>
                  {s.status === "done" ? <CircleCheck className="h-4 w-4" /> : s.status === "running" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : s.status === "failed" ? <CircleX className="h-4 w-4" /> : "·"}
                </span>
                <span><span className="block text-[13.5px] text-night">{s.label}</span>{s.detail && <span className="block font-mono text-[11.5px] text-steel">{s.detail}</span>}</span>
              </li>
            ))}
          </ol>
          {up.status === "failed" && <p className="mt-3 rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{up.error} <button className="underline" onClick={reset}>Try again</button></p>}
          {up.status === "cancelled" && <p className="mt-3 text-[13px] text-steel">Upload cancelled. <button className="text-cyan-deep underline" onClick={reset}>Start again</button></p>}
          {up.status === "registered" && up.dataset && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href={up.dataset.url} className="rounded-lg bg-cyan-deep px-3.5 py-2 text-[13px] font-medium text-white">Explore dataset</Link>
              <button onClick={reset} className="rounded-lg border border-frost bg-white px-3.5 py-2 text-[13px] text-night">Ingest another</button>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
