"""Resource-level search used by Explore, the documents/datasets/media lists and autocomplete."""
from __future__ import annotations

import time
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.models import User
from app.search.hybrid import retrieve
from app.services import provenance as prov
from app.services import visual
from app.services.catalog import Catalog, Filters, apply_filters, build_catalog
from app.utils.text import content_terms, normalize, snippet_around, stem

SORTS = {"relevance", "newest", "oldest", "views", "alphabetical"}
RRF_K = 60
VISUAL_WEIGHT = 1.0       # a visual rank counts like one more ranked list in Reciprocal Rank Fusion
AUTHORITY_BOOST = 1.12    # verified / partner / public-source records get a modest multiplier; demo data never does


def _reasons(card: dict, a: dict, matched: list[str], concepts: list[str], title_hits: int, filters: Filters,
             cat: Catalog) -> list[str]:
    """Plain-language 'why this result matched' — every reason corresponds to a signal actually used."""
    out = []
    if a["kw"] and matched:
        out.append("Keyword match: " + ", ".join(matched[:5]))
    if title_hits:
        out.append("Title match")
    if a["vec"] > 0:
        out.append(f"Semantic similarity ({a['vec']:.2f})")
    if a["visual"]:
        v = a["visual"]
        out.append(f"Visual similarity ({v['similarity']:.2f})" + (f" · relevant frame {v['timestamp']}" if v.get("timestamp") else ""))
    if concepts:
        out.append("Topic match: " + ", ".join(concepts[:3]))
    for label, rtype, slug in (("Station", "station", filters.station), ("Expedition", "expedition", filters.expedition),
                               ("Researcher", "researcher", filters.researcher)):
        if slug and (key := cat.by_slug.get((rtype, slug))) and (c := cat.card(*key)):
            out.append(f"{label} match: {c['title']}")
    v = card.get("verification")
    if card.get("official"):
        out.append("Official source (verified)")
    elif v == "verified":
        out.append("Verified source")
    elif v == "public_source":
        out.append("Public source")
    elif v in prov.DEMO_STATUSES:
        out.append("Demonstration record — no authority boost")
    return out


GROUP_ORDER = ["Documents", "Datasets", "Images", "Videos", "Expeditions", "Stations", "Researchers",
               "Institutional Activities", "Topics", "Outreach Content"]


def resource_group(c: dict) -> str:
    t = c["type"]
    if t == "media":
        return "Videos" if c["extra"].get("media_type") == "video" else "Images"
    return {"document": "Documents", "dataset": "Datasets", "expedition": "Expeditions", "station": "Stations",
            "researcher": "Researchers", "activity": "Institutional Activities", "topic": "Topics",
            "content": "Outreach Content"}.get(t, t.title())


def _facets(cards: list[dict]) -> dict:
    regions = Counter(c["region"] for c in cards if c["region"])
    kinds = Counter(c["kind"] for c in cards)
    topics = Counter(t for c in cards for t in c["topic_slugs"])
    years = [c["year"] for c in cards if c["year"]]
    groups = Counter(resource_group(c) for c in cards)
    verification: Counter = Counter()
    for c in cards:
        if c["type"] == "topic":
            continue
        pseudo = {"verification_status": c.get("verification", "unverified"),
                  "source_type": prov.OFFICIAL_SOURCE_TYPE if c.get("official") else ""}
        for label, pred in prov.FILTERS.items():
            if pred(pseudo):
                verification[label] += 1
    orgs = Counter(c.get("organisation") for c in cards if c.get("organisation"))
    return {
        "regions": dict(regions.most_common()),
        "types": dict(kinds.most_common()),
        "topics": dict(topics.most_common(20)),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "resource_groups": {g: groups[g] for g in GROUP_ORDER if groups.get(g)},
        "verification": {k: verification[k] for k in prov.FILTERS if verification.get(k)},
        "organisations": dict(orgs.most_common(15)),
    }


def search_resources(db: Session, user: User | None, q: str, mode: str, filters: Filters,
                     sort: str = "relevance", page: int = 1, page_size: int = 12,
                     restrict_types: set[str] | None = None, catalog: Catalog | None = None) -> dict:
    t0 = time.perf_counter()
    cat = catalog or build_catalog(db, user)
    q = (q or "").strip()
    notice, mode_used = "", mode
    pool = [c for c in cat.cards.values() if not restrict_types or c["type"] in restrict_types]
    scored: list[dict] = []

    if q:
        r = retrieve(db, q, mode=mode, k=120)
        notice, mode_used = r.notice, r.mode_used
        qterms = content_terms(q)
        qstems = {stem(t) for t in qterms}
        agg: dict[tuple[str, int], dict] = defaultdict(lambda: {"score": 0.0, "hits": [], "vec": 0.0, "kw": False, "visual": None})
        for h in r.hits:
            key = (h.chunk.resource_type, h.chunk.resource_id)
            a = agg[key]
            a["score"] = max(a["score"], h.score) + 0.15 * min(h.score, a["score"])  # reward multiple matching passages
            a["hits"].append(h)
            a["vec"] = max(a["vec"], h.vector_sim)
            a["kw"] = a["kw"] or h.keyword_rank is not None
        # Visual relevance: CLIP text→image similarity over photographs and video key frames (when available)
        if mode in {"semantic", "hybrid"} and (not restrict_types or "media" in restrict_types):
            try:
                vis_hits = visual.search(db, q, k=40)
            except Exception:  # optional subsystem — never break search
                vis_hits = []
            for rank, v in enumerate(vis_hits):
                a = agg[("media", v["media_id"])]
                a["visual"] = v
                a["score"] += VISUAL_WEIGHT / (RRF_K + rank + 1)
        top_vec = max((a["vec"] for a in agg.values()), default=0.0)
        allowed = {(c["type"], c["id"]) for c in pool}
        for key, a in agg.items():
            if key not in allowed:
                continue
            if not a["kw"] and not a["visual"] and a["vec"] < max(0.12, 0.55 * top_vec):
                continue  # weak purely-semantic neighbours are noise
            card = cat.cards[key]
            title_terms = {stem(t) for t in content_terms(card["title"])}
            title_hits = len(qstems & title_terms)
            title_boost = 0.012 * title_hits
            best = max(a["hits"], key=lambda h: h.score) if a["hits"] else None
            matched = sorted({t for h in a["hits"] for t in h.matched_terms})
            concepts = [t for t in card["topics"] if {stem(x) for x in content_terms(t)} & qstems]
            kinds = [k for k, on in (("keyword", a["kw"]), ("semantic", a["vec"] > 0), ("visual", bool(a["visual"]))) if on]
            match_type = " + ".join(kinds)
            authority = AUTHORITY_BOOST if card.get("verification") in prov.AUTHORITATIVE_STATUSES else 1.0
            base = a["score"] + title_boost
            item = {
                **card,
                "score": round(base * authority, 5),
                "matched_terms": matched,
                "matching_concepts": concepts,
                "match_type": match_type,
                "highlight": snippet_around(best.chunk.text, [normalize(t) for t in (matched or qterms)]) if best else card["summary"],
                "matched_section": best.chunk.section if best else "Visual match",
                "match_reasons": _reasons(card, a, matched, concepts, title_hits, filters, cat),
                "score_breakdown": {"text": round(a["score"] - (VISUAL_WEIGHT / RRF_K if a["visual"] else 0), 5),
                                    "title": round(title_boost, 4), "authority_multiplier": authority},
            }
            if a["visual"]:
                v = a["visual"]
                item["visual_match"] = {"similarity": v["similarity"], "timestamp": v["timestamp"],
                                        "frame_seconds": v["frame_seconds"],
                                        "frame_url": f"/api/media/{card['slug']}/frames/{v['frame_index']}" if v["frame_index"] is not None else None}
            scored.append(item)
        if scored:
            mx = max(s["score"] for s in scored)
            for s in scored:
                s["relevance"] = round(s["score"] / mx, 3) if mx else 0
    else:
        scored = [{**c, "score": 0, "relevance": None, "matched_terms": [], "matching_concepts": [],
                   "match_type": "", "highlight": c["summary"], "matched_section": ""} for c in pool]
        if sort == "relevance":
            sort = "views"

    scored = apply_filters(cat, scored, filters)
    sort = sort if sort in SORTS else "relevance"
    if sort == "relevance":
        scored.sort(key=lambda c: -c["score"])
    elif sort == "newest":
        scored.sort(key=lambda c: (-(c["year"] or 0), -c["score"]))
    elif sort == "oldest":
        scored.sort(key=lambda c: ((c["year"] or 9999), -c["score"]))
    elif sort == "views":
        scored.sort(key=lambda c: -c["views"])
    elif sort == "alphabetical":
        scored.sort(key=lambda c: c["title"].lower())

    total = len(scored)
    page = max(1, page)
    page_size = max(1, min(page_size, 1000))
    items = scored[(page - 1) * page_size: page * page_size]
    return {
        "query": q, "mode": mode, "mode_used": mode_used, "notice": notice, "sort": sort,
        "total": total, "page": page, "page_size": page_size,
        "pages": max(1, -(-total // page_size)), "results": items, "facets": _facets(scored),
        "filters": filters.as_dict(), "took_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


SUGGESTED = [
    "Antarctic sea ice", "Maitri station", "Arctic expeditions", "sea-ice research",
    "polar atmospheric studies", "Southern Ocean carbon", "Himalayan glaciers", "Bharati station",
    "Antarctic climate change", "Antarctic atmosphere", "Antarctic oceanography", "Svalbard Kongsfjorden",
    "polar microbiology", "ice core records", "aerosol observations", "krill and phytoplankton",
]


def suggest(cat: Catalog, q: str, limit: int = 8) -> list[dict]:
    qn = normalize(q.strip())
    if not qn:
        return [{"text": s, "kind": "suggested"} for s in SUGGESTED[:limit]]
    out, seen = [], set()

    def push(text: str, kind: str, url: str = ""):
        if text.lower() not in seen:
            seen.add(text.lower())
            out.append({"text": text, "kind": kind, "url": url})

    for s in SUGGESTED:
        if qn in normalize(s):
            push(s, "query")
    for t in cat.topics.values():
        if qn in normalize(t.name):
            push(t.name, "topic", f"/explore?topic={t.slug}")
    for c in sorted(cat.cards.values(), key=lambda c: -c["views"]):
        if qn in normalize(c["title"]):
            push(c["title"], c["type"], c["url"])
        if len(out) >= limit * 2:
            break
    # prefix-extension suggestions ("Antarctic climate" -> "Antarctic climate change")
    first = qn.split()[0] if qn.split() else ""
    if first:
        for s in SUGGESTED:
            if normalize(s).startswith(first):
                push(s, "related")
    return out[:limit]
