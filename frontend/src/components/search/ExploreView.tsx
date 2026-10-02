"use client";

import clsx from "clsx";
import { Bookmark, LayoutGrid, List, SlidersHorizontal, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";
import { ResourceCard, ResourceRow } from "@/components/cards/ResourceCard";
import { useToast } from "@/components/common/Toast";
import {
  Button,
  CardSkeleton,
  Chip,
  EmptyState,
  ErrorState,
  GLOSSARY,
  InfoTip,
  Modal,
  Pagination,
  inputCls,
} from "@/components/common/ui";
import { post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtNum } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { SearchResponse } from "@/lib/types";
import { SearchBox } from "./SearchBox";

const REGIONS = ["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"];
const ALL_TYPES = ["Research Paper", "Technical Report", "Expedition Report", "Educational Resource", "News / Outreach", "Dataset", "Image", "Video", "Infographic", "Expedition", "Research Station", "Researcher", "Institutional Activity", "Topic", "Outreach Content"];
const VERIFICATION = ["Verified", "Official", "Partner", "Uploaded", "Pending", "Demo", "Synthetic"];
const GROUP_TYPE: Record<string, string[]> = {
  Documents: ["Research Paper", "Technical Report", "Expedition Report", "Educational Resource", "News / Outreach"],
  Datasets: ["Dataset"], Images: ["Image", "Infographic"], Videos: ["Video"], Expeditions: ["Expedition"],
  Stations: ["Research Station"], Researchers: ["Researcher"], "Institutional Activities": ["Institutional Activity"],
  Topics: ["Topic"], "Outreach Content": ["Outreach Content"],
};
const DOC_TYPES = ALL_TYPES.slice(0, 5);
const MEDIA_TYPES = ["Image", "Video", "Infographic"];

type Kind = "document" | "dataset" | "media" | undefined;

function useParamState() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const get = (k: string) => sp.get(k) || "";
  const getAll = (k: string) => sp.getAll(k);
  const set = (updates: Record<string, string | string[] | null>, resetPage = true) => {
    const next = new URLSearchParams(sp.toString());
    Object.entries(updates).forEach(([k, v]) => {
      next.delete(k);
      if (Array.isArray(v)) v.forEach((x) => next.append(k, x));
      else if (v) next.set(k, v);
    });
    if (resetPage && !("page" in updates)) next.delete("page");
    router.push(`${pathname}?${next.toString()}`, { scroll: false });
  };
  return { sp, get, getAll, set };
}

function FilterGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="border-b border-frost pb-4 pt-4 first:pt-0 last:border-0">
      <legend className="mb-2 font-mono text-[10.5px] uppercase tracking-wider text-steel">{title}</legend>
      {children}
    </fieldset>
  );
}

function Check({ label, checked, onChange, count }: { label: string; checked: boolean; onChange: () => void; count?: number }) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 py-1 text-[13.5px] text-ink-soft hover:text-night">
      <input type="checkbox" checked={checked} onChange={onChange} className="h-4 w-4 rounded border-frost accent-[#0f7fa1]" />
      <span className="flex-1">{label}</span>
      {count !== undefined && <span className="font-mono text-[11px] text-mist">{count}</span>}
    </label>
  );
}

export function ExploreView({ kind, header }: { kind?: Kind; header: ReactNode }) {
  const { get, getAll, set } = useParamState();
  const { user } = useAuth();
  const toast = useToast();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [layout, setLayout] = useState<"grid" | "list">("grid");

  const q = get("q");
  const mode = (get("mode") || "hybrid") as "hybrid" | "keyword" | "semantic";
  const sort = get("sort") || (q ? "relevance" : "views");
  const page = Number(get("page") || 1);
  const regions = getAll("region");
  const types = getAll("type");
  const topics = getAll("topic");
  const yearFrom = get("year_from");
  const yearTo = get("year_to");
  const station = get("station");
  const expedition = get("expedition");
  const language = get("language");
  const dataType = get("data_type");
  const category = get("category");
  const verification = getAll("verification");
  const organisation = get("organisation");
  const researcher = get("researcher");

  const endpoint = kind === "dataset" ? "/api/datasets" : kind === "media" ? "/api/media" : "/api/resources";
  const query = {
    q, mode, sort, page, page_size: kind === "media" ? 12 : 12, region: regions, type: types, topic: topics,
    year_from: yearFrom, year_to: yearTo, station, expedition, language, data_type: dataType, verification, organisation, researcher,
    kind: kind === "document" ? "document" : undefined, category: kind === "media" ? category : undefined,
  };
  const { data, error, loading, reload } = useApi<SearchResponse & { categories?: Record<string, number> }>(endpoint, query);
  const topicList = useApi<{ results: { slug: string; name: string; count: number }[] }>("/api/topics");
  const stationList = useApi<{ results: { slug: string; name: string }[] }>("/api/stations");
  const expList = useApi<{ results: { slug: string; name: string; season: string }[] }>("/api/expeditions");
  const options = useApi<{ organisations: string[]; researchers: { slug: string; name: string }[] }>("/api/filters/options");
  const terms = useMemo(() => (q ? q.split(/\s+/).filter((t) => t.length > 2) : []), [q]);

  const typeOptions = kind === "document" ? DOC_TYPES : kind === "media" ? MEDIA_TYPES : kind === "dataset" ? [] : ALL_TYPES;
  const toggle = (key: string, list: string[], v: string) => set({ [key]: list.includes(v) ? list.filter((x) => x !== v) : [...list, v] });
  const activeChips: { label: string; clear: () => void }[] = [
    ...regions.map((r) => ({ label: r, clear: () => toggle("region", regions, r) })),
    ...types.map((t) => ({ label: t, clear: () => toggle("type", types, t) })),
    ...topics.map((t) => ({ label: topicList.data?.results.find((x) => x.slug === t)?.name || t, clear: () => toggle("topic", topics, t) })),
    ...(yearFrom ? [{ label: `From ${yearFrom}`, clear: () => set({ year_from: null }) }] : []),
    ...(yearTo ? [{ label: `To ${yearTo}`, clear: () => set({ year_to: null }) }] : []),
    ...(station ? [{ label: `Station: ${stationList.data?.results.find((s) => s.slug === station)?.name || station}`, clear: () => set({ station: null }) }] : []),
    ...(expedition ? [{ label: `Expedition: ${expList.data?.results.find((s) => s.slug === expedition)?.name || expedition}`, clear: () => set({ expedition: null }) }] : []),
    ...(language ? [{ label: language, clear: () => set({ language: null }) }] : []),
    ...(dataType ? [{ label: dataType, clear: () => set({ data_type: null }) }] : []),
    ...(category ? [{ label: category, clear: () => set({ category: null }) }] : []),
    ...verification.map((v) => ({ label: v, clear: () => toggle("verification", verification, v) })),
    ...(organisation ? [{ label: organisation, clear: () => set({ organisation: null }) }] : []),
    ...(researcher ? [{ label: `Researcher: ${options.data?.researchers.find((r) => r.slug === researcher)?.name || researcher}`, clear: () => set({ researcher: null }) }] : []),
  ];
  const clearAll = () =>
    set({ region: null, type: null, topic: null, year_from: null, year_to: null, station: null, expedition: null, language: null, data_type: null, category: null, verification: null, organisation: null, researcher: null });

  const facets = data?.facets;
  const filters = (
    <div>
      <FilterGroup title="Region">
        {REGIONS.map((r) => (
          <Check key={r} label={r} checked={regions.includes(r)} onChange={() => toggle("region", regions, r)} count={facets?.regions[r]} />
        ))}
      </FilterGroup>
      {typeOptions.length > 0 && (
        <FilterGroup title="Resource type">
          {typeOptions.map((t) => (
            <Check key={t} label={t} checked={types.includes(t)} onChange={() => toggle("type", types, t)} count={facets?.types[t]} />
          ))}
        </FilterGroup>
      )}
      {kind === "media" && data?.categories && (
        <FilterGroup title="Category">
          <select value={category} onChange={(e) => set({ category: e.target.value || null })} className={inputCls} aria-label="Media category">
            <option value="">All categories</option>
            {Object.entries(data.categories).map(([c, n]) => <option key={c} value={c}>{c} ({n})</option>)}
          </select>
        </FilterGroup>
      )}
      {kind === "dataset" && (
        <FilterGroup title="Data type">
          <select value={dataType} onChange={(e) => set({ data_type: e.target.value || null })} className={inputCls} aria-label="Data type">
            <option value="">All data types</option>
            {["Time series", "Profiles", "Point observations", "Annual series", "Paleoclimate record"].map((d) => <option key={d}>{d}</option>)}
          </select>
        </FilterGroup>
      )}
      <FilterGroup title="Year">
        <div className="flex items-center gap-2">
          <input type="number" inputMode="numeric" placeholder={String(facets?.year_min || 1980)} defaultValue={yearFrom} key={`yf${yearFrom}`} aria-label="From year" min={1800} max={2100}
            onBlur={(e) => e.target.value !== yearFrom && set({ year_from: e.target.value || null })}
            onKeyDown={(e) => e.key === "Enter" && set({ year_from: (e.target as HTMLInputElement).value || null })} className={inputCls} />
          <span className="text-mist">–</span>
          <input type="number" inputMode="numeric" placeholder={String(facets?.year_max || 2025)} defaultValue={yearTo} key={`yt${yearTo}`} aria-label="To year" min={1800} max={2100}
            onBlur={(e) => e.target.value !== yearTo && set({ year_to: e.target.value || null })}
            onKeyDown={(e) => e.key === "Enter" && set({ year_to: (e.target as HTMLInputElement).value || null })} className={inputCls} />
        </div>
      </FilterGroup>
      <FilterGroup title="Scientific topic">
        <select value={topics[0] || ""} onChange={(e) => set({ topic: e.target.value ? [e.target.value] : null })} className={inputCls} aria-label="Scientific topic">
          <option value="">All topics</option>
          {topicList.data?.results.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
        </select>
      </FilterGroup>
      <FilterGroup title="Research station">
        <select value={station} onChange={(e) => set({ station: e.target.value || null })} className={inputCls} aria-label="Research station">
          <option value="">Any station</option>
          {stationList.data?.results.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
        </select>
      </FilterGroup>
      <FilterGroup title="Expedition">
        <select value={expedition} onChange={(e) => set({ expedition: e.target.value || null })} className={inputCls} aria-label="Expedition">
          <option value="">Any expedition</option>
          {expList.data?.results.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
        </select>
      </FilterGroup>
      <FilterGroup title="Verification">
        {VERIFICATION.map((v) => (
          <Check key={v} label={v} checked={verification.includes(v)} onChange={() => toggle("verification", verification, v)} count={facets?.verification?.[v]} />
        ))}
      </FilterGroup>
      <FilterGroup title="Researcher">
        <select value={researcher} onChange={(e) => set({ researcher: e.target.value || null })} className={inputCls} aria-label="Researcher">
          <option value="">Any researcher</option>
          {options.data?.researchers.map((r) => <option key={r.slug} value={r.slug}>{r.name}</option>)}
        </select>
      </FilterGroup>
      <FilterGroup title="Organisation">
        <select value={organisation} onChange={(e) => set({ organisation: e.target.value || null })} className={inputCls} aria-label="Organisation">
          <option value="">Any organisation</option>
          {options.data?.organisations.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </FilterGroup>
      {kind !== "dataset" && kind !== "media" && (
        <FilterGroup title="Language">
          <select value={language} onChange={(e) => set({ language: e.target.value || null })} className={inputCls} aria-label="Language">
            <option value="">Any language</option>
            <option>English</option>
            <option>Hindi</option>
          </select>
        </FilterGroup>
      )}
    </div>
  );

  return (
    <div>
      {header}
      <div className="mb-5">
        <SearchBox size="md" initial={q} onSearch={(t) => set({ q: t, sort: null })} placeholder={kind === "dataset" ? "Search datasets, variables, regions…" : kind === "media" ? "Search photos, videos, infographics…" : "Search polar knowledge…"} />
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Search mode" className="flex items-center rounded-lg bg-ice p-0.5">
          {(["keyword", "semantic", "hybrid"] as const).map((m) => (
            <button key={m} role="radio" aria-checked={mode === m} onClick={() => set({ mode: m })}
              className={clsx("rounded-md px-3 py-1.5 text-[13px] capitalize", mode === m ? "bg-white font-medium text-night shadow-sm" : "text-ink-soft hover:text-night")}>
              {m}
            </button>
          ))}
        </div>
        <InfoTip label={`${mode[0].toUpperCase()}${mode.slice(1)} search`} text={GLOSSARY[mode]} />
        <div className="ml-auto flex items-center gap-2">
          <label className="sr-only" htmlFor="sort">Sort</label>
          <select id="sort" value={sort} onChange={(e) => set({ sort: e.target.value })} className="h-9 rounded-lg border border-frost bg-white px-2.5 text-[13px] text-night">
            {q && <option value="relevance">Relevance</option>}
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="views">Most viewed</option>
            <option value="alphabetical">Alphabetical</option>
          </select>
          <div className="hidden rounded-lg bg-ice p-0.5 sm:flex">
            {([["grid", LayoutGrid], ["list", List]] as const).map(([k, I]) => (
              <button key={k} aria-label={`${k} view`} aria-pressed={layout === k} onClick={() => setLayout(k)} className={clsx("rounded-md p-1.5", layout === k ? "bg-white text-night shadow-sm" : "text-steel")}>
                <I className="h-4 w-4" />
              </button>
            ))}
          </div>
          <Button variant="secondary" size="sm" className="lg:hidden" onClick={() => setFiltersOpen(true)} icon={<SlidersHorizontal className="h-3.5 w-3.5" />}>
            Filters{activeChips.length ? ` (${activeChips.length})` : ""}
          </Button>
        </div>
      </div>

      {!kind && data?.facets.resource_groups && Object.keys(data.facets.resource_groups).length > 1 && (
        <nav aria-label="Results by resource type" className="mb-4 flex flex-wrap gap-1.5">
          {Object.entries(data.facets.resource_groups).map(([g, n]) => {
            const on = GROUP_TYPE[g]?.every((t) => types.includes(t));
            return (
              <button key={g} type="button" aria-pressed={on}
                onClick={() => set({ type: on ? types.filter((t) => !GROUP_TYPE[g].includes(t)) : Array.from(new Set([...types, ...(GROUP_TYPE[g] || [])])) })}
                className={clsx("rounded-full border px-3 py-1 text-[12.5px]", on ? "border-cyan bg-[#e3f4fa] text-cyan-deep" : "border-frost bg-white text-ink-soft hover:border-glacier")}>
                <strong className="font-semibold text-night">{fmtNum(n)}</strong> {g}
              </button>
            );
          })}
        </nav>
      )}

      {activeChips.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {activeChips.map((c) => <Chip key={c.label} active onRemove={c.clear}>{c.label}</Chip>)}
          <button onClick={clearAll} className="text-[13px] text-cyan-deep hover:underline">Clear all</button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[250px_1fr]">
        <aside className="hidden lg:block">
          <div className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto rounded-2xl border border-frost bg-white p-4 shadow-card scrollbar-thin">{filters}</div>
        </aside>
        <section aria-live="polite" aria-busy={loading}>
          <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-steel">
            {data && !loading && (
              <>
                <span>
                  <strong className="text-night">{fmtNum(data.total)}</strong> {data.total === 1 ? "result" : "results"}
                  {q && <> for “<span className="text-night">{q}</span>”</>}
                </span>
                {q && <span className="font-mono text-[11px]">· {data.mode_used} · {data.took_ms} ms</span>}
                {data.notice && <span className="rounded bg-[#fbf1df] px-2 py-0.5 text-[#7a520b]">{data.notice}</span>}
                {user && q && (
                  <button
                    onClick={async () => {
                      try {
                        await post("/api/saved", { item_type: "search", label: `${q} · ${mode}`, query: { q, mode, region: regions, type: types } });
                        toast("success", "Search saved", "Find it in My Knowledge.");
                      } catch (e) {
                        toast("error", "Could not save search", (e as Error).message);
                      }
                    }}
                    className="ml-auto inline-flex items-center gap-1 text-cyan-deep hover:underline"
                  >
                    <Bookmark className="h-3.5 w-3.5" /> Save search
                  </button>
                )}
              </>
            )}
          </div>
          {error ? (
            <ErrorState error={error} onRetry={reload} />
          ) : loading || !data ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}</div>
          ) : data.results.length === 0 ? (
            <EmptyState
              title="No resources found"
              body="Try changing your filters or search terms, or switch to semantic search to match by meaning."
              action={
                <div className="flex gap-2">
                  {activeChips.length > 0 && <Button variant="secondary" onClick={clearAll}>Clear Filters</Button>}
                  {mode !== "semantic" && q && <Button onClick={() => set({ mode: "semantic" })}>Try semantic search</Button>}
                </div>
              }
            />
          ) : layout === "grid" ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {data.results.map((r) => <ResourceCard key={`${r.type}${r.id}`} item={r} terms={terms} showReason={!!q} />)}
            </div>
          ) : (
            <div className="divide-y divide-frost rounded-2xl border border-frost bg-white px-2 py-1 shadow-card">
              {data.results.map((r) => <ResourceRow key={`${r.type}${r.id}`} item={r} />)}
            </div>
          )}
          {data && <Pagination page={data.page} pages={data.pages} onPage={(p) => { set({ page: String(p) }, false); window.scrollTo({ top: 0, behavior: "smooth" }); }} />}
        </section>
      </div>

      <Modal open={filtersOpen} onClose={() => setFiltersOpen(false)} title="Filters">
        {filters}
        <div className="mt-4 flex gap-2">
          <Button variant="secondary" className="flex-1" onClick={clearAll} icon={<X className="h-4 w-4" />}>Clear</Button>
          <Button className="flex-1" onClick={() => setFiltersOpen(false)}>Show {data ? fmtNum(data.total) : ""} results</Button>
        </div>
      </Modal>
    </div>
  );
}
