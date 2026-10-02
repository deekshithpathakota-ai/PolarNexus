"""seed_demo_data — (re)populates every table with the PolarNexus prototype demonstration corpus.

Usage:  python -m app.seed.seed_demo_data            # reset + seed
        python -m app.seed.seed_demo_data --if-empty # seed only when the database has no users
"""
from __future__ import annotations

import logging
import random
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import ROLE_INFO, ROLE_PERMISSIONS, hash_password
from app.core.config import settings
from app.core.database import Base, SessionLocal, detect_vector_backend, engine
from app.models import (
    AIQuery,
    AnalyticsEvent,
    AuditLog,
    Dataset,
    DatasetRecord,
    Document,
    Expedition,
    IngestionJob,
    Media,
    Notification,
    Researcher,
    ResourceLink,
    ResourceTopic,
    Review,
    Role,
    SavedItem,
    SearchLog,
    Station,
    Topic,
    User,
)
from app.rag.indexer import ensure_fulltext_index, reindex_all
from app.seed.datasets_media import DATASETS, MEDIA, SYNTH_LICENSE, SYNTH_SOURCE
from app.seed.documents import DEMO_SOURCE, DOCS, FLAGSHIP
from app.seed.entities import EXPEDITIONS, RESEARCHERS, STATIONS, TOPICS

log = logging.getLogger("polarnexus.seed")
NOW = datetime.now(timezone.utc)

TOPIC_ALIASES = {
    "Polar Logistics": "Logistics & Engineering", "Marine Ecosystems": "Krill & Marine Ecosystems",
}

DEMO_USERS = [
    ("public@polarnexus.demo", "Demo Visitor", "public", "Member of the public"),
    ("researcher@polarnexus.demo", "Dr. Ananya Rao", "researcher", "Aurora Institute of Polar Studies (demo)"),
    ("editor@polarnexus.demo", "Meghna Kulkarni", "editor", "Outreach & Communications (demo)"),
    ("admin@polarnexus.demo", "Platform Administrator", "admin", "PolarNexus (demo)"),
    ("vikram.menon@polarnexus.demo", "Dr. Vikram Menon", "researcher", "Konkan Ocean Sciences Institute (demo)"),
    ("meera.iyer@polarnexus.demo", "Dr. Meera Iyer", "researcher", "Deccan Centre for Atmospheric Research (demo)"),
    ("arjun.desai@polarnexus.demo", "Dr. Arjun Desai", "researcher", "Himalayan Cryosphere Laboratory (demo)"),
    ("lakshmi.s@polarnexus.demo", "Dr. Lakshmi Subramanian", "editor", "Aurora Institute of Polar Studies (demo)"),
    ("teacher.goa@polarnexus.demo", "Sunita Fernandes", "public", "School teacher (demo)"),
    ("student.hyd@polarnexus.demo", "Rahul Varma", "public", "University student (demo)"),
]


def ago(days: float, hours: float = 0) -> datetime:
    return NOW - timedelta(days=days, hours=hours)


def compose_content(abstract: str, sections: list[tuple]) -> str:
    lines = ["[[page 1]]", "## Abstract", abstract, ""]
    for i, sec in enumerate(sections):
        if len(sec) == 3:
            heading, page, text = sec
        else:
            heading, text = sec
            page = i + 1 if i < 2 else 2 + (i - 1) // 2
        lines += [f"[[page {page}]]", f"## {heading}", text, ""]
    return "\n".join(lines)


def reset_schema() -> None:
    from sqlalchemy import text

    from app.core.migrations import migrate
    detect_vector_backend()
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))
    Base.metadata.create_all(engine)
    migrate(engine)


def seed(db: Session) -> dict:
    rnd = random.Random(7)
    rng = np.random.default_rng(42)

    # ---------- roles & users
    roles = {}
    for name, perms in ROLE_PERMISSIONS.items():
        label, desc = ROLE_INFO[name]
        roles[name] = Role(name=name, label=label, description=desc, permissions=perms)
        db.add(roles[name])
    db.flush()
    pw = hash_password(settings.DEMO_USER_PASSWORD)
    users = {}
    for i, (email, name, role, inst) in enumerate(DEMO_USERS):
        u = User(email=email, name=name, password_hash=pw, role_id=roles[role].id, institution=inst, is_demo=True,
                 created_at=ago(120 - i * 5), last_login=ago(rnd.uniform(0, 20)))
        db.add(u)
        users[email] = u
    db.flush()
    researcher_u, editor_u, admin_u = users["researcher@polarnexus.demo"], users["editor@polarnexus.demo"], users["admin@polarnexus.demo"]

    # ---------- topics
    topics = {}
    for slug, name, cat, desc in TOPICS:
        topics[slug] = Topic(slug=slug, name=name, category=cat, description=desc)
        db.add(topics[slug])
    db.flush()
    topic_by_name = {t.name: t for t in topics.values()}

    def topic_ids_from_names(names):
        out = []
        for n in names:
            t = topic_by_name.get(TOPIC_ALIASES.get(n, n))
            if t:
                out.append(t.id)
        return out

    rt_seen = set()

    def tag(rtype, rid, topic_ids):
        for tid in topic_ids:
            if (rtype, rid, tid) not in rt_seen:
                rt_seen.add((rtype, rid, tid))
                db.add(ResourceTopic(resource_type=rtype, resource_id=rid, topic_id=tid))

    link_seen = set()

    def link(st, sid, tt, tid, rel):
        key = (st, sid, tt, tid, rel)
        if key not in link_seen and sid and tid:
            link_seen.add(key)
            db.add(ResourceLink(source_type=st, source_id=sid, target_type=tt, target_id=tid, relation=rel))

    # ---------- stations, researchers, expeditions
    stations = {}
    for s in STATIONS:
        st = Station(**s, views=rnd.randint(120, 900))
        db.add(st)
        stations[s["slug"]] = st
    researchers = {}
    for slug, name, title, inst, expertise, bio in RESEARCHERS:
        r = Researcher(slug=slug, name=name, title=title, institution=inst + " (demo)", expertise=expertise, bio=bio)
        db.add(r)
        researchers[slug] = r
    expeditions = {}
    for e in EXPEDITIONS:
        data = {k: v for k, v in e.items() if k not in {"stations", "lat", "lon"}}
        ex = Expedition(**data, latitude=e["lat"], longitude=e["lon"], views=rnd.randint(60, 600))
        db.add(ex)
        expeditions[e["slug"]] = ex
    db.flush()
    for s in STATIONS:
        tag("station", stations[s["slug"]].id, topic_ids_from_names(s["themes"]))
    for slug, *_rest in RESEARCHERS:
        tag("researcher", researchers[slug].id, topic_ids_from_names(researchers[slug].expertise))
    for e in EXPEDITIONS:
        ex = expeditions[e["slug"]]
        tag("expedition", ex.id, topic_ids_from_names(e["themes"]))
        for st in e["stations"]:
            link("expedition", ex.id, "station", stations[st].id, "visited")

    # ---------- datasets
    datasets = {}
    for spec in DATASETS:
        recs = spec["gen"](rng)
        ds = Dataset(slug=spec["slug"], title=spec["title"], description=spec["description"], region=spec["region"],
                     data_type=spec["data_type"], temporal_start=spec["start"], temporal_end=spec["end"],
                     spatial_coverage=spec["spatial"],
                     variables=[{"name": n, "unit": u, "description": d} for n, u, d in spec["variables"]],
                     source=SYNTH_SOURCE, format=spec["fmt"], license=SYNTH_LICENSE,
                     size_label=f"{max(1, len(recs) * 90 // 1024)} KB", record_count=len(recs), year=spec["year"],
                     keywords=spec["keywords"], views=rnd.randint(40, 700),
                     created_at=ago(rnd.uniform(30, 300)))
        for t, lat, lon, vals in recs:
            ds.records.append(DatasetRecord(observed_at=t, latitude=lat, longitude=lon, values=vals))
        db.add(ds)
        datasets[spec["slug"]] = ds
    db.flush()
    for spec in DATASETS:
        ds = datasets[spec["slug"]]
        tag("dataset", ds.id, [topics[t].id for t in spec["topics"]])
        for st in spec["stations"]:
            link("dataset", ds.id, "station", stations[st].id, "observed_at")
        for ex in spec["expeditions"]:
            link("dataset", ds.id, "expedition", expeditions[ex].id, "collected_during")

    # ---------- documents
    documents = {}
    all_docs = [FLAGSHIP] + [dict(slug=d[0], title=d[1], doc_type=d[2], region=d[3], year=d[4], authors=d[5],
                                  topics=d[6], stations=d[7], expeditions=d[8], datasets=d[9], abstract=d[10],
                                  sections=d[11], media=[], keywords=[]) for d in DOCS]
    for i, d in enumerate(all_docs):
        inst = researchers[d["authors"][0]].institution if d["authors"] else "PolarNexus demo"
        internal = d["slug"].startswith("internal-")
        doc = Document(slug=d["slug"], title=d["title"], doc_type=d["doc_type"], abstract=d["abstract"],
                       content=compose_content(d["abstract"], d["sections"]),
                       authors=[researchers[a].name for a in d["authors"]], institution=d.get("institution") or inst,
                       region=d["region"], year=d["year"], keywords=d.get("keywords") or [topics[t].name for t in d["topics"][:4]],
                       source=DEMO_SOURCE, file_name=f"{d['slug']}.pdf", page_count=max(2, len(d["sections"]) + 1),
                       status="indexed", visibility="internal" if internal else "public", is_demo=True,
                       views=2400 if i == 0 else rnd.randint(30, 1400), uploaded_by=researcher_u.id if i % 3 == 0 else admin_u.id,
                       created_at=ago(rnd.uniform(5, 360)))
        db.add(doc)
        documents[d["slug"]] = (doc, d)
    db.flush()
    for slug, (doc, d) in documents.items():
        tag("document", doc.id, [topics[t].id for t in d["topics"]])
        for a in d["authors"]:
            link("document", doc.id, "researcher", researchers[a].id, "authored_by")
        for st in d["stations"]:
            link("document", doc.id, "station", stations[st].id, "conducted_at")
        for ex in d["expeditions"]:
            link("document", doc.id, "expedition", expeditions[ex].id, "from_expedition")
            for a in d["authors"]:
                link("researcher", researchers[a].id, "expedition", expeditions[ex].id, "participated_in")
        for ds in d["datasets"]:
            link("document", doc.id, "dataset", datasets[ds].id, "uses_dataset")
            for a in d["authors"]:
                link("researcher", researchers[a].id, "dataset", datasets[ds].id, "contributed")

    # ---------- media
    media = {}
    for slug, title, mtype, cat, region, year, scene, tags, desc, links in MEDIA:
        m = Media(slug=slug, title=title, description=desc, media_type=mtype, category=cat, region=region, year=year,
                  credit="PolarNexus prototype artwork (original, generated)",
                  license="Original prototype illustration — placeholder for institutional media",
                  tags=tags, scene=scene, duration="2:10" if mtype == "video" else "",
                  views=rnd.randint(20, 900), created_at=ago(rnd.uniform(5, 300)))
        db.add(m)
        media[slug] = (m, links)
    db.flush()
    for slug, (m, links) in media.items():
        tids: list[int] = []
        for dslug in links.get("documents", []):
            doc, d = documents[dslug]
            link("media", m.id, "document", doc.id, "illustrates")
            tids += [topics[t].id for t in d["topics"][:2]]
        for st in links.get("stations", []):
            link("media", m.id, "station", stations[st].id, "depicts")
            tids += topic_ids_from_names(stations[st].themes[:1])
        for ex in links.get("expeditions", []):
            link("media", m.id, "expedition", expeditions[ex].id, "captured_during")
        if m.media_type == "infographic":
            tids.append(topics["science-education"].id)
        tag("media", m.id, list(dict.fromkeys(tids)))
    db.commit()

    # ---------- v2: institutional activities + media map positions (linked to the records above)
    from app.seed.extensions import index_new_passages, link_media_coordinates, seed_activities
    n_activities = seed_activities(db)
    link_media_coordinates(db)

    # ---------- search & semantic index
    idx = reindex_all(db)
    ensure_fulltext_index(db)

    # ---------- outreach workflow examples (generated with the real generator + evidence check)
    from app.content.generator import create_draft

    def make(fmt, rtype, slug, status, by, days, comment="", channels=None):
        c = create_draft(db, by, fmt, rtype, slug)
        c.is_demo = True
        c.created_at = ago(days)
        c.reviews.append(Review(reviewer_id=by.id, reviewer_name=by.name, action="created", comment="Draft generated", created_at=ago(days)))
        if status in {"under_review", "approved", "published", "changes_requested", "rejected"}:
            c.submitted_at = ago(days - 0.2)
            c.reviews.append(Review(reviewer_id=by.id, reviewer_name=by.name, action="submitted", comment="Submitted for editorial review", created_at=ago(days - 0.2)))
        if status in {"approved", "published"}:
            c.reviewer_id, c.approved_at = editor_u.id, ago(days - 1)
            c.reviews.append(Review(reviewer_id=editor_u.id, reviewer_name=editor_u.name, action="approved",
                                    comment=comment or "Checked against sources. Approved.", created_at=ago(days - 1)))
        if status == "published":
            c.published_at, c.channels = ago(days - 1.2), channels or ["website"]
            c.reviews.append(Review(reviewer_id=editor_u.id, reviewer_name=editor_u.name, action="published",
                                    comment="Published to " + ", ".join(c.channels), created_at=ago(days - 1.2)))
        if status in {"changes_requested", "rejected"}:
            c.reviewer_id = editor_u.id
            c.reviews.append(Review(reviewer_id=editor_u.id, reviewer_name=editor_u.name, action=status,
                                    comment=comment, created_at=ago(days - 0.8)))
        c.status = status
        return c

    make("website", "document", "antarctic-sea-ice-variability-study", "published", researcher_u, 12, channels=["website", "linkedin"])
    make("linkedin", "document", "southern-ocean-carbon-dynamics", "approved", users["vikram.menon@polarnexus.demo"], 6)
    make("instagram", "document", "antarctic-ozone-hole-seasonal-monitoring", "under_review", researcher_u, 2)
    make("public", "document", "polar-microbiology-research-report", "changes_requested", researcher_u, 4,
         "Please simplify the second paragraph and keep the caveat about summer-only sampling.")
    make("media", "document", "himalayan-glacier-mass-balance", "published", users["arjun.desai@polarnexus.demo"], 20, channels=["website"])
    make("student", "document", "how-sea-ice-changes-explainer", "published", users["lakshmi.s@polarnexus.demo"], 30, channels=["website"])
    make("website", "dataset", "polar-atmospheric-observations", "draft", users["meera.iyer@polarnexus.demo"], 1)
    make("linkedin", "document", "arctic-atmospheric-aerosol-observations", "rejected", users["meera.iyer@polarnexus.demo"], 9,
         "Superseded by the updated aerosol highlight; please regenerate after the internal draft is reviewed.")
    make("public", "topic", "stratospheric-ozone", "under_review", users["lakshmi.s@polarnexus.demo"], 1.5)
    db.commit()
    index_new_passages(db)  # published outreach becomes discoverable in unified search

    # ---------- telemetry history (prototype demonstration analytics)
    popular = sorted(documents.values(), key=lambda x: -x[0].views)
    weights = [x[0].views for x in popular]
    queries = ["Antarctic sea ice", "Maitri station", "Arctic expeditions", "sea-ice research", "polar atmospheric studies",
               "Southern Ocean carbon", "ozone hole", "Himalayan glaciers", "krill", "Bharati", "aurora", "ice core",
               "black carbon Arctic", "katabatic winds", "microbial mats", "Kongsfjorden", "permafrost Himalaya"]
    qweights = [30, 18, 14, 12, 10, 9, 9, 8, 6, 6, 6, 5, 4, 3, 3, 3, 2]
    for day in range(90):
        growth = 0.55 + day / 120
        n_events = int(rnd.gauss(26, 6) * (1.6 - growth / 2)) if day > 0 else 30
        for _ in range(max(5, n_events)):
            ts = ago(day, rnd.uniform(0, 23))
            r = rnd.random()
            if r < 0.55:
                doc = rnd.choices(popular, weights=weights)[0][0]
                db.add(AnalyticsEvent(event_type="view", resource_type="document", resource_id=doc.id, created_at=ts))
            elif r < 0.68:
                ds = rnd.choice(list(datasets.values()))
                db.add(AnalyticsEvent(event_type="view", resource_type="dataset", resource_id=ds.id, created_at=ts))
            elif r < 0.78:
                m = rnd.choice(list(media.values()))[0]
                db.add(AnalyticsEvent(event_type="view", resource_type="media", resource_id=m.id, created_at=ts))
            elif r < 0.92:
                q = rnd.choices(queries, weights=qweights)[0]
                mode = rnd.choice(["hybrid", "hybrid", "hybrid", "keyword", "semantic"])
                db.add(SearchLog(query=q, mode=mode, result_count=rnd.randint(3, 25), created_at=ts))
                db.add(AnalyticsEvent(event_type="search", meta={"query": q}, created_at=ts))
            else:
                db.add(AnalyticsEvent(event_type="ai_question", created_at=ts))
        if day % 6 == 0:
            db.add(AnalyticsEvent(event_type="generate", created_at=ago(day, 3)))
        if day % 11 == 0:
            db.add(AnalyticsEvent(event_type="publish", created_at=ago(day, 5)))
    ai_examples = [
        ("What factors influence Antarctic sea-ice variability?", "curated_demo", "strong"),
        ("Which expeditions studied atmospheric science?", "metadata", "strong"),
        ("What are the major research themes in Antarctica?", "metadata", "strong"),
        ("How does the Southern Ocean absorb carbon?", "extractive", "strong"),
        ("Explain the ozone hole for a student", "extractive", "strong"),
        ("What is the population of penguins at Maitri?", "insufficient", "insufficient"),
        ("Summarize the methodology of the glacier mass balance study", "extractive", "strong"),
        ("Who won the cricket world cup?", "insufficient", "insufficient"),
    ]
    for i in range(70):
        q, mode, status = ai_examples[i % len(ai_examples)]
        db.add(AIQuery(question=q, mode=mode, evidence_status=status, answer="(historical demo record)",
                       sources=[], feedback=rnd.choice(["", "", "up", "up", "down"]), created_at=ago(rnd.uniform(0, 88))))

    # ---------- audit history
    actions = [("login", "user", ""), ("upload", "document", "antarctic-cryosphere-monitoring-report"),
               ("ai_generate", "content", ""), ("content_submit", "content", ""), ("content_approve", "content", ""),
               ("content_publish", "content", ""), ("metadata_edit", "dataset", "antarctic-sea-ice-observations"),
               ("role_change", "user", "lakshmi.s@polarnexus.demo"), ("content_reject", "content", ""),
               ("reindex", "repository", "")]
    actors = [researcher_u, editor_u, admin_u, users["vikram.menon@polarnexus.demo"], users["lakshmi.s@polarnexus.demo"]]
    for i in range(90):
        act, rtype, rid = rnd.choice(actions)
        u = admin_u if act in {"role_change", "reindex"} else editor_u if act in {"content_approve", "content_publish", "content_reject"} else rnd.choice(actors)
        db.add(AuditLog(user_id=u.id, user_email=u.email, action=act, resource_type=rtype, resource_id=rid or str(rnd.randint(1, 9)),
                        detail="Historical demo record", status="failure" if (act == "login" and rnd.random() < 0.08) else "success",
                        created_at=ago(rnd.uniform(0, 85))))

    # ---------- ingestion jobs, notifications, saved items
    flagship_doc = documents["antarctic-sea-ice-variability-study"][0]
    steps = [{"key": k, "label": l, "status": "done", "detail": d} for k, l, d in [
        ("upload", "Upload document", "File received"), ("validate", "Validate file", "PDF, 0.4 MB"),
        ("extract", "Extract text", "7 pages"), ("metadata", "Extract metadata", "Title, year, region, keywords"),
        ("chunk", "Create document chunks", "7 passages"), ("embed", "Generate embeddings", idx["embedding_model"]),
        ("store", "Store vectors", idx["vector_backend"]), ("index", "Index document", "Full-text + vector"),
        ("ready", "Mark repository status", "Indexed")]]
    db.add(IngestionJob(document_id=flagship_doc.id, file_name="antarctic-sea-ice-variability-study.pdf", status="completed",
                        steps=steps, created_by=researcher_u.id, created_at=ago(40)))
    for title, body, link_, kind, uid, role, d in [
        ("Content awaiting review", "Instagram caption on the Antarctic ozone hole was submitted for review.", "/review", "review", None, "editor", 2),
        ("Content awaiting review", "Public explainer on stratospheric ozone was submitted for review.", "/review", "review", None, "editor", 1.5),
        ("Changes requested", "An editor requested changes to your public explainer on Schirmacher lake microbes.", "/studio", "warning", researcher_u.id, "", 3.2),
        ("Content published", "Your research highlight on Antarctic sea ice was published to the website feed.", "/outreach", "success", researcher_u.id, "", 10.8),
        ("Document processing completed", "Antarctic Cryosphere Monitoring Report is indexed and searchable.", "/resources/antarctic-cryosphere-monitoring-report", "success", researcher_u.id, "", 6),
        ("New resource indexed", "Polar Data Management and Metadata Guidelines was added to the repository.", "/resources/polar-data-management-guidelines", "info", None, "admin", 4),
        ("Index rebuilt", f"Search index rebuilt: {idx['chunks']} passages, {idx['embedding_model']}.", "/admin/health", "info", None, "admin", 0.1),
    ]:
        db.add(Notification(title=title, body=body, link=link_, kind=kind, user_id=uid, role=role, created_at=ago(d)))
    db.add(SavedItem(user_id=researcher_u.id, item_type="document", item_slug="antarctic-sea-ice-variability-study",
                     label="Antarctic Sea Ice Variability Study"))
    db.add(SavedItem(user_id=researcher_u.id, item_type="dataset", item_slug="antarctic-sea-ice-observations",
                     label="Antarctic Sea Ice Observations"))
    db.add(SavedItem(user_id=researcher_u.id, item_type="search", item_slug="", label="Southern Ocean · Hybrid",
                     query={"q": "Southern Ocean", "mode": "hybrid"}))
    db.commit()

    from app.services.provenance import ensure_all
    ensure_all(db)

    from app.seed.v3 import seed_v3  # real public-source records + labelled v3 demonstration data
    v3 = seed_v3(db)

    counts = {name: db.scalar(select(func.count()).select_from(model)) for name, model in [
        ("documents", Document), ("datasets", Dataset), ("dataset_records", DatasetRecord), ("media", Media),
        ("expeditions", Expedition), ("stations", Station), ("researchers", Researcher), ("topics", Topic),
        ("users", User), ("links", ResourceLink)]}
    counts.update(index=idx, activities=n_activities, v3=v3)
    return counts


def run(if_empty: bool = False) -> dict | None:
    detect_vector_backend()
    if if_empty:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            if db.scalar(select(func.count()).select_from(User)):
                return None
    reset_schema()
    with SessionLocal() as db:
        return seed(db)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run(if_empty="--if-empty" in sys.argv)
    print("Database already seeded — nothing to do." if result is None else f"Seeded demo data: {result}")
