"use client";

import clsx from "clsx";
import {
  ArrowRight,
  BookOpen,
  ClipboardCheck,
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
import { FORMAT_LABEL, genModeLabel, timeAgo } from "@/lib/format";
import { useApi, useDebounced } from "@/lib/hooks";
import type { ContentItem, SearchResponse } from "@/lib/types";

const FORMATS: { key: string; label: string; desc: string; icon: LucideIcon }[] = [
  { key: "website", label: "Website", desc: "Research highlight", icon: Newspaper },
  { key: "linkedin", label: "LinkedIn", desc: "Professional research post", icon: Users },
  { key: "instagram", label: "Instagram", desc: "Short educational caption", icon: Megaphone },
  { key: "student", label: "Student", desc: "Simple explanation", icon: GraduationCap },
  { key: "public", label: "Public", desc: "Plain-language explanation", icon: UserRound },
  { key: "media", label: "Media", desc: "Press-style research summary", icon: BookOpen },
];

function SourcePicker({ value, onChange }: { value: { type: string; slug: string; title: string } | null; onChange: (v: { type: string; slug: string; title: string }) => void }) {
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 250);
  const [kind, setKind] = useState<"document" | "dataset" | "topic">("document");
  const docs = useApi<SearchResponse>(kind === "topic" ? null : kind === "dataset" ? "/api/datasets" : "/api/resources", { q: dq, kind: kind === "document" ? "document" : undefined, page_size: 8, sort: dq ? "relevance" : "views" });
  const topics = useApi<{ results: { slug: string; name: string; count: number }[] }>(kind === "topic" ? "/api/topics" : null);
  return (
    <div>
      <Tabs className="mb-3 w-fit" value={kind} onChange={setKind} tabs={[{ key: "document", label: "Document" }, { key: "dataset", label: "Dataset" }, { key: "topic", label: "Topic" }]} />
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

function NewDraft({ initial }: { initial: { type: string; slug: string } | null }) {
  const router = useRouter();
  const toast = useToast();
  const [source, setSource] = useState<{ type: string; slug: string; title: string } | null>(null);
  const [format, setFormat] = useState("student");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!initial) return;
    const path = initial.type === "dataset" ? `/api/datasets/${initial.slug}` : `/api/resources/${initial.slug}`;
    api<{ title: string }>(path).then((d) => setSource({ ...initial, title: d.title })).catch(() => setSource(null));
  }, [initial]);

  const stages = ["Retrieve evidence", "Generate draft", "Attach sources", "Evidence validation"];
  const generate = async () => {
    if (!source) return;
    setBusy(true);
    setErr(null);
    setStage(0);
    const t = setInterval(() => setStage((s) => Math.min(stages.length - 1, s + 1)), 420);
    try {
      const c = await post<ContentItem>("/api/content/generate", { format, resource_type: source.type, resource_slug: source.slug });
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
                <button key={f.key} onClick={() => setFormat(f.key)} aria-pressed={format === f.key}
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

  const editable = ["draft", "changes_requested"].includes(item.status) && (item.created_by_id === user?.id || can("edit_content"));
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
          <div className="ml-auto">
            <Tabs value={mode} onChange={setMode} tabs={[{ key: "preview", label: <span className="inline-flex items-center gap-1"><Eye className="h-3.5 w-3.5" /> Preview</span> }, { key: "edit", label: <span className="inline-flex items-center gap-1"><PenLine className="h-3.5 w-3.5" /> Edit</span> }]} />
          </div>
        </div>
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
            <Button size="sm" loading={busy === "submit"} disabled={dirty} title={dirty ? "Save your changes first" : undefined} icon={<Send className="h-3.5 w-3.5" />}
              onClick={() => run("submit", () => post<ContentItem>(`/api/content/${id}/submit`), "Submitted for review")}>
              Submit for review
            </Button>
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
        {item.status === "published" && (
          <div className="flex flex-wrap items-center gap-3 border-t border-[#bfe5df] bg-[#f2faf8] px-5 py-4">
            <Megaphone className="h-5 w-5 text-teal" />
            <p className="flex-1 text-[13.5px] text-night">Published to: {item.channels.join(", ")}.</p>
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
        {side === "check" && <EvidenceCheckView item={item} rechecking={busy === "check"} onRecheck={() => run("check", async () => {
          const ec = await post<ContentItem["evidence_check"]>(`/api/content/${id}/check`);
          return { ...item, evidence_check: ec } as ContentItem;
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
  const [initial, setInitial] = useState<{ type: string; slug: string } | null>(null);
  useEffect(() => setInitial(type && slug ? { type, slug } : null), [type, slug]);
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
