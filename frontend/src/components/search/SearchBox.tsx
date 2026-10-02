"use client";

import clsx from "clsx";
import { ArrowRight, Clock, Search, Sparkles, Tag, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useDebounced, useLocalList } from "@/lib/hooks";

interface Suggestion { text: string; kind: string; url?: string }

export function SearchBox({ initial = "", onSearch, size = "lg", dark, autoFocus, placeholder }: {
  initial?: string;
  onSearch?: (q: string) => void;
  size?: "lg" | "md";
  dark?: boolean;
  autoFocus?: boolean;
  placeholder?: string;
}) {
  const [q, setQ] = useState(initial);
  const [open, setOpen] = useState(false);
  const [sugs, setSugs] = useState<Suggestion[]>([]);
  const [hi, setHi] = useState(-1);
  const recent = useLocalList("polarnexus.recent-searches");
  const dq = useDebounced(q, 180);
  const router = useRouter();
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => setQ(initial), [initial]);
  useEffect(() => {
    if (!open) return;
    api<{ suggestions: Suggestion[] }>("/api/search/suggest", { query: { q: dq } })
      .then((d) => setSugs(d.suggestions))
      .catch(() => setSugs([]));
  }, [dq, open]);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => box.current && !box.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const go = (text: string, url?: string) => {
    const t = text.trim();
    setOpen(false);
    if (url && !url.startsWith("/explore")) return router.push(url);
    if (!t) return;
    recent.push(t);
    if (onSearch) onSearch(t);
    else router.push(url || `/explore?q=${encodeURIComponent(t)}`);
  };

  const list: (Suggestion & { recent?: boolean })[] = [
    ...(q.trim() ? [] : recent.items.slice(0, 4).map((r) => ({ text: r, kind: "recent", recent: true }))),
    ...sugs,
  ].slice(0, 9);

  return (
    <div ref={box} className="relative w-full">
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          if (hi >= 0 && list[hi]) go(list[hi].text, list[hi].url || undefined);
          else go(q);
        }}
        className={clsx(
          "flex items-center gap-2 rounded-2xl border transition-shadow",
          dark ? "border-white/15 bg-white/[0.08] backdrop-blur-md focus-within:border-glacier/60 focus-within:bg-white/[0.12]" : "border-frost bg-white shadow-card focus-within:border-cyan focus-within:ring-4 focus-within:ring-cyan/10",
          size === "lg" ? "h-[60px] pl-5 pr-2" : "h-12 pl-4 pr-1.5",
        )}
      >
        <Search className={clsx("h-5 w-5 shrink-0", dark ? "text-glacier" : "text-mist")} />
        <input
          value={q}
          autoFocus={autoFocus}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
            setHi(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setHi((h) => Math.min(list.length - 1, h + 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setHi((h) => Math.max(-1, h - 1));
            } else if (e.key === "Escape") setOpen(false);
          }}
          placeholder={placeholder || "Search polar knowledge…"}
          aria-label="Search polar knowledge"
          aria-autocomplete="list"
          aria-expanded={open}
          role="combobox"
          aria-controls="search-suggestions"
          className={clsx("min-w-0 flex-1 bg-transparent focus:outline-none", size === "lg" ? "text-[17px]" : "text-[15px]", dark ? "text-white placeholder:text-frost/60" : "text-night placeholder:text-mist")}
        />
        {q && (
          <button type="button" aria-label="Clear search" onClick={() => setQ("")} className={clsx("rounded-md p-1", dark ? "text-frost/70 hover:text-white" : "text-mist hover:text-night")}>
            <X className="h-4 w-4" />
          </button>
        )}
        <button type="submit" className={clsx("inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-cyan-deep font-medium text-white hover:bg-[#0c6f8e]", size === "lg" ? "h-11 px-5 text-[15px]" : "h-9 px-4 text-sm")}>
          Search <ArrowRight className="hidden h-4 w-4 sm:block" />
        </button>
      </form>
      {open && list.length > 0 && (
        <ul id="search-suggestions" role="listbox" className="absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-2xl border border-frost bg-white py-1.5 text-left shadow-lift">
          {!q.trim() && recent.items.length > 0 && (
            <li className="flex items-center justify-between px-4 pb-1 pt-1.5 font-mono text-[10px] uppercase tracking-wider text-steel">
              Recent searches
              <button className="normal-case tracking-normal text-cyan-deep hover:underline" onMouseDown={(e) => e.preventDefault()} onClick={recent.clear}>
                Clear
              </button>
            </li>
          )}
          {list.map((s, i) => {
            const Icon = s.kind === "recent" ? Clock : s.kind === "topic" ? Tag : s.kind === "suggested" || s.kind === "query" || s.kind === "related" ? Sparkles : Search;
            return (
              <li key={`${s.kind}${s.text}`} role="option" aria-selected={hi === i}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => go(s.text, s.url || undefined)}
                  onMouseEnter={() => setHi(i)}
                  className={clsx("flex w-full items-center gap-3 px-4 py-2 text-left text-[14px]", hi === i ? "bg-ice" : "hover:bg-snow")}
                >
                  <Icon className="h-4 w-4 shrink-0 text-mist" />
                  <span className="min-w-0 flex-1 truncate text-night">{s.text}</span>
                  <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-mist">{s.kind === "recent" ? "" : s.kind}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
