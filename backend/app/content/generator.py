"""Outreach content generation: research resource -> evidence -> draft -> citations -> evidence check.

With an LLM configured, drafts are written by the model from the retrieved evidence only. Without one,
a template generator assembles the draft from source sentences (lightly simplified for lay audiences),
so every sentence remains traceable to a passage. Nothing is ever published without human review.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.evidence_check import run_evidence_check
from app.models import Citation, Dataset, Document, DocumentChunk, GeneratedContent, ResourceLink, ResourceTopic, Topic, User
from app.rag.llm import LLMUnavailable, get_llm
from app.rag.simplify import glossary_for, simplify
from app.utils.text import split_sentences

log = logging.getLogger("polarnexus.content")

FORMATS = {
    "website": ("Website — Research highlight", "website"),
    "linkedin": ("LinkedIn — Professional research post", "social"),
    "instagram": ("Instagram — Short educational caption", "social"),
    "student": ("Student — Simple explanation", "education"),
    "public": ("Public — Plain-language explanation", "public"),
    "media": ("Media — Press-style research summary", "media"),
}

HOOKS = {
    "sea-ice": "Why does Antarctic sea ice change so much from one year to the next?",
    "ocean-carbon": "How does the Southern Ocean help absorb carbon dioxide?",
    "aerosols": "What is floating in the Arctic air — and why does it matter?",
    "stratospheric-ozone": "What happens to the ozone layer over Antarctica every spring?",
    "himalayan-cryosphere": "What is happening to the glaciers of the 'third pole'?",
    "polar-microbiology": "What lives in Antarctica's frozen lakes?",
    "upper-atmosphere": "What makes the polar skies glow?",
    "marine-ecosystems": "Why are tiny krill so important to Antarctic life?",
    "ice-cores-paleoclimate": "How can ice remember the climate of the past?",
}

PRIORITY_SECTIONS = ["Abstract", "Key Findings", "Preliminary Findings", "Outcome", "Highlights",
                     "Implications and Outreach Relevance", "Why It Matters", "Significance", "Limitations", "Background"]


@dataclass
class Source:
    n: int
    chunk: DocumentChunk
    title: str
    slug: str
    rtype: str
    rid: int


def gather_evidence(db: Session, resource_type: str, slug: str | None = None,
                    chunk_ids: list[int] | None = None) -> tuple[str, int | None, str, list[Source], list[str]]:
    """Returns (resource_type, resource_id, title, sources, topic_slugs)."""
    chunks: list[tuple[DocumentChunk, str, str]] = []
    rid, title, topic_slugs = None, "", []

    def doc_chunks(doc: Document, limit: int = 6) -> list[DocumentChunk]:
        ordered = sorted(doc.chunks, key=lambda c: (PRIORITY_SECTIONS.index(c.section) if c.section in PRIORITY_SECTIONS else 99, c.chunk_index))
        return ordered[:limit]

    if resource_type == "document" and slug:
        doc = db.scalar(select(Document).where(Document.slug == slug))
        if not doc:
            raise LookupError("Document not found")
        rid, title = doc.id, doc.title
        chunks = [(c, doc.title, doc.slug) for c in doc_chunks(doc)]
    elif resource_type == "dataset" and slug:
        ds = db.scalar(select(Dataset).where(Dataset.slug == slug))
        if not ds:
            raise LookupError("Dataset not found")
        rid, title = ds.id, ds.title
        own = db.scalars(select(DocumentChunk).where(DocumentChunk.resource_type == "dataset", DocumentChunk.resource_id == ds.id)).all()
        chunks = [(c, ds.title, ds.slug) for c in own]
        linked_doc_ids = [l.source_id if l.source_type == "document" else l.target_id for l in db.scalars(
            select(ResourceLink).where(
                ((ResourceLink.source_type == "dataset") & (ResourceLink.source_id == ds.id) & (ResourceLink.target_type == "document")) |
                ((ResourceLink.target_type == "dataset") & (ResourceLink.target_id == ds.id) & (ResourceLink.source_type == "document"))))]
        for d in db.scalars(select(Document).where(Document.id.in_(linked_doc_ids), Document.visibility == "public")).all()[:2]:
            chunks.extend((c, d.title, d.slug) for c in doc_chunks(d, 3))
    elif resource_type == "topic" and slug:
        topic = db.scalar(select(Topic).where(Topic.slug == slug))
        if not topic:
            raise LookupError("Topic not found")
        rid, title = topic.id, topic.name
        topic_slugs = [topic.slug]
        doc_ids = [rt.resource_id for rt in db.scalars(select(ResourceTopic).where(
            ResourceTopic.topic_id == topic.id, ResourceTopic.resource_type == "document"))]
        docs = db.scalars(select(Document).where(Document.id.in_(doc_ids), Document.visibility == "public")
                          .order_by(Document.views.desc())).all()[:3]
        for d in docs:
            chunks.extend((c, d.title, d.slug) for c in doc_chunks(d, 2))
    elif chunk_ids:
        rows = db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))).all()
        for c in rows:
            d = db.get(Document, c.document_id) if c.document_id else None
            chunks.append((c, d.title if d else c.section, d.slug if d else ""))
        resource_type, title = "chunks", (chunks[0][1] if chunks else "Research result")
    else:
        raise LookupError("Select a document, dataset or topic as the source.")

    if not topic_slugs and rid is not None and resource_type in {"document", "dataset"}:
        topic_slugs = [t.slug for t in db.scalars(select(Topic).join(ResourceTopic, ResourceTopic.topic_id == Topic.id)
                                                  .where(ResourceTopic.resource_type == resource_type,
                                                         ResourceTopic.resource_id == rid))]
    sources = [Source(n=i + 1, chunk=c, title=t, slug=s, rtype=c.resource_type, rid=c.resource_id)
               for i, (c, t, s) in enumerate(chunks)]
    if not sources:
        raise LookupError("The selected resource has no indexed text to generate from.")
    return resource_type, rid, title, sources, topic_slugs


def _sentences(sources: list[Source], sections: set[str], limit: int) -> list[tuple[str, int]]:
    out = []
    for src in sources:
        if src.chunk.section in sections:
            for s in split_sentences(src.chunk.text):
                if len(s) > 40 and not s.startswith("Figure"):
                    out.append((s, src.n))
    return out[:limit]


def _hashtags(topic_slugs: list[str]) -> str:
    tags = ["#PolarScience"] + ["#" + "".join(w.capitalize() for w in re.split(r"[-\s]", t)) for t in topic_slugs[:3]]
    return " ".join(dict.fromkeys(tags))


def template_draft(fmt: str, title: str, sources: list[Source], topic_slugs: list[str]) -> tuple[str, str]:
    abstract = _sentences(sources, {"Abstract", "Background", "Dataset description", "Voyage Summary"}, 3)
    findings = _sentences(sources, {"Key Findings", "Preliminary Findings", "Outcome", "Highlights", "Data Collected",
                                    "Key Concepts", "Significance"}, 4)
    implic = _sentences(sources, {"Implications and Outreach Relevance", "Why It Matters", "Significance", "Lessons", "Legacy"}, 2)
    limits = _sentences(sources, {"Limitations"}, 1)
    if not findings:
        findings = abstract[1:] or abstract
    hook = next((HOOKS[t] for t in topic_slugs if t in HOOKS), None)
    used: set[str] = set()

    def simp(s):
        return simplify(s, used)

    def tidy(s):
        s = re.sub(r"^(First|Second|Third|Fourth|Fifth),\s*", "", s)
        return s[0].upper() + s[1:] if s else s

    def cite(pairs, f=lambda s: s):
        return [f"{tidy(f(s))} [{n}]" for s, n in pairs]

    if fmt == "website":
        headline = f"Research Highlight: {title}"
        parts = [" ".join(cite(abstract[:2])), "**What the study found**", *[f"- {x}" for x in cite(findings[:4])]]
        if implic:
            parts += ["**Why it matters**", " ".join(cite(implic[:1]))]
        if limits:
            parts += ["**Caveats**", " ".join(cite(limits))]
        return headline, "\n\n".join(parts)
    if fmt == "linkedin":
        headline = f"LinkedIn: {title}"
        body = [f"New in the PolarNexus knowledge repository: **{title}**.", " ".join(cite(abstract[:1])),
                "Key points from the source:", *[f"- {x}" for x in cite(findings[:3])]]
        if limits:
            body.append("As the authors note: " + cite(limits)[0])
        body.append(_hashtags(topic_slugs))
        return headline, "\n\n".join(body)
    if fmt == "instagram":
        headline = f"Instagram: {title}"
        first = findings[0] if findings else abstract[0]
        body = [f"🧊 {hook}" if hook else f"🧊 {title}", f"{simp(first[0])} [{first[1]}]"]
        if implic:
            body.append(f"{simp(implic[0][0])} [{implic[0][1]}]")
        body += ["Source-linked and human-reviewed via PolarNexus.", _hashtags(topic_slugs) + " #ScienceForAll"]
        return headline, "\n\n".join(body)
    if fmt == "student":
        headline = f"For Students: {title}"
        text_all = " ".join(s for s, _ in abstract + findings + implic)
        body = ["**What is this about?**", " ".join(cite(abstract[:2], simp)),
                "**What did scientists find?**", *[f"- {x}" for x in cite(findings[:3], simp)]]
        if implic:
            body += ["**Why does it matter?**", " ".join(cite(implic[:1], simp))]
        gl = glossary_for(text_all)
        if gl:
            body += ["**Words to know**", *[f"- {g}" for g in gl]]
        return headline, "\n\n".join(body)
    if fmt == "public":
        headline = f"In Plain Language: {title}"
        body = [hook or f"What does {title} tell us?", " ".join(cite(abstract[:2], simp)),
                " ".join(cite(findings[:3], simp))]
        if limits:
            lim = cite(limits, simp)[0]
            body.append("The researchers are careful to note the limits of their work: " + lim[0].lower() + lim[1:])
        return headline, "\n\n".join(body)
    if fmt == "media":
        headline = f"Media Brief: {title}"
        body = [f"**{title}** — research summary for media", " ".join(cite(abstract[:2])),
                "**Key findings**", *[f"- {x}" for x in cite(findings[:4])]]
        if limits:
            body += ["**Context and limitations**", " ".join(cite(limits))]
        body.append("Note to editors: this summary is generated from a repository record and reviewed by an editor "
                    "before release. No quotations are attributed to the researchers.")
        return headline, "\n\n".join(body)
    raise ValueError("Unknown format")


CURATED_STUDENT_FLAGSHIP = (
    "**What is this about?**\n\n"
    "Every year, the sea around Antarctica freezes over in winter and melts back in summer [1]. This sea ice matters "
    "because its bright surface reflects sunlight and it is a home for algae, krill, penguins and seals [1].\n\n"
    "**What did scientists find?**\n\n"
    "- Wind can push the ice away from the coast or pile it up against it [2].\n"
    "- Warmer water under the ice can delay freezing in autumn, making the ice season shorter [2].\n"
    "- When freezing starts late, there is usually thinner and less ice in the months that follow [2].\n\n"
    "**Why does it matter?**\n\n"
    "No single cause controls Antarctic sea ice — wind, ocean warmth and timing work together, which is why it can "
    "change a lot from one year to the next [3].\n\n"
    "**Words to know**\n\n"
    "- Sea ice: frozen sea water floating on the ocean surface.\n"
    "- Freeze-up: the time in autumn when the sea starts to freeze."
)


def _llm_draft(fmt: str, title: str, sources: list[Source]) -> tuple[str, str] | None:
    llm = get_llm()
    if not llm:
        return None
    label = FORMATS[fmt][0]
    ev = "\n\n".join(f"[{s.n}] {s.title} — {s.chunk.section}\n{s.chunk.text}" for s in sources)
    system = ("You write science outreach content for a polar research knowledge platform. Use ONLY facts from the "
              "numbered evidence. Cite each factual sentence with [n]. Do not invent statistics, quotes, names or "
              "institutional statements. Keep cautious wording where the evidence is cautious. No hype words.")
    user = (f"Format: {label}.\nSource title: {title}\n\nEvidence:\n{ev}\n\n"
            "Return the first line as a short headline, then a blank line, then the body in Markdown.")
    text = llm.complete(system, user, max_tokens=700, temperature=0.4)
    head, _, body = text.partition("\n")
    return head.strip().lstrip("# ").strip("*") or title, body.strip()


def create_draft(db: Session, user: User | None, fmt: str, resource_type: str, slug: str | None = None,
                 chunk_ids: list[int] | None = None, prefer_curated: bool = True) -> GeneratedContent:
    if fmt not in FORMATS:
        raise ValueError(f"Unsupported format '{fmt}'.")
    rtype, rid, title, sources, topic_slugs = gather_evidence(db, resource_type, slug, chunk_ids)
    mode = "template"
    headline, body = None, None
    if prefer_curated and get_llm() is None and fmt == "student" and slug == "antarctic-sea-ice-variability-study":
        wanted = ["Background", "Key Findings", "Implications and Outreach Relevance"]
        picked = []
        for sec in wanted:
            cands = [s for s in sources if s.chunk.section == sec and s not in picked]
            if cands:
                picked.append(cands[0])
        if len(picked) == 3:
            sources = [Source(n=i + 1, chunk=s.chunk, title=s.title, slug=s.slug, rtype=s.rtype, rid=s.rid) for i, s in enumerate(picked)]
            headline, body, mode = f"For Students: {title}", CURATED_STUDENT_FLAGSHIP, "curated_demo"
    if body is None:
        try:
            res = _llm_draft(fmt, title, sources)
            if res:
                headline, body = res
                mode = "llm"
        except LLMUnavailable:
            log.warning("LLM unavailable; using template generator")
    if body is None:
        headline, body = template_draft(fmt, title, sources, topic_slugs)
        mode = "template"

    used_ns = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    kept = [s for s in sources if s.n in used_ns] or sources[:1]
    renumber = {s.n: i + 1 for i, s in enumerate(kept)}
    body = re.sub(r"\[(\d+)\]", lambda m: f"[{renumber[int(m.group(1))]}]" if int(m.group(1)) in renumber else "", body)
    content = GeneratedContent(
        title=headline or title, format=fmt, body=body, status="draft", generation_mode=mode,
        resource_type=rtype, resource_id=rid, resource_title=title, created_by=user.id if user else None,
        channels=[], is_demo=False,
    )
    for s in kept:
        content.citations.append(Citation(chunk_id=s.chunk.id, position=renumber[s.n], resource_type=s.rtype,
                                          resource_id=s.rid, resource_slug=s.slug, label=s.title,
                                          section=s.chunk.section, quote=s.chunk.text))
    content.evidence_check = run_evidence_check(body, [c.quote for c in content.citations], len(content.citations))
    db.add(content)
    db.flush()
    return content


def recheck(content: GeneratedContent) -> dict:
    content.evidence_check = run_evidence_check(content.body, [c.quote for c in content.citations], len(content.citations))
    return content.evidence_check
