"use client";

import clsx from "clsx";
import {
  ArrowRight,
  BookOpen,
  ClipboardCheck,
  FileText,
  Languages,
  Mail,
  Ship,
  ShieldCheck,
  Star,
  Eye,
  GraduationCap,
  Megaphone,
  Newspaper,
  PenLine,
  Plus,
  Save,
  Send,
  Sparkles,
  Trash2,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { CitationList, EvidenceCheckView, History } from "@/components/content/EvidencePanel";
import { Markdown } from "@/components/common/Markdown";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DemoBadge,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  StatusBadge,
  Tabs,
  inputCls,
} from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { ApiError, api, del, post, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AUDIENCE_LABEL, FORMAT_LABEL, genModeLabel, timeAgo } from "@/lib/format";
import { useApi, useDebounced } from "@/lib/hooks";
import type { ContentItem, SearchResponse } from "@/lib/types";

const FORMATS: { key: string; label: string; desc: string; icon: LucideIcon }[] = [
  { key: "website", label: "Website", desc: "Research highlight", icon: Newspaper },
  { key: "linkedin", label: "LinkedIn", desc: "Professional research post", icon: Users },
  { key: "instagram", label: "Instagram", desc: "Short educational caption", icon: Megaphone },
  { key: "student", label: "Student", desc: "Simple explanation", icon: GraduationCap },
  { key: "public", label: "Public", desc: "Plain-language explanation", icon: UserRound },
  { key: "media", label: "Media", desc: "Press-style research summary", icon: BookOpen },
  { key: "summary", label: "Research Summary", desc: "Structured summary with methods", icon: FileText },
  { key: "newsletter", label: "Newsletter", desc: "Short feature", icon: Mail },
  { key: "expedition_update", label: "Expedition Update", desc: "Field news", icon: Ship },
  { key: "highlight", label: "Research Highlight", desc: "Three-sentence highlight", icon: Star },
];

const AUDIENCES: { key: string; label: string }[] = [
  { key: "researchers", label: "Researchers" }, { key: "students", label: "Students" }, { key: "teachers", label: "Teachers" },
  { key: "general_public", label: "General Public" }, { key: "media", label: "Media" }, { key: "policy", label: "Policy / Institutional" },
];
const DEFAULT_AUDIENCE: Record<string, string> = {
  student: "students", public: "general_public", media: "media", linkedin: "researchers", summary: "researchers",
  instagram: "general_public", website: "general_public", newsletter: "general_public", expedition_update: "general_public", highlight: "general_public",
};

const PIPELINE = ["Selected research", "Evidence retrieval", "Key findings", "Evidence validation", "Audience", "Content generation",
  "Citation attachment", "Evidence check", "Human editing", "Review", "Approval", "Dissemination"];
const STATUS_STAGE: Record<string, number> = { draft: 8, evidence_checked: 8, changes_requested: 8, under_review: 9, approved: 10, published: 11, rejected: 9 };

function WorkflowStepper({ status }: { status: string }) {
  const at = STATUS_STAGE[status] ?? 8;
  return (
    <ol aria-label="Research-to-outreach workflow" className="flex gap-1 overflow-x-auto pb-1 scrollbar-thin">
      {PIPELINE.map((p, i) => (
        <li key={p} aria-current={i === at ? "step" : undefined}
          className={clsx("shrink-0 rounded-full px-2.5 py-1 text-[11px] whitespace-nowrap",
            i < at ? "bg-[#e2f4f1] text-teal" : i === at ? (status === "rejected" ? "bg-[#fbe9e5] text-coral" : "bg-night text-white") : "bg-ice text-mist")}>
          {i + 1}. {p}
        </li>
      ))}
    </ol>
  );
}

type SourceKind = "document" | "dataset" | "topic" | "expedition" | "activity";

function SourcePicker({ value, onChange }: { value: Source | null; onChange: (v: Source) => void }) {
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 250);
  const [kind, setKind] = useState<SourceKind>("document");
  const searchable = kind === "document" || kind === "dataset" || kind === "expedition" || kind === "activity";
  const docs = useApi<SearchResponse>(!searchable ? null : kind === "dataset" ? "/api/datasets" : "/api/resources",
    { q: dq, kind: kind === "dataset" ? undefined : kind, page_size: 8, sort: dq ? "relevance" : "views" });
  const topics = useApi<{ results: { slug: string; name: string; count: number }[] }>(kind === "topic" ? "/api/topics" : null);
  return (
    <div>
      <Tabs className="mb-3 w-fit max-w-full" value={kind} onChange={setKind} tabs={[{ key: "document", label: "Document" }, { key: "dataset", label: "Dataset" }, { key: "expedition", label: "Expedition" }, { key: "activity", label: "Activity" }, { key: "topic", label: "Topic" }]} />
      {kind !== "topic" && <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Search ${kind}s…`} className={inputCls} aria-label="Search sources" />}
      <ul className="mt-2 max-h-64 overflow-y-auto rounded-xl border border-frost scrollbar-thin">
        {kind === "topic"
          ? topics.data?.results.filter((t) => t.count > 0).map((t) => (
              <li key={t.slug}>
                <button onClick={() => onChange({ type: "topic", slug: t.slug, title: t.name })} className={clsx("flex w-full items-center justify-between px-3 py-2 text-left text-[13.5px] hover:bg-snow", value?.slug === t.slug && "bg-[#e3f4fa]")}>
                  {t.name} <span className="text-[11px] text-mist">{t.count}</span>
                </button>
              </li>
            ))
          : docs.loading ? <li className="p-3"><Skeleton className="h-4 w-2/3" /></li>
          : docs.data?.results.map((r) => (
              <li key={r.slug}>
                <button onClick={() => onChange({ type: r.type, slug: r.slug, title: r.title })} className={clsx("block w-full px-3 py-2 text-left hover:bg-snow", value?.slug === r.slug && "bg-[#e3f4fa]")}>
                  <span className="block text-[13.5px] text-night">{r.title}</span>
                  <span className="block text-[11.5px] text-steel">{r.kind} · {r.region} · {r.year}</span>
                </button>
              </li>
            ))}
      </ul>
    </div>
  );
}

interface Source { type: string; slug: string; title: string; ids?: number[] }

const DETAIL_PATH: Record<string, (s: string) => string> = {
  document: (s) => `/api/resources/${s}`, dataset: (s) => `/api/datasets/${s}`, expedition: (s) => `/api/expeditions/${s}`,
  station: (s) => `/api/stations/${s}`, researcher: (s) => `/api/researchers/${s}`, activity: (s) => `/api/activities/${s}`,
  topic: (s) => `/api/topics/${s}`,
};

function NewDraft({ initial }: { initial: { type: string; slug: string; ids?: number[] } | null }) {
  const router = useRouter();
  const toast = useToast();
  const [source, setSource] = useState<Source | null>(null);
  const [format, setFormat] = useState("student");
  const [audience, setAudience] = useState("students");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!initial) return;
    if (initial.type === "chunks") {
      setSource({ type: "chunks", slug: "", ids: initial.ids, title: `${initial.ids?.length || 0} cited passages from an AI answer` });
      return;
    }
    const path = (DETAIL_PATH[initial.type] || DETAIL_PATH.document)(initial.slug);
    api<{ title?: string; name?: string }>(path).then((d) => setSource({ ...initial, title: d.title || d.name || initial.slug })).catch(() => setSource(null));
  }, [initial]);

  const stages = ["Retrieve evidence", "Generate draft", "Attach sources", "Evidence validation"];
  const generate = async () => {
    if (!source) return;
    setBusy(true);
    setErr(null);
    setStage(0);
    const t = setInterval(() => setStage((s) => Math.min(stages.length - 1, s + 1)), 420);
    try {
      const c = await post<ContentItem>("/api/content/generate", source.type === "chunks"
        ? { format, audience, resource_type: "chunks", chunk_ids: source.ids }
        : { format, audience, resource_type: source.type, resource_slug: source.slug });
      await new Promise((r) => setTimeout(r, 900));
      toast("success", "Draft generated", "Review the evidence panel before submitting.");
      router.push(`/studio?id=${c.id}`);
    } catch (e) {
      setErr(e as ApiError);
    } finally {
      clearInterval(t);
      setBusy(false);
    }
  };

  return (
    <Card className="p-5 md:p-6">
      <h2 className="text-xl text-night">Create outreach content</h2>
      <p className="mt-1 text-[14px] text-ink-soft">Pick a research resource and an audience. The draft is built only from the resource&apos;s passages and keeps them attached as citations.</p>
      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">1 · Source</p>
          {source ? (
            <div className="mb-3 flex items-start justify-between gap-3 rounded-xl border border-cyan bg-[#f0f9fc] p-3">
              <div>
                <p className="text-[11px] uppercase tracking-wide text-cyan-deep">{source.type}</p>
                <p className="text-[14.5px] font-medium text-night">{source.title}</p>
              </div>
              <button className="text-[12.5px] text-cyan-deep hover:underline" onClick={() => setSource(null)}>Change</button>
            </div>
          ) : (
            <SourcePicker value={source} onChange={setSource} />
          )}
        </div>
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">2 · Format & audience</p>
          <div className="grid grid-cols-2 gap-2">
            {FORMATS.map((f) => {
              const I = f.icon;
              return (
                <button key={f.key} onClick={() => { setFormat(f.key); setAudience(DEFAULT_AUDIENCE[f.key] || "general_public"); }} aria-pressed={format === f.key}
                  className={clsx("rounded-xl border p-3 text-left transition", format === f.key ? "border-cyan bg-[#f0f9fc] ring-2 ring-cyan/15" : "border-frost hover:border-glacier")}>
                  <I className={clsx("mb-1.5 h-4.5 w-4.5", format === f.key ? "text-cyan-deep" : "text-mist")} />
                  <span className="block text-[14px] font-medium text-night">{f.label}</span>
                  <span className="block text-[12px] text-steel">{f.desc}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
      <div className="mt-5">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">3 · Audience</p>
        <div role="radiogroup" aria-label="Audience" className="flex flex-wrap gap-1.5">
          {AUDIENCES.map((a) => (
            <button key={a.key} role="radio" aria-checked={audience === a.key} onClick={() => setAudience(a.key)}
              className={clsx("rounded-full border px-3 py-1 text-[13px]", audience === a.key ? "border-cyan bg-[#e3f4fa] text-cyan-deep" : "border-frost text-ink-soft hover:border-glacier")}>
              {a.label}
            </button>
          ))}
        </div>
        <p className="mt-1.5 text-[11.5px] text-steel">Audience changes wording (simplified for students, teachers and the public), adds classroom questions for teachers and cited decision points for policy readers — never new facts.</p>
      </div>
      {busy && (
        <div className="mt-5 rounded-xl bg-snow p-4" role="status">
          <div className="flex gap-1.5">{stages.map((s, i) => <span key={s} className={clsx("h-1 flex-1 rounded-full", i <= stage ? "bg-cyan" : "bg-frost")} />)}</div>
          <p className="mt-2 text-[13px] text-ink-soft">{stages[stage]}…</p>
        </div>
      )}
      {err && <div className="mt-4"><ErrorState error={err} onRetry={generate} compact /></div>}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-frost pt-4">
        <p className="text-[12.5px] text-steel">Nothing is published automatically — drafts go to an editor for review.</p>
        <Button size="lg" onClick={generate} disabled={!source} loading={busy} icon={<Sparkles className="h-4 w-4" />}>Generate draft</Button>
      </div>
    </Card>
  );
}

function Editor({ id }: { id: number }) {
  const { data: item, error, loading, reload, setData } = useApi<ContentItem>(`/api/content/${id}`);
  const { user, can, demoLogin } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [mode, setMode] = useState<"edit" | "preview">("preview");
  const [active, setActive] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);
  const [side, setSide] = useState<"evidence" | "check" | "history">("evidence");

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setBody(item.body || "");
    }
  }, [item]);

  if (loading && !item) return <Skeleton className="h-[520px] w-full rounded-2xl" />;
  if (error || !item) return <ErrorState error={error || "Not found"} onRetry={reload} />;

  const editable = ["draft", "evidence_checked", "changes_requested"].includes(item.status) && (item.created_by_id === user?.id || can("edit_content"));
  const removeClaim = (text: string) => {
    const esc = text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+");
    const re = new RegExp(`\\s*${esc}(\\s*\\[\\d+\\])*`);
    const current = body;
    const next = current.replace(re, "").replace(/\n{3,}/g, "\n\n");
    if (next === current) {
      toast("info", "Remove it in the editor", "This sentence is formatted differently in the text — edit it manually.");
      setMode("edit");
      return;
    }
    setBody(next);
    setMode("edit");
    toast("success", "Claim removed", "Save changes to re-run the evidence check.");
  };
  const dirty = title !== item.title || body !== (item.body || "");
  const run = async (key: string, fn: () => Promise<ContentItem | void>, ok?: string) => {
    setBusy(key);
    try {
      const r = await fn();
      if (r) setData(r);
      if (ok) toast("success", ok);
    } catch (e) {
      toast("error", "Action failed", (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <Card className="min-w-0 overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 border-b border-frost bg-snow/70 px-5 py-3">
          <StatusBadge status={item.status} />
          <Badge tone="slate">{FORMAT_LABEL[item.format]}</Badge>
          <span className={clsx("rounded-full border px-2 py-0.5 font-mono text-[10.5px] uppercase", item.generation_mode.startsWith("curated") ? "border-dashed border-[#e2c58f] bg-[#fdf8ee] text-[#8a5c0c]" : "border-frost text-steel")}>
            {genModeLabel(item.generation_mode)}
          </span>
          <span className="font-mono text-[11px] text-mist">v{item.version}</span>
          {item.audience && <Badge tone="slate">For {AUDIENCE_LABEL[item.audience] || item.audience}</Badge>}
          {item.language && item.language !== "English" && <Badge tone="violet">{item.language}</Badge>}
          <div className="ml-auto">
            <Tabs value={mode} onChange={setMode} tabs={[{ key: "preview", label: <span className="inline-flex items-center gap-1"><Eye className="h-3.5 w-3.5" /> Preview</span> }, { key: "edit", label: <span className="inline-flex items-center gap-1"><PenLine className="h-3.5 w-3.5" /> Edit</span> }]} />
          </div>
        </div>
        <div className="border-b border-frost px-5 py-2.5"><WorkflowStepper status={item.status} /></div>
        <div className="p-5">
          <p className="mb-1 text-[12px] text-steel">Source: <span className="text-night">{item.resource_title}</span></p>
          {mode === "edit" && editable ? (
            <>
              <input value={title} onChange={(e) => setTitle(e.target.value)} className={clsx(inputCls, "mb-3 font-display text-lg")} aria-label="Title" />
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={18} className={clsx(inputCls, "font-mono text-[13px] leading-relaxed")} aria-label="Content body (Markdown)" />
              <p className="mt-1.5 text-[11.5px] text-steel">Markdown supported. Keep [n] markers next to sentences they support — the evidence check uses them.</p>
            </>
          ) : (
            <>
              {mode === "edit" && !editable && <p className="mb-3 rounded-lg bg-snow p-2.5 text-[12.5px] text-steel">This item is {item.status.replace("_", " ")} and can&apos;t be edited here{item.status === "under_review" ? " — an editor can edit it in the Review Center" : ""}.</p>}
              <h2 className="mb-3 text-[24px] leading-tight text-night">{title}</h2>
              <Markdown text={body} onCite={(n) => { setActive(n); setSide("evidence"); }} citeTitle={(n) => item.citations?.find((c) => c.n === n)?.label} />
            </>
          )}
          {item.generation_mode.startsWith("curated") && <div className="mt-4"><DemoBadge label="Curated demo draft — prepared in advance because no LLM is configured" /></div>}
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-frost bg-snow/50 px-5 py-3">
          {editable && (
            <Button variant="secondary" size="sm" disabled={!dirty} loading={busy === "save"} icon={<Save className="h-3.5 w-3.5" />}
              onClick={() => run("save", () => put<ContentItem>(`/api/content/${id}`, { title, body }), "Saved — evidence check re-run")}>
              Save changes
            </Button>
          )}
          {editable && (
            <Button variant="secondary" size="sm" loading={busy === "check"} disabled={dirty} icon={<ShieldCheck className="h-3.5 w-3.5" />}
              title={dirty ? "Save your changes first" : "Run the automated evidence check"}
              onClick={() => run("check", async () => {
                const ec = await post<NonNullable<ContentItem["evidence_check"]> & { status: ContentItem["status"] }>(`/api/content/${id}/check`);
                setSide("check");
                return { ...item, evidence_check: ec, status: ec.status } as ContentItem;
              }, "Evidence check complete")}>
              Run evidence check
            </Button>
          )}
          {editable && (
            <Button size="sm" loading={busy === "submit"} disabled={dirty} title={dirty ? "Save your changes first" : undefined} icon={<Send className="h-3.5 w-3.5" />}
              onClick={() => run("submit", () => post<ContentItem>(`/api/content/${id}/submit`), "Submitted for review")}>
              Submit for review
            </Button>
          )}
          {can("generate_content") && (item.language || "English") === "English" && (
            <select aria-label="Create a translation draft" value="" disabled={busy === "translate"}
              onChange={(e) => {
                const language = e.target.value;
                if (!language) return;
                run("translate", async () => {
                  const t = await post<ContentItem>(`/api/content/${id}/translate`, { language });
                  router.push(`/studio?id=${t.id}`);
                }, "Translation draft created");
              }}
              className="h-8 rounded-lg border border-frost bg-white px-2 text-[12.5px] text-ink-soft">
              <option value="">Translate draft…</option>
              <option value="Hindi">Hindi (हिन्दी)</option>
              <option value="Telugu">Telugu (తెలుగు)</option>
            </select>
          )}
          {item.status !== "published" && (item.created_by_id === user?.id || user?.role === "admin") && (
            <Button variant="ghost" size="sm" className="ml-auto text-coral" icon={<Trash2 className="h-3.5 w-3.5" />} onClick={() => setConfirmDel(true)}>Delete</Button>
          )}
        </div>
        {item.status === "under_review" && (
          <div className="flex flex-wrap items-center gap-3 border-t border-[#dcd7f5] bg-[#f6f5fd] px-5 py-4">
            <ClipboardCheck className="h-5 w-5 text-[#5a4bb5]" />
            <p className="flex-1 text-[13.5px] text-night">Waiting for editorial review. An editor checks the sources and approves before anything is published.</p>
            {can("review") ? (
              <Button size="sm" onClick={() => router.push(`/review?item=${id}`)} icon={<ArrowRight className="h-3.5 w-3.5" />}>Open Review Center</Button>
            ) : user?.is_demo ? (
              <Button size="sm" variant="dark" onClick={async () => { await demoLogin("editor"); toast("success", "Switched to Editor demo account"); router.push(`/review?item=${id}`); }}>
                Switch to Editor (demo) & review
              </Button>
            ) : null}
          </div>
        )}
        {item.language && item.language !== "English" && (
          <div className="flex items-start gap-2 border-t border-[#dcd7f5] bg-[#f6f5fd] px-5 py-3 text-[12.5px] text-night">
            <Languages className="mt-0.5 h-4 w-4 text-[#5a4bb5]" aria-hidden />
            Prototype translation workflow: a bilingual editor must confirm meaning, numbers and every [n] marker against the English original before approval.
          </div>
        )}
        {item.status === "published" && (
          <div className="flex flex-wrap items-center gap-3 border-t border-[#bfe5df] bg-[#f2faf8] px-5 py-4">
            <Megaphone className="h-5 w-5 text-teal" />
            <p className="flex-1 text-[13.5px] text-night">
              Published to: {(item.channel_status || []).map((c) => `${c.label}${c.status === "live" ? "" : " (prototype simulation)"}`).join(", ") || item.channels.join(", ")}.
            </p>
            <Link href="/outreach" className="text-[13px] font-medium text-teal hover:underline">View in Outreach Feed →</Link>
          </div>
        )}
      </Card>

      <Card className="h-fit p-5 xl:sticky xl:top-20">
        <Tabs className="mb-4" value={side} onChange={setSide} tabs={[
          { key: "evidence", label: `Sources · ${item.citations?.length || 0}` },
          { key: "check", label: "Evidence check" },
          { key: "history", label: "History" },
        ]} />
        {side === "evidence" && <CitationList item={item} active={active} onActive={setActive} />}
        {side === "check" && <EvidenceCheckView item={item} rechecking={busy === "check"} onRemoveClaim={editable ? removeClaim : undefined}
          onRecheck={() => run("check", async () => {
            const ec = await post<NonNullable<ContentItem["evidence_check"]> & { status: ContentItem["status"] }>(`/api/content/${id}/check`);
            return { ...item, evidence_check: ec, status: ec.status } as ContentItem;
          })} />}
        {side === "history" && <History item={item} />}
      </Card>

      <ConfirmDialog open={confirmDel} title="Delete this draft?" body="The draft and its attached citations will be permanently removed." confirmLabel="Delete draft" danger loading={busy === "del"}
        onCancel={() => setConfirmDel(false)}
        onConfirm={() => run("del", async () => { await del(`/api/content/${id}`); setConfirmDel(false); router.push("/studio"); }, "Draft deleted")} />
    </div>
  );
}

function MyContent({ current }: { current: number | null }) {
  const { data, loading } = useApi<{ results: ContentItem[]; counts: Record<string, number> }>("/api/content", { mine: true }, [current]);
  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-mono text-[11px] uppercase tracking-wider text-steel">My content</h2>
        <Link href="/studio" className="inline-flex items-center gap-1 text-[12.5px] text-cyan-deep hover:underline"><Plus className="h-3.5 w-3.5" /> New</Link>
      </div>
      {loading ? <Skeleton className="h-40 w-full" /> : !data?.results.length ? (
        <p className="py-6 text-center text-[13px] text-steel">No drafts yet.</p>
      ) : (
        <ul className="space-y-1">
          {data.results.map((c) => (
            <li key={c.id}>
              <Link href={`/studio?id=${c.id}`} className={clsx("block rounded-lg px-2.5 py-2 hover:bg-snow", current === c.id && "bg-ice")}>
                <span className="line-clamp-1 text-[13.5px] text-night">{c.title}</span>
                <span className="mt-0.5 flex items-center gap-2"><StatusBadge status={c.status} /><span className="text-[11px] text-mist">{timeAgo(c.updated_at)}</span></span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Studio() {
  const sp = useSearchParams();
  const id = sp.get("id") ? Number(sp.get("id")) : null;
  const type = sp.get("type");
  const slug = sp.get("slug");
  const ids = sp.get("ids");
  const [initial, setInitial] = useState<{ type: string; slug: string; ids?: number[] } | null>(null);
  useEffect(() => setInitial(
    type === "chunks" && ids ? { type, slug: "", ids: ids.split(",").map(Number).filter(Boolean).slice(0, 12) }
      : type && slug ? { type, slug } : null), [type, slug, ids]);
  return (
    <Container className="max-w-[1400px]">
      <PageHeader eyebrow="Outreach" title="Content Studio" description="Turn scientific resources into understandable outreach — source-linked, evidence-checked and human-reviewed before release." />
      <div className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="order-2 lg:order-1"><MyContent current={id} /></aside>
        <div className="order-1 min-w-0 lg:order-2">{id ? <Editor key={id} id={id} /> : <NewDraft initial={initial} />}</div>
      </div>
      {!id && !initial && (
        <div className="mt-6 hidden lg:block">
          <EmptyState icon={<Sparkles className="h-6 w-6" />} title="Tip: start from a resource page" body="Open any research document and choose “Generate Outreach Content” — the source is filled in for you." />
        </div>
      )}
    </Container>
  );
}

export default function Page() {
  return (
    <RequireAuth permission="generate_content" title="Content Studio">
      <Suspense>
        <Studio />
      </Suspense>
    </RequireAuth>
  );
}
