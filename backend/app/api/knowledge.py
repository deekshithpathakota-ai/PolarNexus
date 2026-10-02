"""Read APIs for the knowledge repository: resources, datasets, media, expeditions, stations,
researchers, topics, map layers and the relationship graph."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import get_current_user_optional
from app.core.database import get_db
from app.models import (
    Dataset,
    DatasetRecord,
    Document,
    Expedition,
    Media,
    Researcher,
    ResourceTopic,
    Station,
    Topic,
    User,
)
from app.search.service import search_resources
from app.services.audit import track
from app.services.catalog import Catalog, Filters, build_catalog
from app.services.serializers import (
    dataset_out,
    document_out,
    expedition_out,
    media_out,
    researcher_out,
    station_out,
)

router = APIRouter(prefix="/api", tags=["knowledge"])


def parse_filters(region: list[str] | None, type_: list[str] | None, topic: list[str] | None, year_from: int | None,
                  year_to: int | None, station: str | None, expedition: str | None, researcher: str | None,
                  language: str | None, data_type: str | None) -> Filters:
    return Filters(regions=[r for r in (region or []) if r], types=[t for t in (type_ or []) if t],
                   topics=[t for t in (topic or []) if t], year_from=year_from, year_to=year_to, station=station or None,
                   expedition=expedition or None, researcher=researcher or None, language=language or None,
                   data_type=data_type or None)


def _list(db, user, restrict: set[str] | None, q, mode, sort, page, page_size, region, type_, topic, year_from, year_to,
          station, expedition, researcher, language, data_type):
    f = parse_filters(region, type_, topic, year_from, year_to, station, expedition, researcher, language, data_type)
    return search_resources(db, user, q or "", mode, f, sort=sort, page=page, page_size=page_size, restrict_types=restrict)


def _common(q: str | None = Query(None, max_length=300), mode: str = Query("hybrid", pattern="^(hybrid|keyword|semantic)$"),
            sort: str = Query("relevance", pattern="^(relevance|newest|oldest|views|alphabetical)$"),
            page: int = Query(1, ge=1, le=1000), page_size: int = Query(12, ge=1, le=60),
            region: list[str] | None = Query(None), type: list[str] | None = Query(None),
            topic: list[str] | None = Query(None), year_from: int | None = Query(None, ge=1800, le=2100),
            year_to: int | None = Query(None, ge=1800, le=2100), station: str | None = None,
            expedition: str | None = None, researcher: str | None = None, language: str | None = None,
            data_type: str | None = None):
    return dict(q=q, mode=mode, sort=sort, page=page, page_size=page_size, region=region, type_=type, topic=topic,
                year_from=year_from, year_to=year_to, station=station, expedition=expedition, researcher=researcher,
                language=language, data_type=data_type)


def _view(db: Session, obj, rtype: str, user: User | None):
    obj.views = (obj.views or 0) + 1
    track(db, "view", rtype, obj.id, user, commit=False)
    db.commit()


def _related_block(cat: Catalog, rtype: str, rid: int) -> dict:
    groups: dict[str, list] = {"document": [], "dataset": [], "media": [], "expedition": [], "station": [], "researcher": []}
    for r in cat.related(rtype, rid):
        groups.setdefault(r["type"], []).append(r)
    # topic-based "similar" resources (same topics, not already linked)
    card = cat.card(rtype, rid)
    linked = {(r["type"], r["id"]) for v in groups.values() for r in v} | {(rtype, rid)}
    similar = []
    if card:
        mine = set(card["topic_slugs"])
        for c in cat.cards.values():
            if (c["type"], c["id"]) in linked or c["type"] in {"researcher"}:
                continue
            overlap = len(mine & set(c["topic_slugs"]))
            if overlap:
                similar.append((overlap, c["views"], c))
        similar.sort(key=lambda x: (-x[0], -x[1]))
    return {"groups": groups, "similar": [s[2] for s in similar[:6]]}


def _topics(db: Session, rtype: str, rid: int) -> list[dict]:
    rows = db.scalars(select(Topic).join(ResourceTopic, ResourceTopic.topic_id == Topic.id)
                      .where(ResourceTopic.resource_type == rtype, ResourceTopic.resource_id == rid)).all()
    return [{"slug": t.slug, "name": t.name, "category": t.category} for t in rows]


def _get_or_404(db: Session, model, slug: str, label: str):
    obj = db.scalar(select(model).where(model.slug == slug))
    if not obj:
        raise HTTPException(404, f"{label} not found.")
    return obj


# ----------------------------------------------------------------------- resources / documents
@router.get("/resources")
def list_resources(params: dict = Depends(_common), kind: str | None = Query(None, pattern="^(document|dataset|media|expedition|station|researcher)$"),
                   db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    restrict = {kind} if kind else None
    return _list(db, user, restrict, **params)


@router.get("/resources/{slug}")
def get_resource(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    doc = _get_or_404(db, Document, slug, "Resource")
    cat = build_catalog(db, user)
    if not cat.card("document", doc.id):
        raise HTTPException(404, "Resource not found or not available to your role.")
    _view(db, doc, "document", user)
    out = document_out(doc, include_content=True)
    out["topics"] = _topics(db, "document", doc.id)
    out["related"] = _related_block(cat, "document", doc.id)
    out["citation"] = citation_text(doc)
    return out


def citation_text(doc: Document) -> str:
    authors = ", ".join(doc.authors) if doc.authors else doc.institution
    return f"{authors} ({doc.year}). {doc.title}. {doc.institution}. PolarNexus repository record: /resources/{doc.slug}. [{doc.source}]"


@router.get("/resources/{slug}/download")
def download_resource(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    doc = _get_or_404(db, Document, slug, "Resource")
    if not build_catalog(db, user).card("document", doc.id):
        raise HTTPException(404, "Resource not found.")
    track(db, "download", "document", doc.id, user)
    text = f"{doc.title}\n{'=' * len(doc.title)}\n\n{citation_text(doc)}\n\n" + (doc.content or doc.abstract)
    text = text.replace("[[page ", "\n--- page ").replace("]]", " ---")
    return PlainTextResponse(text, headers={"Content-Disposition": f'attachment; filename="{doc.slug}.txt"'})


# ----------------------------------------------------------------------- datasets
@router.get("/datasets")
def list_datasets(params: dict = Depends(_common), db: Session = Depends(get_db),
                  user: User | None = Depends(get_current_user_optional)):
    return _list(db, user, {"dataset"}, **params)


@router.get("/datasets/{slug}")
def get_dataset(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    ds = _get_or_404(db, Dataset, slug, "Dataset")
    cat = build_catalog(db, user)
    if not cat.card("dataset", ds.id):
        raise HTTPException(404, "Dataset not found.")
    _view(db, ds, "dataset", user)
    out = dataset_out(ds)
    out["topics"] = _topics(db, "dataset", ds.id)
    out["related"] = _related_block(cat, "dataset", ds.id)
    return out


@router.get("/datasets/{slug}/records")
def dataset_records(slug: str, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
                    date_from: str | None = None, date_to: str | None = None,
                    variable: str | None = None, min_value: float | None = None, max_value: float | None = None,
                    sort: str = Query("asc", pattern="^(asc|desc)$"), db: Session = Depends(get_db)):
    ds = _get_or_404(db, Dataset, slug, "Dataset")
    rows = _filtered_records(db, ds, date_from, date_to, variable, min_value, max_value)
    if sort == "desc":
        rows = rows[::-1]
    total = len(rows)
    items = rows[(page - 1) * page_size: page * page_size]
    return {"total": total, "page": page, "page_size": page_size, "pages": max(1, -(-total // page_size)),
            "records": [_record_out(r) for r in items]}


def _record_out(r: DatasetRecord) -> dict:
    return {"id": r.id, "observed_at": r.observed_at.isoformat() if r.observed_at else None,
            "latitude": r.latitude, "longitude": r.longitude, **r.values}


def _filtered_records(db, ds, date_from, date_to, variable, min_value, max_value) -> list[DatasetRecord]:
    stmt = select(DatasetRecord).where(DatasetRecord.dataset_id == ds.id).order_by(DatasetRecord.observed_at, DatasetRecord.id)
    try:
        if date_from:
            stmt = stmt.where(DatasetRecord.observed_at >= datetime.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(DatasetRecord.observed_at <= datetime.fromisoformat(date_to))
    except ValueError:
        raise HTTPException(422, "Dates must be in YYYY-MM-DD format.")
    rows = list(db.scalars(stmt))
    if variable and (min_value is not None or max_value is not None):
        def ok(r):
            v = r.values.get(variable)
            if not isinstance(v, (int, float)):
                return False
            return (min_value is None or v >= min_value) and (max_value is None or v <= max_value)
        rows = [r for r in rows if ok(r)]
    return rows


@router.get("/datasets/{slug}/series")
def dataset_series(slug: str, x: str = "observed_at", y: str | None = None, group: str | None = None,
                   date_from: str | None = None, date_to: str | None = None, max_points: int = Query(800, le=3000),
                   db: Session = Depends(get_db)):
    ds = _get_or_404(db, Dataset, slug, "Dataset")
    numeric = [v["name"] for v in ds.variables if v["unit"] not in {"text", "name", "id", "ISO date", "ISO datetime"}
               and v["name"] not in {"latitude", "longitude", "date", "timestamp"}]
    y = y or (numeric[0] if numeric else None)
    if not y:
        raise HTTPException(422, "This dataset has no numeric variables to plot.")
    rows = _filtered_records(db, ds, date_from, date_to, None, None, None)
    step = max(1, len(rows) // max_points)
    pts = []
    for r in rows[::step]:
        xv = r.observed_at.isoformat()[:10] if x == "observed_at" and r.observed_at else r.values.get(x, getattr(r, x, None))
        yv = r.values.get(y)
        if xv is None or not isinstance(yv, (int, float)):
            continue
        pts.append({"x": xv, "y": yv, "group": r.values.get(group) if group else None,
                    "lat": r.latitude, "lon": r.longitude})
    vals = [p["y"] for p in pts]
    stats = {"count": len(vals), "min": min(vals) if vals else None, "max": max(vals) if vals else None,
             "mean": round(sum(vals) / len(vals), 3) if vals else None}
    return {"x": x, "y": y, "numeric_variables": numeric, "points": pts, "stats": stats,
            "unit": next((v["unit"] for v in ds.variables if v["name"] == y), "")}


@router.get("/datasets/{slug}/download")
def download_dataset(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    ds = _get_or_404(db, Dataset, slug, "Dataset")
    track(db, "download", "dataset", ds.id, user)
    rows = db.scalars(select(DatasetRecord).where(DatasetRecord.dataset_id == ds.id).order_by(DatasetRecord.id)).all()
    keys: list[str] = []
    for r in rows:
        for k in r.values:
            if k not in keys:
                keys.append(k)
    buf = io.StringIO()
    buf.write(f"# {ds.title} — {ds.license}. SYNTHETIC DEMONSTRATION VALUES, not observations.\n")
    w = csv.writer(buf)
    w.writerow(["observed_at", "latitude", "longitude", *keys])
    for r in rows:
        w.writerow([r.observed_at.isoformat() if r.observed_at else "", r.latitude, r.longitude, *[r.values.get(k, "") for k in keys]])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{ds.slug}.csv"'})


# ----------------------------------------------------------------------- media
@router.get("/media")
def list_media(params: dict = Depends(_common), category: str | None = None, media_type: str | None = None,
               db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    res = _list(db, user, {"media"}, **{**params, "page": 1, "page_size": 60 * 10})
    items = res["results"]
    if category:
        items = [c for c in items if c["extra"].get("category") == category]
    if media_type:
        items = [c for c in items if c["extra"].get("media_type") == media_type]
    page, size = params["page"], params["page_size"]
    res.update(total=len(items), page=page, page_size=size, pages=max(1, -(-len(items) // size)),
               results=items[(page - 1) * size: page * size])
    cats = db.execute(select(Media.category, func.count()).group_by(Media.category)).all()
    res["categories"] = {c: n for c, n in sorted(cats)}
    return res


@router.get("/media/{slug}")
def get_media(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    m = _get_or_404(db, Media, slug, "Media item")
    cat = build_catalog(db, user)
    _view(db, m, "media", user)
    out = media_out(m)
    out["topics"] = _topics(db, "media", m.id)
    out["related"] = _related_block(cat, "media", m.id)
    return out


# ----------------------------------------------------------------------- expeditions / stations / researchers
@router.get("/expeditions")
def list_expeditions(program: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, le=100),
                     db: Session = Depends(get_db)):
    stmt = select(Expedition).order_by(Expedition.year, Expedition.number)
    if program:
        stmt = stmt.where(Expedition.program == program)
    rows = db.scalars(stmt).all()
    total = len(rows)
    return {"total": total, "page": page, "pages": max(1, -(-total // page_size)),
            "results": [expedition_out(e) for e in rows[(page - 1) * page_size: page * page_size]],
            "programs": sorted({e.program for e in db.scalars(select(Expedition))})}


@router.get("/expeditions/{slug}")
def get_expedition(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    e = _get_or_404(db, Expedition, slug, "Expedition")
    cat = build_catalog(db, user)
    _view(db, e, "expedition", user)
    out = expedition_out(e)
    out["topics"] = _topics(db, "expedition", e.id)
    out["related"] = _related_block(cat, "expedition", e.id)
    return out


@router.get("/stations")
def list_stations(region: str | None = None, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    stmt = select(Station).order_by(Station.verified.desc(), Station.name)
    if region:
        stmt = stmt.where(Station.region == region)
    cat = build_catalog(db, user)
    out = []
    for s in db.scalars(stmt):
        so = station_out(s)
        rel = cat.related("station", s.id)
        so["counts"] = {t: sum(1 for r in rel if r["type"] == t) for t in ("document", "dataset", "expedition", "media")}
        out.append(so)
    return {"total": len(out), "results": out}


@router.get("/stations/{slug}")
def get_station(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    s = _get_or_404(db, Station, slug, "Station")
    cat = build_catalog(db, user)
    _view(db, s, "station", user)
    out = station_out(s)
    out["topics"] = _topics(db, "station", s.id)
    out["related"] = _related_block(cat, "station", s.id)
    return out


@router.get("/researchers")
def list_researchers(page: int = Query(1, ge=1), page_size: int = Query(24, le=60), q: str | None = None,
                     db: Session = Depends(get_db)):
    rows = db.scalars(select(Researcher).order_by(Researcher.name)).all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.name.lower() or any(ql in e.lower() for e in r.expertise)]
    total = len(rows)
    return {"total": total, "page": page, "pages": max(1, -(-total // page_size)),
            "results": [researcher_out(r) for r in rows[(page - 1) * page_size: page * page_size]]}


@router.get("/researchers/{slug}")
def get_researcher(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    r = _get_or_404(db, Researcher, slug, "Researcher")
    cat = build_catalog(db, user)
    out = researcher_out(r)
    out["topics"] = _topics(db, "researcher", r.id)
    out["related"] = _related_block(cat, "researcher", r.id)
    return out


@router.get("/topics")
def list_topics(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(ResourceTopic.topic_id, func.count()).group_by(ResourceTopic.topic_id)).all())
    return {"results": [{"id": t.id, "slug": t.slug, "name": t.name, "category": t.category,
                         "description": t.description, "count": counts.get(t.id, 0)}
                        for t in db.scalars(select(Topic).order_by(Topic.category, Topic.name))]}


# ----------------------------------------------------------------------- map + graph + stats
@router.get("/map")
def map_layers(db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    cat = build_catalog(db, user)
    stations = []
    for s in db.scalars(select(Station)):
        rel = cat.related("station", s.id)
        stations.append({**station_out(s), "topics": [t for t in cat.card("station", s.id)["topics"]] if cat.card("station", s.id) else [],
                         "counts": {t: sum(1 for r in rel if r["type"] == t) for t in ("document", "dataset", "expedition", "media")}})
    expeditions = [{**expedition_out(e), "topics": (cat.card("expedition", e.id) or {}).get("topics", [])}
                   for e in db.scalars(select(Expedition)) if e.latitude is not None]
    datasets = []
    for ds in db.scalars(select(Dataset)):
        first = db.scalar(select(DatasetRecord).where(DatasetRecord.dataset_id == ds.id, DatasetRecord.latitude.is_not(None))
                          .order_by(DatasetRecord.id))
        if first:
            datasets.append({"slug": ds.slug, "title": ds.title, "region": ds.region, "latitude": first.latitude,
                             "longitude": first.longitude, "url": f"/datasets/{ds.slug}", "data_type": ds.data_type,
                             "topics": (cat.card("dataset", ds.id) or {}).get("topics", [])})
    return {"stations": stations, "expeditions": expeditions, "datasets": datasets,
            "topics": sorted({t for c in cat.cards.values() for t in c["topics"]})}


@router.get("/graph/{rtype}/{slug}")
def knowledge_graph(rtype: str, slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    cat = build_catalog(db, user)
    key = cat.by_slug.get((rtype, slug))
    if not key:
        raise HTTPException(404, "Resource not found.")
    nodes = {key: {**cat.cards[key], "depth": 0}}
    edges = []
    for t, i, rel in sorted(cat.links.get(key, set())):
        if (t, i) in cat.cards:
            nodes.setdefault((t, i), {**cat.cards[(t, i)], "depth": 1})
            edges.append({"source": f"{key[0]}:{key[1]}", "target": f"{t}:{i}", "relation": rel})
    for (t, i) in list(nodes):
        if nodes[(t, i)]["depth"] != 1 or t not in {"expedition", "station"}:
            continue
        for t2, i2, rel in sorted(cat.links.get((t, i), set()))[:4]:
            if (t2, i2) in cat.cards and (t2, i2) not in nodes and len(nodes) < 28:
                nodes[(t2, i2)] = {**cat.cards[(t2, i2)], "depth": 2}
                edges.append({"source": f"{t}:{i}", "target": f"{t2}:{i2}", "relation": rel})
    for tname in cat.cards[key]["topics"][:4]:
        tslug = next((tp.slug for tp in cat.topics.values() if tp.name == tname), "")
        tid = f"topic:{tslug}"
        nodes[("topic", tslug)] = {"type": "topic", "id": tslug, "slug": tslug, "title": tname, "kind": "Topic",
                                   "url": f"/explore?topic={tslug}", "depth": 1}
        edges.append({"source": f"{key[0]}:{key[1]}", "target": tid, "relation": "about"})
    slim = [{"key": f"{k[0]}:{k[1]}", "type": v["type"], "title": v["title"], "kind": v["kind"], "url": v["url"],
             "depth": v["depth"]} for k, v in nodes.items()]
    return {"nodes": slim, "edges": edges}


@router.get("/stats")
def public_stats(db: Session = Depends(get_db)):
    def count(model, *where):
        stmt = select(func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return db.scalar(stmt) or 0
    return {
        "documents": count(Document, Document.visibility == "public", Document.status != "archived"),
        "datasets": count(Dataset), "expeditions": count(Expedition), "stations": count(Station),
        "media": count(Media), "topics": count(Topic), "researchers": count(Researcher),
        "dataset_records": count(DatasetRecord),
        "label": "Prototype demonstration repository — counts reflect the demo corpus, not institutional holdings.",
    }
