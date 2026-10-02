"""Source-grounded document summaries (executive, research, student, 100-word, key findings, methodology, impact)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Document
from app.rag.llm import LLMUnavailable, get_llm
from app.rag.simplify import glossary_for, simplify
from app.utils.text import split_sentences

KINDS = {
    "executive": ("Executive Summary", ["Abstract", "Key Findings", "Implications and Outreach Relevance", "Why It Matters", "Significance"]),
    "research": ("Research Summary", ["Abstract", "Background", "Data and Methods", "Key Findings", "Limitations"]),
    "student": ("Student-Friendly Summary", ["Abstract", "Background", "Key Findings"]),
    "100-word": ("100-word Summary", ["Abstract", "Key Findings"]),
    "key-findings": ("Key Findings", ["Key Findings", "Preliminary Findings", "Outcome", "Highlights", "Key Concepts"]),
    "methodology": ("Methodology", ["Data and Methods", "Programme", "Recommendations", "Science Programmes"]),
    "impact": ("Research Impact", ["Implications and Outreach Relevance", "Why It Matters", "Significance", "Legacy", "Lessons", "Outcome"]),
}


def summarize(db: Session, doc: Document, kind: str) -> dict:
    if kind not in KINDS:
        raise ValueError("Unknown summary type")
    label, sections = KINDS[kind]
    chunks = [c for sec in sections for c in doc.chunks if c.section == sec]
    if not chunks:
        return {"kind": kind, "label": label, "text": "", "sources": [], "mode": "insufficient",
                "notice": f"This document has no indexed section that supports a '{label}'."}
    sources = [{"n": i + 1, "chunk_id": c.id, "section": c.section, "page": c.page, "snippet": c.text,
                "title": doc.title, "slug": doc.slug, "url": f"/resources/{doc.slug}"} for i, c in enumerate(chunks)]
    n_for = {c.id: i + 1 for i, c in enumerate(chunks)}

    llm = get_llm()
    if llm:
        ev = "\n\n".join(f"[{s['n']}] {s['section']}\n{s['snippet']}" for s in sources)
        try:
            text = llm.complete(
                "Summarise ONLY from the numbered passages, citing [n] after each sentence. No new facts or numbers.",
                f"Write a {label} of '{doc.title}'." + (" Keep it to at most 100 words." if kind == "100-word" else "")
                + (" Write for a school student with simple words." if kind == "student" else "") + f"\n\n{ev}",
                max_tokens=500)
            return {"kind": kind, "label": label, "text": text, "sources": sources, "mode": "llm", "notice": ""}
        except LLMUnavailable:
            pass

    used: set[str] = set()
    sent = [(s, n_for[c.id], c.section) for c in chunks for s in split_sentences(c.text) if not s.startswith("Figure")]
    if kind == "100-word":
        out, words = [], 0
        for s, n, _ in sent:
            w = len(s.split())
            if words + w > 100:
                break
            out.append(f"{s} [{n}]")
            words += w
        text = " ".join(out)
    elif kind in {"key-findings", "methodology"}:
        text = "\n".join(f"- {s} [{n}]" for s, n, _ in sent[:7])
    elif kind == "student":
        picked = [x for x in sent if x[2] != "Background"][:2] + [x for x in sent if x[2] == "Key Findings"][:4]
        text = "\n".join(f"- {simplify(s, used)} [{n}]" for s, n, _ in picked)
        gl = glossary_for(" ".join(s for s, _, _ in picked))
        if gl:
            text += "\n\n**Words to know**\n" + "\n".join(f"- {g}" for g in gl)
    elif kind == "executive":
        first = [x for x in sent if x[2] == "Abstract"][:2]
        finds = [x for x in sent if x[2] in sections[1:2]][:3]
        imp = [x for x in sent if x[2] in sections[2:]][:1]
        text = " ".join(f"{s} [{n}]" for s, n, _ in first)
        if finds:
            text += "\n\n" + "\n".join(f"- {s} [{n}]" for s, n, _ in finds)
        if imp:
            text += "\n\n" + " ".join(f"{s} [{n}]" for s, n, _ in imp)
    elif kind == "research":
        parts = []
        for sec in sections:
            ss = [x for x in sent if x[2] == sec][:2]
            if ss:
                parts.append(f"**{sec}.** " + " ".join(f"{s} [{n}]" for s, n, _ in ss))
        text = "\n\n".join(parts)
    else:  # impact
        text = " ".join(f"{s} [{n}]" for s, n, _ in sent[:4])
    return {"kind": kind, "label": label, "text": text, "sources": sources, "mode": "extractive",
            "notice": "Extractive summary — sentences selected from the document's own sections (no LLM configured)."}
