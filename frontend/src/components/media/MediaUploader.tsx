"use client";

import clsx from "clsx";
import { Film, ImageUp, RefreshCw, Upload } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useToast } from "@/components/common/Toast";
import { Button, Card, Field, inputCls } from "@/components/common/ui";
import { api, ApiError, post } from "@/lib/api";
import { fmtBytes } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { MediaItem } from "@/lib/types";
import { ProcessingSteps, ProcessingStatusPill } from "./ProcessingSteps";

interface Options {
  regions: string[]; categories: string[]; image_formats: string[]; video_formats: string[];
  max_image_mb: number; max_video_mb: number; video_processing: string; speech_to_text: string | null;
  stations: { slug: string; name: string }[]; expeditions: { slug: string; name: string }[];
  researchers: { slug: string; name: string }[]; topics: { slug: string; name: string }[];
}
interface Status { processing_status: string; steps: MediaItem["processing_steps"]; error: string; media: MediaItem }

const IMG = /\.(jpe?g|png|webp|tiff?)$/i;
const VID = /\.(mp4|m4v|mov|webm)$/i;

/** Image / video ingestion with live pipeline status. Only the upload is blocking — processing runs in the background. */
export function MediaUploader({ onDone }: { onDone?: () => void }) {
  const toast = useToast();
  const opts = useApi<Options>("/api/media-options");
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState<File | null>(null);
  const [meta, setMeta] = useState({ title: "", description: "", category: "Other", region: "Antarctic", year: "", tags: "", credit: "",
    license: "CC BY 4.0", location: "", station: "", expedition: "", researcher: "", topics: "", visibility: "public" });
  const [phase, setPhase] = useState<"idle" | "uploading" | "processing" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<Status | null>(null);
  const [err, setErr] = useState("");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const kind = file ? (IMG.test(file.name) ? "image" : VID.test(file.name) ? "video" : null) : null;
  const o = opts.data;

  const poll = (slug: string) => {
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(async () => {
      try {
        const st = await api<Status>(`/api/media/${slug}/processing`);
        setStatus(st);
        if (st.processing_status === "ready" || st.processing_status === "failed") {
          if (timer.current) clearInterval(timer.current);
          setPhase("done");
          onDone?.();
          if (st.processing_status === "ready") toast("success", "Media indexed", "It is now searchable in the repository.");
        }
      } catch {
        /* transient — keep polling */
      }
    }, 800);
  };

  const start = () => {
    if (!file || !o) return;
    setErr("");
    if (!kind) return setErr(`Unsupported file. Images: ${o.image_formats.join(", ")}. Videos: ${o.video_formats.join(", ")}.`);
    const limit = (kind === "image" ? o.max_image_mb : o.max_video_mb) * 1024 * 1024;
    if (file.size > limit) return setErr(`The file exceeds the ${kind === "image" ? o.max_image_mb : o.max_video_mb} MB limit for ${kind}s.`);
    const fd = new FormData();
    fd.append("file", file);
    if (transcript && kind === "video") fd.append("transcript", transcript);
    Object.entries(meta).forEach(([k, v]) => fd.append(k, v));
    setPhase("uploading");
    setProgress(0);
    setStatus(null);
    // XHR (not fetch) so the user sees real upload progress for large videos
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${(process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "")}/api/media/upload`);
    try {
      const token = window.localStorage.getItem("polarnexus.token");
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    } catch {
      /* storage unavailable */
    }
    xhr.upload.onprogress = (e) => e.lengthComputable && setProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onerror = () => { setPhase("idle"); setErr("Upload failed — check your connection and retry."); };
    xhr.onload = () => {
      let body: { detail?: string; slug?: string } = {};
      try { body = JSON.parse(xhr.responseText || "{}"); } catch { /* non-JSON */ }
      if (xhr.status >= 200 && xhr.status < 300 && body.slug) {
        setPhase("processing");
        poll(body.slug);
      } else {
        setPhase("idle");
        setErr(body.detail || (xhr.status === 413 ? "The file is too large." : `Upload failed (${xhr.status}).`));
      }
    };
    xhr.send(fd);
  };

  const retry = async () => {
    if (!status) return;
    try {
      await post(`/api/media/${status.media.slug}/reprocess`);
      setPhase("processing");
      poll(status.media.slug);
    } catch (e) {
      toast("error", "Could not retry", (e as ApiError).message);
    }
  };

  const set = (k: keyof typeof meta) => (e: { target: { value: string } }) => setMeta({ ...meta, [k]: e.target.value });

  return (
    <Card className="p-5 md:p-6">
      <h2 className="text-xl text-night">Upload an image or video</h2>
      <p className="mt-1 text-[13.5px] text-ink-soft">
        Images ({o?.image_formats.join(", ") || "JPG, PNG, WEBP, TIFF"}, up to {o?.max_image_mb ?? 20} MB) and videos ({o?.video_formats.join(", ") || "MP4, MOV, WEBM"}, up to {o?.max_video_mb ?? 200} MB).
        Files are validated, stored, described from their metadata, thumbnailed and indexed for search.
      </p>
      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <div>
          <label className={clsx("flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-8 text-center transition hover:border-glacier", file ? "border-cyan bg-[#f0f9fc]" : "border-frost")}>
            {kind === "video" ? <Film className="mb-2 h-8 w-8 text-cyan-deep" /> : <ImageUp className="mb-2 h-8 w-8 text-cyan-deep" />}
            <span className="max-w-full truncate text-[14px] font-medium text-night">{file ? file.name : "Choose an image or video"}</span>
            <span className="mt-1 text-[12px] text-steel">{file ? `${kind || "unsupported"} · ${fmtBytes(file.size)}` : "Click to browse"}</span>
            <input type="file" accept="image/jpeg,image/png,image/webp,image/tiff,video/mp4,video/quicktime,video/webm,.mov,.m4v" className="sr-only"
              onChange={(e) => { setFile(e.target.files?.[0] || null); setPhase("idle"); setStatus(null); }} aria-label="Media file" />
          </label>
          {kind === "video" && (
            <div className="mt-3 rounded-xl bg-snow p-3 text-[12.5px] text-ink-soft">
              <Field label="Transcript (optional — .vtt, .srt or .txt)" hint={o?.speech_to_text ? `Without a file, speech-to-text (${o.speech_to_text}) is used.` : "No speech-to-text service is configured, so speech becomes searchable only if you attach a transcript."}>
                <input type="file" accept=".vtt,.srt,.txt,text/vtt,text/plain" onChange={(e) => setTranscript(e.target.files?.[0] || null)} className="block w-full text-[12.5px]" />
              </Field>
              {o?.video_processing !== "ffmpeg" && <p className="mt-2 text-[12px] text-[#8a5c0c]">ffmpeg is not installed on this server: thumbnails and duration will be skipped (shown as such).</p>}
            </div>
          )}
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Field label="Title"><input className={inputCls} value={meta.title} onChange={set("title")} placeholder="From file name if empty" /></Field>
            <Field label="Category">
              <select className={inputCls} value={meta.category} onChange={set("category")}>{(o?.categories || ["Other"]).map((c) => <option key={c}>{c}</option>)}</select>
            </Field>
            <div className="sm:col-span-2"><Field label="Description (recommended — it is indexed)"><textarea className={inputCls} rows={2} value={meta.description} onChange={set("description")} /></Field></div>
            <Field label="Region">
              <select className={inputCls} value={meta.region} onChange={set("region")}>{(o?.regions || ["Antarctic"]).map((c) => <option key={c}>{c}</option>)}</select>
            </Field>
            <Field label="Year"><input className={inputCls} inputMode="numeric" value={meta.year} onChange={(e) => setMeta({ ...meta, year: e.target.value.replace(/\D/g, "").slice(0, 4) })} placeholder="From EXIF / today" /></Field>
            <Field label="Station">
              <select className={inputCls} value={meta.station} onChange={set("station")}><option value="">None</option>{o?.stations.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}</select>
            </Field>
            <Field label="Expedition">
              <select className={inputCls} value={meta.expedition} onChange={set("expedition")}><option value="">None</option>{o?.expeditions.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}</select>
            </Field>
            <Field label="Researcher">
              <select className={inputCls} value={meta.researcher} onChange={set("researcher")}><option value="">None</option>{o?.researchers.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}</select>
            </Field>
            <Field label="Topic">
              <select className={inputCls} value={meta.topics} onChange={set("topics")}><option value="">None</option>{o?.topics.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}</select>
            </Field>
            <Field label="Tags"><input className={inputCls} value={meta.tags} onChange={set("tags")} placeholder="Comma separated" /></Field>
            <Field label="Licence"><input className={inputCls} value={meta.license} onChange={set("license")} /></Field>
            <Field label="Credit / source"><input className={inputCls} value={meta.credit} onChange={set("credit")} placeholder="Defaults to your name" /></Field>
            <Field label="Visibility">
              <select className={inputCls} value={meta.visibility} onChange={set("visibility")}><option value="public">Public</option><option value="internal">Internal</option></select>
            </Field>
          </div>
          {err && <p role="alert" className="mt-3 rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
          <Button className="mt-4 w-full" size="lg" disabled={!file || phase === "uploading" || phase === "processing"} loading={phase === "uploading"}
            onClick={start} icon={<Upload className="h-4 w-4" />}>Upload & process</Button>
        </div>
        <div className="rounded-2xl bg-snow p-5" aria-live="polite">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-steel">Media pipeline</p>
          {phase === "uploading" && (
            <div>
              <ProcessingStatusPill status="uploading" />
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-frost" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress">
                <div className="h-full rounded-full bg-cyan transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-1 font-mono text-[11px] text-steel">{progress}%</p>
            </div>
          )}
          {status ? (
            <>
              <ProcessingSteps status={status.processing_status} steps={status.steps || []} error={status.error} />
              {status.processing_status === "ready" && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link href={`/media/${status.media.slug}`} className="rounded-lg bg-cyan-deep px-3.5 py-2 text-[13px] font-medium text-white">Open media record</Link>
                  <Link href={`/explore?q=${encodeURIComponent(status.media.title)}`} className="rounded-lg border border-frost bg-white px-3.5 py-2 text-[13px] text-night">Find it in search</Link>
                </div>
              )}
              {status.processing_status === "failed" && (
                <Button className="mt-3" size="sm" variant="secondary" onClick={retry} icon={<RefreshCw className="h-3.5 w-3.5" />}>Retry processing</Button>
              )}
            </>
          ) : phase !== "uploading" && (
            <ol className="space-y-1.5 text-[13px] text-steel">
              {(kind === "video"
                ? ["Upload", "Validate file", "Store", "Generate thumbnail", "Extract metadata", "Extract audio", "Speech-to-text / transcript", "Index transcript", "Generate searchable metadata", "Associate with entities", "Repository"]
                : ["Upload", "Validate file", "Store", "Extract metadata", "Generate thumbnail", "Extract EXIF", "Generate searchable metadata", "Associate with entities", "Index", "Repository"]
              ).map((s, i) => <li key={s} className="flex gap-3"><span className="flex h-5 w-5 items-center justify-center rounded-full bg-ice text-[10.5px]">{i + 1}</span>{s}</li>)}
            </ol>
          )}
        </div>
      </div>
    </Card>
  );
}
