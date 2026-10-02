"use client";

import { Fragment, type ReactNode } from "react";

/**
 * Minimal, safe Markdown renderer (no HTML injection): paragraphs, **bold**, *italic*,
 * bullet/numbered lists and [n] citation markers rendered as interactive chips.
 */
export function Markdown({ text, onCite, citeTitle }: { text: string; onCite?: (n: number) => void; citeTitle?: (n: number) => string | undefined }) {
  const blocks = text.replace(/\r/g, "").split(/\n{2,}/);
  return (
    <div className="prose-polar text-[15px] text-ink">
      {blocks.map((block, bi) => {
        const lines = block.split("\n").filter((l) => l.trim().length);
        if (!lines.length) return null;
        const isUl = lines.every((l) => /^\s*[-•*]\s+/.test(l));
        const isOl = lines.every((l) => /^\s*\d+[.)]\s+/.test(l));
        if (isUl || isOl) {
          const Tag = isOl ? "ol" : "ul";
          return (
            <Tag key={bi}>
              {lines.map((l, li) => (
                <li key={li}>{inline(l.replace(/^\s*([-•*]|\d+[.)])\s+/, ""), onCite, citeTitle)}</li>
              ))}
            </Tag>
          );
        }
        // mixed block: render lines with soft breaks, but lists inside get their own list
        const out: ReactNode[] = [];
        let list: string[] = [];
        const flush = () => {
          if (list.length) {
            out.push(
              <ul key={`l${out.length}`}>
                {list.map((l, i) => <li key={i}>{inline(l.replace(/^\s*[-•*]\s+/, ""), onCite, citeTitle)}</li>)}
              </ul>,
            );
            list = [];
          }
        };
        lines.forEach((l, i) => {
          if (/^\s*[-•*]\s+/.test(l)) list.push(l);
          else {
            flush();
            out.push(
              <p key={`p${i}`}>{inline(l.replace(/^#+\s*/, ""), onCite, citeTitle)}</p>,
            );
          }
        });
        flush();
        return <Fragment key={bi}>{out}</Fragment>;
      })}
    </div>
  );
}

function inline(s: string, onCite?: (n: number) => void, citeTitle?: (n: number) => string | undefined): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|\[\d+\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(s))) {
    if (m.index > last) parts.push(s.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) parts.push(<strong key={k++}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("[")) {
      const n = Number(tok.slice(1, -1));
      parts.push(
        <button
          key={k++}
          type="button"
          onClick={() => onCite?.(n)}
          title={citeTitle?.(n) || `Source ${n}`}
          aria-label={`Open source ${n}${citeTitle?.(n) ? `: ${citeTitle(n)}` : ""}`}
          className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-px items-center justify-center rounded-md bg-[#e3f4fa] px-1 align-middle font-mono text-[10.5px] font-semibold text-cyan-deep hover:bg-cyan hover:text-white"
        >
          {n}
        </button>,
      );
    } else parts.push(<em key={k++}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < s.length) parts.push(s.slice(last));
  return parts;
}

export function highlightTerms(text: string, terms: string[]): ReactNode[] {
  if (!terms.length) return [text];
  const esc = terms.filter((t) => t.length > 2).map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (!esc.length) return [text];
  const re = new RegExp(`(${esc.join("|")})`, "gi");
  return text.split(re).map((part, i) =>
    i % 2 === 1 ? (
      <mark key={i} className="rounded bg-[#fdf1cf] px-0.5 text-night">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}
