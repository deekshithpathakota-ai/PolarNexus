"use client";

import clsx from "clsx";
import { CircleCheck, CircleX, FileUp, LoaderCircle, SquarePen, Upload } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Badge, Button, Card, Field, PageHeader, Skeleton, StatusBadge, Tabs, inputCls } from "@/components/common/ui";
import { MediaUploader } from "@/components/media/MediaUploader";
import { ProcessingStatusPill } from "@/components/media/ProcessingSteps";
import { Container } from "@/components/layout/AppShell";
import { api, ApiError, post } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { ContentItem, DuplicateCandidate, MediaItem } from "@/lib/types";
import { DuplicateNotice } from "@/components/datasets/DuplicateNotice";
import { DatasetUploader } from "@/components/datasets/DatasetUploader";

interface Step { key: string; label: string; status: "pending" | "running" | "done" | "failed" | "skipped"; detail: string }
interface Job { id: number; file_name: string; status: string; steps: Step[]; error: string; document?: { slug: string; title: string; status: string } | null; created_at: string }

function Pipeline({ job }: { job: Job }) {
  return (
    <ol className="space-y-2">
      {job.steps.map((s, i) => (
        <li key={s.key} className="flex items-start gap-3">
          <span className={clsx("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
            s.status === "done" ? "bg-[#e2f4f1] text-teal" : s.status === "running" ? "bg-[#e3f4fa] text-cyan-deep" : s.status === "failed" ? "bg-[#fbe9e5] text-coral" : "bg-ice text-mist")}>
            {s.status === "done" ? <CircleCheck className="h-4 w-4" /> : s.status === "running" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : s.status === "failed" ? <CircleX className="h-4 w-4" /> : i + 1}
          </span>
          <span className="min-w-0">
            <span className={clsx("block text-[13.5px]", s.status === "pending" || s.status === "skipped" ? "text-mist" : "text-night")}>{s.label}</span>
            {s.detail && <span className="block font-mono text-[11.5px] text-steel">{s.detail}</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Uploader({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [meta, setMeta] = useState({ title: "", doc_type: "Technical Report", region: "", year: "", authors: "", visibility: "public" });
  const [job, setJob] = useState<Job | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const [dups, setDups] = useState<DuplicateCandidate[] | null>(null);

  const check = async () => {
    if (!file) return;
    setErr("");
    if (file.size > 25 * 1024 * 1024) return setErr("The file exceeds the 25 MB limit.");
    if (!/\.(pdf|txt|md)$/i.test(file.name)) return setErr("Only PDF, TXT or MD documents can be ingested here.");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("title", meta.title);
      const r = await post<{ duplicates: DuplicateCandidate[] }>("/api/ingestion/check-duplicates", fd, {});
      if (r.duplicates.length) {
        setDups(r.duplicates);
        setBusy(false);
        return;
      }
    } catch (e) {
      setErr((e as ApiError).message);
      setBusy(false);
      return;
    }
    await start();
  };

  const start = async (updateSlug?: string) => {
    if (!file) return;
    setErr("");
    setDups(null);
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    Object.entries(meta).forEach(([k, v]) => fd.append(k, v));
    if (updateSlug) fd.append("update_existing", updateSlug);
    try {
      const j = await post<Job>("/api/ingestion/upload", fd, {});
      setJob(j);
      timer.current = setInterval(async () => {
        try {
          const cur = await api<Job>(`/api/ingestion/jobs/${j.id}`);
          setJob(cur);
          if (cur.status !== "processing") {
            if (timer.current) clearInterval(timer.current);
            setBusy(false);
            onDone();
            if (cur.status === "completed") toast("success", "Document indexed", "It is now searchable and available to the AI assistant.");
          }
        } catch {
          /* transient; keep polling */
        }
      }, 700);
    } catch (e) {
      setErr((e as ApiError).message);
      setBusy(false);
    }
  };

  return (
    <Card className="p-5 md:p-6">
      <h2 className="text-xl text-night">Upload a document</h2>
      <p className="mt-1 text-[13.5px] text-ink-soft">PDF, TXT or Markdown up to 25 MB. The file is validated, text is extracted, metadata inferred, then chunked, embedded and indexed.</p>
      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <div>
          <label
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }}
            className={clsx("flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-10 text-center transition", drag ? "border-cyan bg-[#f0f9fc]" : "border-frost hover:border-glacier")}
          >
            <FileUp className="mb-2 h-8 w-8 text-cyan-deep" />
            <span className="text-[14px] font-medium text-night">{file ? file.name : "Drop a file or click to browse"}</span>
            <span className="mt-1 text-[12px] text-steel">{file ? `${(file.size / 1024).toFixed(0)} KB` : "PDF · TXT · MD"}</span>
            <input type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <Field label="Title (optional)"><input className={inputCls} value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} placeholder="Inferred if empty" /></Field>
            <Field label="Type">
              <select className={inputCls} value={meta.doc_type} onChange={(e) => setMeta({ ...meta, doc_type: e.target.value })}>
                {["Research Paper", "Technical Report", "Expedition Report", "Educational Resource", "News / Outreach"].map((t) => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Region">
              <select className={inputCls} value={meta.region} onChange={(e) => setMeta({ ...meta, region: e.target.value })}>
                <option value="">Infer from text</option>
                {["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"].map((t) => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Year"><input className={inputCls} inputMode="numeric" value={meta.year} onChange={(e) => setMeta({ ...meta, year: e.target.value.replace(/\D/g, "").slice(0, 4) })} placeholder="Infer" /></Field>
            <Field label="Authors"><input className={inputCls} value={meta.authors} onChange={(e) => setMeta({ ...meta, authors: e.target.value })} placeholder="Comma separated" /></Field>
            <Field label="Visibility">
              <select className={inputCls} value={meta.visibility} onChange={(e) => setMeta({ ...meta, visibility: e.target.value })}>
                <option value="public">Public</option><option value="internal">Internal</option>
              </select>
            </Field>
          </div>
          {err && <p role="alert" className="mt-3 rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
          {dups && file ? (
            <div className="mt-4">
              <DuplicateNotice uploaded={file.name} candidates={dups} busy={busy} onKeepBoth={() => start()} onUpdate={(slug) => start(slug)} onCancel={() => setDups(null)} />
            </div>
          ) : (
            <Button className="mt-4 w-full" size="lg" disabled={!file} loading={busy} onClick={check} icon={<Upload className="h-4 w-4" />}>Upload & index</Button>
          )}
          <p className="mt-2 text-[11.5px] text-steel">Scanned PDFs are read with OCR when it is available on the server; page numbers are kept for citations.</p>
        </div>
        <div className="rounded-2xl bg-snow p-5">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Ingestion pipeline</p>
          {job ? (
            <>
              <Pipeline job={job} />
              {job.status === "failed" && <p className="mt-3 rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{job.error}</p>}
              {job.status === "completed" && job.document && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link href={`/resources/${job.document.slug}`} className="rounded-lg bg-cyan-deep px-3.5 py-2 text-[13px] font-medium text-white">Open document</Link>
                  <Link href={`/resources/${job.document.slug}?tab=ask`} className="rounded-lg border border-frost bg-white px-3.5 py-2 text-[13px] text-night">Ask AI about it</Link>
                </div>
              )}
            </>
          ) : (
            <ol className="space-y-2 text-[13px] text-steel">
              {["Upload document", "Validate file (type, signature, size, name)", "Extract text (PyMuPDF)", "OCR scanned pages (tesseract)", "Extract metadata", "Create document chunks", "Generate embeddings", "Store vectors", "Index document", "Mark repository status"].map((s, i) => (
                <li key={s} className="flex gap-3"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-ice text-[11px]">{i + 1}</span>{s}</li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </Card>
  );
}

function Workspace() {
  const [tick, setTick] = useState(0);
  const [mode, setMode] = useState<"document" | "media" | "dataset">("document");
  const jobs = useApi<{ results: Job[] }>("/api/ingestion/jobs", undefined, [tick]);
  const media = useApi<{ results: MediaItem[] }>("/api/my/media-uploads", undefined, [tick]);
  const content = useApi<{ results: ContentItem[] }>("/api/content", { mine: true });
  return (
    <Container>
      <PageHeader eyebrow="Researcher" title="Researcher Workspace" description="Upload resources into the repository, follow their processing, and turn your research into outreach drafts."
        actions={<Link href="/studio" className="inline-flex h-10 items-center gap-2 rounded-lg bg-night px-4 text-sm font-medium text-white hover:bg-deep"><SquarePen className="h-4 w-4" /> Content Studio</Link>} />
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0">
          <Tabs className="mb-4 w-fit max-w-full" value={mode} onChange={setMode}
            tabs={[{ key: "document", label: "Document" }, { key: "dataset", label: "Dataset (CSV · JSON)" }, { key: "media", label: "Image / Video" }]} />
          {mode === "document" ? <Uploader onDone={() => setTick((t) => t + 1)} /> : mode === "dataset" ? <DatasetUploader /> : <MediaUploader onDone={() => setTick((t) => t + 1)} />}
        </div>
        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Media uploads</h2>
            {!media.data?.results.length ? <p className="text-[13px] text-steel">No media uploaded yet.</p> : (
              <ul className="space-y-2">
                {media.data.results.slice(0, 8).map((m) => (
                  <li key={m.id} className="flex items-center justify-between gap-2 text-[13px]">
                    <Link href={`/media/${m.slug}`} className="min-w-0 truncate text-night hover:text-cyan-deep">{m.title}</Link>
                    <ProcessingStatusPill status={m.processing_status || "ready"} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-5">
            <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Recent uploads</h2>
            {jobs.loading && !jobs.data ? <Skeleton className="h-24" /> : !jobs.data?.results.length ? <p className="text-[13px] text-steel">No uploads yet.</p> : (
              <ul className="space-y-2">
                {jobs.data.results.slice(0, 8).map((j) => (
                  <li key={j.id} className="flex items-center justify-between gap-2 text-[13px]">
                    <span className="min-w-0 truncate text-night">{j.file_name}</span>
                    <Badge tone={j.status === "completed" ? "teal" : j.status === "failed" ? "coral" : "cyan"}>{j.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-5">
            <h2 className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">My outreach drafts</h2>
            {!content.data?.results.length ? <p className="text-[13px] text-steel">No drafts yet.</p> : (
              <ul className="space-y-2">
                {content.data.results.slice(0, 8).map((c) => (
                  <li key={c.id}>
                    <Link href={`/studio?id=${c.id}`} className="block rounded-lg p-1.5 hover:bg-snow">
                      <span className="line-clamp-1 text-[13px] text-night">{c.title}</span>
                      <span className="mt-0.5 flex items-center gap-2"><StatusBadge status={c.status} /><span className="text-[11px] text-mist">{timeAgo(c.updated_at)}</span></span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="upload" title="Researcher Workspace"><Workspace /></RequireAuth>;
}
