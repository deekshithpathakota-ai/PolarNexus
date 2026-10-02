"""Evidence-grounded question answering (RAG).

Pipeline: question -> query processing (intent, terms) -> hybrid retrieval (keyword + vector, RRF)
-> evidence assessment -> answer generation (LLM if configured; curated demo or extractive otherwise)
-> citation validation -> response with sources, evidence status and related knowledge.
"""
from __future__ import annotations

import logging
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIQuery, Document, DocumentChunk, User
from app.rag.curated import match_curated
from app.rag.llm import LLMUnavailable, get_llm
from app.rag.simplify import glossary_for, simplify
from app.search.hybrid import ChunkHit, retrieve
from app.search.keyword import _build as bm25_index
from app.services.catalog import Catalog, build_catalog
from app.utils.text import content_terms, split_sentences, stem, stems

log = logging.getLogger("polarnexus.rag")

INSUFFICIENT_MSG = ("I couldn't find sufficient supporting evidence in the current PolarNexus knowledge repository "
                    "to answer this confidently.")

INTENTS = OrderedDict([
    ("figure", (r"\bfig(ure)?\.?\s*(\d+)", ["Figures"])),
    ("method", (r"method|how (was|were|did).*(measur|collect|stud)|data (used|source)|approach", ["Data and Methods", "Methods", "Programme", "Recommendations"])),
    ("limitation", (r"limitation|caveat|weakness|uncertain|shortcoming", ["Limitations"])),
    ("finding", (r"finding|result|conclu|key factor|factors|what did .* find|discover|main point", ["Key Findings", "Preliminary Findings", "Outcome", "Highlights", "Data Collected", "Key Concepts"])),
    ("implication", (r"implication|impact|why .*matter|significan|relevance|importance", ["Implications and Outreach Relevance", "Significance", "Why It Matters", "Legacy", "Lessons"])),
    ("summary", (r"summar|overview|what is (this|it) about|tl;?dr|gist|abstract", ["Abstract", "Key Findings"])),
    ("student", (r"student|simple|child|kid|school|beginner|plain language|layman|eli5", ["Abstract", "Background", "Key Findings"])),
])

LIST_RE = re.compile(r"\b(which|list|show( me)?|find|what)\b.*\b(expeditions?|datasets?|stations?|resources?|documents?|reports?|media|videos?|images?)\b")
THEMES_RE = re.compile(r"\b(major|main|key)?\s*(research )?(themes|topics|areas)\b")
REGION_WORDS = {"antarctic": "Antarctic", "antarctica": "Antarctic", "arctic": "Arctic", "southern ocean": "Southern Ocean",
                "himalaya": "Himalaya", "himalayan": "Himalaya"}
TYPE_WORDS = {"expedition": "expedition", "dataset": "dataset", "station": "station", "media": "media", "video": "media",
              "image": "media", "document": "document", "report": "document", "resource": None}


@dataclass
class Evidence:
    n: int
    chunk: DocumentChunk
    title: str
    slug: str
    url: str
    score: float = 0.0


def detect_intent(question: str) -> tuple[str | None, list[str], str | None]:
    q = question.lower()
    for name, (pattern, sections) in INTENTS.items():
        m = re.search(pattern, q)
        if m:
            fig = m.group(2) if name == "figure" else None
            return name, sections, fig
    return None, [], None


def _known_term_ratio(db: Session, question: str) -> float:
    terms = content_terms(question)
    if not terms:
        return 0.0
    df = bm25_index(db)["df"]
    known = sum(1 for t in terms if df.get(stem(t), 0) > 0)
    return known / len(terms)


def _source_entry(cat: Catalog, ev: Evidence) -> dict:
    c = ev.chunk
    return {
        "n": ev.n, "chunk_id": c.id, "resource_type": c.resource_type, "resource_id": c.resource_id,
        "slug": ev.slug, "title": ev.title, "url": ev.url, "section": c.section, "page": c.page,
        "snippet": c.text, "score": round(ev.score, 4),
        "kind": (cat.card(c.resource_type, c.resource_id) or {}).get("kind", c.resource_type),
        "is_demo": (cat.card(c.resource_type, c.resource_id) or {}).get("is_demo", True),
    }


def _number_sources(cat: Catalog, chunks: list[DocumentChunk], scores: dict[int, float] | None = None) -> list[Evidence]:
    out = []
    for c in chunks:
        card = cat.card(c.resource_type, c.resource_id)
        if not card:
            continue  # resource not visible to this user
        out.append(Evidence(n=len(out) + 1, chunk=c, title=card["title"], slug=card["slug"], url=card["url"],
                            score=(scores or {}).get(c.id, 0.0)))
    return out


def _related(cat: Catalog, evidence: list[Evidence], hits: list[ChunkHit], limit: int = 6) -> list[dict]:
    seen = {(e.chunk.resource_type, e.chunk.resource_id) for e in evidence}
    out: list[dict] = []
    for e in evidence:
        for r in cat.related(e.chunk.resource_type, e.chunk.resource_id):
            key = (r["type"], r["id"])
            if key not in seen and r["type"] != "researcher":
                seen.add(key)
                out.append(r)
    for h in hits:
        key = (h.chunk.resource_type, h.chunk.resource_id)
        c = cat.card(*key)
        if c and key not in seen:
            seen.add(key)
            out.append(c)
    slim = [{k: r[k] for k in ("type", "id", "slug", "title", "kind", "region", "year", "url", "summary")} for r in out]
    return slim[:limit]


def _pick_sentences(question: str, evidence: list[Evidence], intent: str | None, max_sentences: int = 5,
                    per_source: int = 2) -> list[tuple[str, int]]:
    qst = stems(question)
    cands = []
    for e in evidence:
        for pos, s in enumerate(split_sentences(e.chunk.text)):
            if len(s) < 35 or len(s.split()) < 7:
                continue
            if intent != "figure" and re.match(r"^Figure \d", s):
                continue
            sst = stems(s)
            overlap = len(qst & sst) / max(1, len(qst)) if qst else 0
            score = overlap + 0.25 / e.n + (0.15 if pos == 0 else 0)
            if intent in {"finding", "method", "limitation", "implication", "summary", "student"}:
                score += 0.3  # section already chosen by intent; prefer coverage of the section
            cands.append((score, e.n, pos, s, sst))
    cands.sort(key=lambda x: -x[0])
    chosen: list[tuple[float, int, int, str]] = []
    count: Counter = Counter()
    for score, n, pos, s, sst in cands:
        if count[n] >= per_source:
            continue
        if any(len(sst & stems(c[3])) / max(1, len(sst | stems(c[3]))) > 0.55 for c in chosen):
            continue
        chosen.append((score, n, pos, s))
        count[n] += 1
        if len(chosen) >= max_sentences:
            break
    chosen.sort(key=lambda x: (x[1], x[2]))
    return [(s, n) for _, n, _, s in chosen]


def _compose_extractive(question: str, evidence: list[Evidence], intent: str | None, doc_title: str | None) -> str:
    focused = intent in {"finding", "method", "limitation", "summary"}
    sentences = _pick_sentences(question, evidence, intent, max_sentences=7 if focused else 5,
                                per_source=5 if focused and doc_title else 2)
    if not sentences:
        return ""
    used: set[str] = set()
    student = intent == "student"
    lead = (f"According to *{doc_title}*" if doc_title else "Based on the PolarNexus repository")
    if intent == "method":
        lead += ", the methodology is described as follows:"
    elif intent == "limitation":
        lead += ", the following limitations are noted:"
    elif intent == "finding":
        lead += ", the key findings are:"
    elif student:
        lead = "**In simple terms**" + (f" — from *{doc_title}*:" if doc_title else ":")
    else:
        lead += ":"
    if intent in {"finding", "limitation", "method"} or len(sentences) >= 4:
        body = "\n".join(f"- {simplify(s, used) if student else s} [{n}]" for s, n in sentences)
    else:
        body = " ".join(f"{simplify(s, used) if student else s} [{n}]" for s, n in sentences)
    out = f"{lead}\n\n{body}"
    if student:
        glossary = glossary_for(" ".join(s for s, _ in sentences))
        if glossary:
            out += "\n\n**Words to know**\n" + "\n".join(f"- {g}" for g in glossary)
    return out


def _llm_answer(question: str, evidence: list[Evidence], doc_title: str | None, intent: str | None) -> str | None:
    llm = get_llm()
    if not llm:
        return None
    blocks = "\n\n".join(f"[{e.n}] {e.title} — {e.chunk.section}\n{e.chunk.text}" for e in evidence)
    audience = ("Write for a school student: short sentences, explain technical words." if intent == "student"
                else "Write for an educated non-specialist.")
    system = (
        "You are PolarNexus AI, an evidence-grounded assistant for a polar-science knowledge repository. "
        "Answer ONLY from the numbered evidence passages provided. Cite every factual sentence with the passage "
        "number in square brackets, e.g. [1] or [2][3]. Never cite a number that is not in the evidence. Do not add "
        "statistics, names or claims that are not in the evidence. Use cautious wording when the evidence is cautious. "
        "If the evidence does not contain the answer, reply exactly: INSUFFICIENT_EVIDENCE. " + audience
    )
    scope = f"The user is asking about the document '{doc_title}'. " if doc_title else ""
    user = f"{scope}Question: {question}\n\nEvidence passages:\n{blocks}\n\nAnswer (concise, with citations):"
    return llm.complete(system, user, max_tokens=650)


def _validate_citations(answer: str, evidence: list[Evidence]) -> tuple[str, set[int]]:
    valid = {e.n for e in evidence}
    cited: set[int] = set()

    def repl(m):
        n = int(m.group(1))
        if n in valid:
            cited.add(n)
            return m.group(0)
        return ""  # drop any citation that does not map to retrieved evidence

    cleaned = re.sub(r"\[(\d+)\]", repl, answer)
    return cleaned, cited


def _list_answer(db: Session, cat: Catalog, question: str) -> dict | None:
    q = question.lower()
    m = LIST_RE.search(q)
    if not m:
        return None
    noun = m.group(3).rstrip("s")
    rtype = TYPE_WORDS.get(noun)
    region = next((v for k, v in REGION_WORDS.items() if k in q), None)
    subject = re.sub(r"\b(which|list|show|me|find|what|expeditions?|datasets?|stations?|resources?|documents?|reports?|"
                     r"media|videos?|images?|studied|study|related|to|about|on|research|have|has|are|were|in|the|of)\b", " ", q)
    if not content_terms(subject) and not region:
        return None
    r = retrieve(db, question, mode="hybrid", k=80)
    seen, picked = set(), []
    subj_stems = stems(subject)
    for h in r.hits:
        key = (h.chunk.resource_type, h.chunk.resource_id)
        if key in seen or (rtype and h.chunk.resource_type != rtype):
            continue
        card = cat.card(*key)
        if not card or (region and card["region"] != region):
            continue
        if subj_stems and not (subj_stems & stems(h.chunk.text + " " + " ".join(card["topics"]))):
            continue
        seen.add(key)
        picked.append((h, card))
        if len(picked) >= 6:
            break
    if not picked:
        return None
    evidence = _number_sources(cat, [h.chunk for h, _ in picked], {h.chunk.id: h.score for h, _ in picked})
    label = {"expedition": "expeditions", "dataset": "datasets", "station": "stations", "media": "media items",
             "document": "documents"}.get(rtype or "", "resources")
    lines = []
    for e, (_, card) in zip(evidence, picked):
        meta = " · ".join(str(x) for x in (card["kind"], card["region"], card["year"]) if x)
        sents = [x for x in split_sentences(e.chunk.text) if not x.startswith(card["title"])]
        first = sents[0] if sents else ""
        lines.append(f"- **{card['title']}** ({meta}) — {first} [{e.n}]")
    answer = f"The repository contains these {label} matching your question:\n\n" + "\n".join(lines)
    return {"answer": answer, "evidence": evidence, "hits": r.hits}


def _themes_answer(cat: Catalog, question: str) -> dict | None:
    q = question.lower()
    if not THEMES_RE.search(q):
        return None
    region = next((v for k, v in REGION_WORDS.items() if k in q), None)
    cards = [c for c in cat.cards.values() if c["type"] in {"document", "dataset", "expedition"}
             and (not region or c["region"] == region)]
    counts = Counter(t for c in cards for t in c["topics"])
    if not counts:
        return None
    return {"themes": counts.most_common(8), "region": region, "cards": cards}


def ask(db: Session, user: User | None, question: str, document_slug: str | None = None,
        mode: str = "hybrid") -> dict:
    question = question.strip()
    cat = build_catalog(db, user)
    doc: Document | None = None
    if document_slug:
        doc = db.scalar(select(Document).where(Document.slug == document_slug))
        if not doc or not cat.card("document", doc.id):
            doc = None
    intent, intent_sections, fig = detect_intent(question)
    result: dict = {"question": question, "document": None, "intent": intent}
    if doc:
        result["document"] = {"slug": doc.slug, "title": doc.title, "url": f"/resources/{doc.slug}"}

    evidence: list[Evidence] = []
    hits: list[ChunkHit] = []
    answer_text = ""
    gen_mode = "extractive"
    notice = ""

    # ---- 1. Structured questions answered from repository metadata (global scope only)
    if not doc:
        themes = _themes_answer(cat, question)
        if themes:
            reps, used_ids = [], set()
            for name, _ in themes["themes"][:6]:
                pool = [c for c in themes["cards"] if name in c["topics"]]
                best = max((c for c in pool if (c["type"], c["id"]) not in used_ids), key=lambda c: c["views"], default=None) \
                    or max(pool, key=lambda c: c["views"], default=None)
                if best:
                    used_ids.add((best["type"], best["id"]))
                    ch = db.scalar(select(DocumentChunk).where(DocumentChunk.resource_type == best["type"],
                                                               DocumentChunk.resource_id == best["id"])
                                   .order_by(DocumentChunk.chunk_index))
                    if ch:
                        reps.append((name, ch))
            evidence = _number_sources(cat, [c for _, c in reps])
            where = f" for the {themes['region']}" if themes["region"] else ""
            lines = [f"- **{name}** — {sum(1 for c in themes['cards'] if name in c['topics'])} linked resources, e.g. "
                     f"*{e.title}* [{e.n}]" for (name, _), e in zip(reps, evidence)]
            answer_text = (f"Across the repository{where}, the most represented research themes (by number of linked "
                           f"documents, datasets and expeditions) are:\n\n" + "\n".join(lines))
            gen_mode = "metadata"
        else:
            listed = _list_answer(db, cat, question)
            if listed:
                evidence, hits, answer_text, gen_mode = listed["evidence"], listed["hits"], listed["answer"], "metadata"

    # ---- 2. Retrieval-augmented answer
    if not answer_text:
        if doc and intent == "figure":
            chunks = [c for c in doc.chunks if fig and re.search(rf"\bFigure {fig}\b", c.text)]
            if chunks:
                evidence = _number_sources(cat, chunks)
                sent = [s for s in split_sentences(chunks[0].text) if re.search(rf"\bFigure {fig}\b", s)]
                answer_text = f"According to *{doc.title}*:\n\n{sent[0]} [1]" if sent else ""
            else:
                answer_text = ""
                notice = f"The indexed text of this document does not describe Figure {fig}."
        else:
            r = retrieve(db, question, mode=mode, k=24, document_id=doc.id if doc else None)
            hits = r.hits
            notice = r.notice
            chosen: list[DocumentChunk] = []
            if doc and intent_sections:
                chosen = [c for c in doc.chunks if c.section in intent_sections]
            hits = [h for h in hits if h.chunk.resource_type not in {"researcher", "media"}]
            relevant = [h for h in hits if h.term_coverage >= 0.5 or (h.vector_sim >= 0.3 and h.term_coverage >= 0.25)
                        or (doc is not None and h.term_coverage >= 0.25)]
            intent_matched = bool(chosen)
            for h in relevant:
                if intent_matched:
                    break  # document question answered from its dedicated section(s)
                if h.chunk not in chosen and len(chosen) < 6:
                    chosen.append(h.chunk)
            if not doc and _known_term_ratio(db, question) < 0.4:
                chosen = []  # mostly out-of-domain vocabulary
            scores = {h.chunk.id: h.score for h in hits}
            evidence = _number_sources(cat, chosen[:6], scores)

            if evidence:
                curated = None if get_llm() else match_curated(question, doc.slug if doc else None)
                llm_text = None
                if not curated:
                    try:
                        llm_text = _llm_answer(question, evidence, doc.title if doc else None, intent)
                    except LLMUnavailable:
                        notice = "The AI model is temporarily unavailable — showing an extractive answer built from repository passages."
                if curated:
                    ev_chunks = []
                    for slug, section in curated["sources"]:
                        ch = db.scalar(select(DocumentChunk).join(Document, Document.id == DocumentChunk.document_id)
                                       .where(Document.slug == slug, DocumentChunk.section == section)
                                       .order_by(DocumentChunk.chunk_index))
                        if ch:
                            ev_chunks.append(ch)
                    if len(ev_chunks) == len(curated["sources"]):
                        evidence = _number_sources(cat, ev_chunks, scores)
                        answer_text, gen_mode = curated["answer"], "curated_demo"
                if not answer_text and llm_text:
                    if "INSUFFICIENT_EVIDENCE" in llm_text:
                        evidence, answer_text = [], ""
                    else:
                        answer_text, gen_mode = llm_text, "llm"
                if not answer_text and evidence:
                    answer_text = _compose_extractive(question, evidence, intent, doc.title if doc else None)
                    gen_mode = "extractive"

    # ---- 3. Validate citations and decide evidence status
    if answer_text:
        answer_text, cited = _validate_citations(answer_text, evidence)
        if gen_mode == "llm" and not cited:
            answer_text, evidence = "", []
        else:
            if cited:
                evidence = [e for e in evidence if e.n in cited]
                remap = {e.n: i + 1 for i, e in enumerate(evidence)}
                answer_text = re.sub(r"\[(\d+)\]", lambda m: f"[{remap.get(int(m.group(1)), m.group(1))}]", answer_text)
                for e in evidence:
                    e.n = remap[e.n]
    distinct = {(e.chunk.resource_type, e.chunk.resource_id) for e in evidence}
    missing: list[str] = []
    if answer_text and evidence and gen_mode in {"extractive", "llm"} and not (doc and intent_sections):
        ev_stems = set().union(*(stems(e.chunk.text + " " + e.title) for e in evidence))
        missing = [t for t in content_terms(question) if stem(t) not in ev_stems]
    if not answer_text or not evidence:
        status = "insufficient"
    elif missing:
        status = "limited"
        notice = (notice + " " if notice else "") + "The retrieved passages do not mention: " + ", ".join(missing) + \
            ". Treat this answer as partial."
    elif len(distinct) >= 2 or len(evidence) >= 3 or (doc and (len(evidence) >= 2 or (intent_sections and any(
            e.chunk.section in intent_sections for e in evidence)))):
        status = "strong"
    else:
        status = "limited"

    related = _related(cat, evidence, hits)
    if status == "insufficient":
        gen_mode = "insufficient"
        suggestions = [f"Search the repository for “{' '.join(content_terms(question)[:4])}”" if content_terms(question) else "Browse the Explore page"]
        if doc:
            suggestions.append("Ask the question across the whole repository instead of this document")
        answer_text = INSUFFICIENT_MSG + (f" {notice}" if notice and doc else "")
        result.update(suggestions=suggestions)

    labels = {
        "llm": "Generated by the configured language model from retrieved passages",
        "extractive": "Extractive answer — sentences quoted from retrieved passages (no LLM configured)",
        "curated_demo": "Demo response — prepared in advance for the demonstration; citations link to real repository passages",
        "metadata": "Answer assembled from repository metadata and linked records",
        "insufficient": "Insufficient evidence",
    }
    evidence_labels = {"strong": "Strong repository evidence", "limited": "Limited repository evidence",
                       "insufficient": "Insufficient repository evidence"}
    sources = [_source_entry(cat, e) for e in evidence]
    result.update(
        answer=answer_text, mode=gen_mode, mode_label=labels[gen_mode], evidence_status=status,
        evidence_label=evidence_labels[status], sources=sources, related=related, notice=notice,
        retrieval={"mode": mode, "passages_considered": max(len(hits), len(sources)), "passages_used": len(sources)},
    )
    q = AIQuery(user_id=user.id if user else None, question=question[:2000], document_id=doc.id if doc else None,
                mode=gen_mode, evidence_status=status, answer=answer_text[:8000],
                sources=[{"n": s["n"], "slug": s["slug"], "section": s["section"]} for s in sources])
    db.add(q)
    db.commit()
    result["query_id"] = q.id
    return result
