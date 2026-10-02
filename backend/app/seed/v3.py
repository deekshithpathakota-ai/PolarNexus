"""v3 data: real public-source records, demonstration story/campaign/metrics, version baseline, visual index.

Everything here is *additive* and idempotent. `seed_v3` runs at the end of a full demo seed; `upgrade_v3` runs at
start-up on an existing database and adds only what is missing — nothing is reset, edited or deleted.

Real records (status **Public source**):
* NSIDC Sea Ice Index v4 monthly extent files (Antarctic Feb/Sep, Arctic Sep) — bundled unmodified in
  seed/assets/public and registered through the same CSV ingestion pipeline users get.
* Openly licensed photographs from Wikimedia Commons — licence, author, date and source page as recorded on Commons
  (seed/assets/public/commons_manifest.json); alt text written for accessibility.
* Metadata-only catalogue records for official public web resources (full text not stored; the record links out).

Demonstration records (always labelled): one research story, one outreach campaign, seeded engagement metrics.
"""
from __future__ import annotations

import json
import logging
import random
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Campaign,
    CampaignItem,
    Dataset,
    DatasetUpload,
    Document,
    GeneratedContent,
    Media,
    OutreachEvent,
    Provenance,
    ResearchStory,
    ResourceLink,
    ResourceTopic,
    Station,
    Topic,
)

log = logging.getLogger("polarnexus.seed.v3")
ASSETS = Path(__file__).resolve().parent / "assets" / "public"
NOW = lambda: datetime.now(timezone.utc)  # noqa: E731

NSIDC_LANDING = "https://nsidc.org/data/g02135"
NSIDC_BASE = "https://noaadata.apps.nsidc.org/NOAA/G02135"
NSIDC_NOTE = ("Values are copied unmodified from the NSIDC file. 'observed_at' is derived from the year and mo columns "
              "(first day of the month). Rows from 2025 onwards list source_dataset NSIDC-0803 in the file itself.")
NSIDC_DATASETS = [
    dict(file="S_09_extent_v4.0.csv", slug="nsidc-sea-ice-index-antarctic-september-extent",
         title="Sea Ice Index v4 — Antarctic monthly sea-ice extent and area, September (1979–2026)",
         region="Antarctic", url=f"{NSIDC_BASE}/south/monthly/data/S_09_extent_v4.0.csv",
         description="Monthly Antarctic (Southern Hemisphere) sea-ice extent and area for September of each year, from the "
                     "NSIDC Sea Ice Index, Version 4 (G02135). September is around the Antarctic annual maximum."),
    dict(file="S_02_extent_v4.0.csv", slug="nsidc-sea-ice-index-antarctic-february-extent",
         title="Sea Ice Index v4 — Antarctic monthly sea-ice extent and area, February (1979–2026)",
         region="Antarctic", url=f"{NSIDC_BASE}/south/monthly/data/S_02_extent_v4.0.csv",
         description="Monthly Antarctic (Southern Hemisphere) sea-ice extent and area for February of each year, from the "
                     "NSIDC Sea Ice Index, Version 4 (G02135). February is around the Antarctic annual minimum."),
    dict(file="N_09_extent_v4.0.csv", slug="nsidc-sea-ice-index-arctic-september-extent",
         title="Sea Ice Index v4 — Arctic monthly sea-ice extent and area, September (1979–2026)",
         region="Arctic", url=f"{NSIDC_BASE}/north/monthly/data/N_09_extent_v4.0.csv",
         description="Monthly Arctic (Northern Hemisphere) sea-ice extent and area for September of each year, from the "
                     "NSIDC Sea Ice Index, Version 4 (G02135). September is around the Arctic annual minimum."),
]

PUBLIC_DOCS = [
    dict(slug="indian-antarctic-act-2022", title="The Indian Antarctic Act, 2022", doc_type="Policy / Legislation",
         year=2022, region="Antarctic", publisher="Government of India — India Code",
         url="https://www.indiacode.nic.in/handle/123456789/19581", topics=["environmental-protection"],
         description="Legislation enacted by the Parliament of India in 2022 that regulates Indian activities in Antarctica "
                     "and gives domestic effect to India's obligations under the Antarctic Treaty system."),
    dict(slug="india-arctic-policy-2022", title="India's Arctic Policy: Building a Partnership for Sustainable Development",
         doc_type="Policy / Legislation", year=2022, region="Arctic", publisher="Ministry of Earth Sciences, Government of India",
         url="https://moes.gov.in/sites/default/files/3720English.pdf", topics=["climate-change", "science-education"],
         description="Policy document released by the Ministry of Earth Sciences in 2022 that sets out India's approach to "
                     "the Arctic region, organised around six pillars that include science and research and climate and "
                     "environmental protection."),
    dict(slug="ncpor-official-website", title="National Centre for Polar and Ocean Research (NCPOR) — official website",
         doc_type="Institutional Resource", year=2026, region="India", publisher="NCPOR, Ministry of Earth Sciences",
         url="https://ncpor.res.in/", topics=["polar-logistics", "science-education"],
         description="Official website of the National Centre for Polar and Ocean Research, an autonomous institute of the "
                     "Ministry of Earth Sciences, Government of India, located in Goa. NCPOR coordinates India's Antarctic, "
                     "Arctic, Southern Ocean and Himalayan research programmes."),
    dict(slug="ncpor-himadri-station-page", title="Himadri Station — NCPOR information page", doc_type="Institutional Resource",
         year=2026, region="Arctic", publisher="NCPOR, Ministry of Earth Sciences",
         url="https://ncaor.gov.in/app/webroot/pages/view/340-himadri-station", topics=["arctic-fjords"], station="himadri",
         description="NCPOR information page about Himadri, India's Arctic research station at Ny-Ålesund, Svalbard, "
                     "which was established in 2008."),
    dict(slug="antarctic-treaty-secretariat-website", title="Secretariat of the Antarctic Treaty — official website",
         doc_type="Institutional Resource", year=2026, region="Antarctic", publisher="Secretariat of the Antarctic Treaty",
         url="https://www.ats.aq/", topics=["environmental-protection"],
         description="Official website of the Secretariat of the Antarctic Treaty. The Antarctic Treaty was signed in 1959 and "
                     "entered into force in 1961."),
    dict(slug="nsidc-sea-ice-index-g02135", title="Sea Ice Index, Version 4 (NSIDC G02135) — dataset landing page",
         doc_type="Institutional Resource", year=2026, region="Global", publisher="National Snow and Ice Data Center (NSIDC)",
         url=NSIDC_LANDING, topics=["sea-ice", "remote-sensing"],
         description="Landing page of the Sea Ice Index, Version 4, distributed by the National Snow and Ice Data Center. "
                     "The index provides daily and monthly Arctic and Antarctic sea-ice extent and concentration derived from "
                     "satellite passive-microwave data."),
]


def _topic_ids(db: Session, slugs: list[str]) -> list[int]:
    return [t.id for t in db.scalars(select(Topic).where(Topic.slug.in_(slugs)))]


def _set_prov(db: Session, rtype: str, obj, **fields) -> None:
    from app.services.provenance import ensure_for

    p = ensure_for(db, rtype, obj, commit=False)
    for k, v in fields.items():
        setattr(p, k, v)


# ------------------------------------------------------------------ public-source documents (metadata-only)
def seed_public_documents(db: Session) -> int:
    from app.rag.indexer import index_document
    from app.services import versions

    n = 0
    for spec in PUBLIC_DOCS:
        if db.scalar(select(Document).where(Document.slug == spec["slug"])):
            continue
        content = (f"[[page 1]]\n## Record description\n{spec['description']}\n\n"
                   f"## Access\nThis is a metadata record. The full text is not stored in PolarNexus; the original is "
                   f"published by {spec['publisher']}.")
        d = Document(slug=spec["slug"], title=spec["title"], doc_type=spec["doc_type"], abstract=spec["description"],
                     content=content, authors=[spec["publisher"]], institution=spec["publisher"], region=spec["region"],
                     year=spec["year"], language="English", keywords=[], source=spec["publisher"], status="indexed",
                     visibility="public", is_demo=False, views=0, publisher=spec["publisher"], source_url=spec["url"],
                     metadata_only=True, page_count=0)
        db.add(d)
        db.flush()
        for tid in _topic_ids(db, spec.get("topics", [])):
            db.add(ResourceTopic(resource_type="document", resource_id=d.id, topic_id=tid))
        if spec.get("station"):
            st = db.scalar(select(Station).where(Station.slug == spec["station"]))
            if st:
                db.add(ResourceLink(source_type="document", source_id=d.id, target_type="station", target_id=st.id, relation="describes"))
        _set_prov(db, "document", d, source_organisation=spec["publisher"], source_type="Official public web resource",
                  source_url=spec["url"], original_identifier=spec["url"], license="See the publisher's terms (link only — no content copied)",
                  publication_date=None, imported_at=NOW(), verification_status="public_source", verified_by="",
                  data_quality="Metadata record only — full text not ingested",
                  provenance_notes="Catalogue entry for a real public resource. Title, publisher and link recorded as published; "
                                   "the description is a short neutral summary written for discovery.")
        db.commit()
        index_document(db, d)
        versions.record(db, "document", d, "Imported (public-source metadata record)", "public_source", user_name="Seed import")
        n += 1
    return n


# ------------------------------------------------------------------ public-source photographs (Wikimedia Commons)
def seed_public_photos(db: Session) -> int:
    from app.ingestion.media import image_metadata, image_thumbnail, media_dir
    from app.rag.indexer import index_resource
    from app.services import versions, visual
    from app.services.duplicates import sha256_file

    manifest = json.loads((ASSETS / "commons_manifest.json").read_text(encoding="utf-8"))
    n = 0
    for spec in manifest["images"]:
        if db.scalar(select(Media).where(Media.slug == spec["slug"])):
            continue
        src = ASSETS / spec["file"]
        dest = media_dir("originals") / f"public-{spec['file']}"
        shutil.copyfile(src, dest)
        basic, exif = image_metadata(dest)
        thumb = media_dir("thumbs") / f"public-{Path(spec['file']).stem}.jpg"
        image_thumbnail(dest, thumb)
        captured = datetime.fromisoformat(spec["captured_at"]).replace(tzinfo=timezone.utc) if spec.get("captured_at") else None
        lat = lon = None
        location = ""
        if spec.get("gps"):
            lat, lon = spec["gps"]
            location = "GPS position recorded on Wikimedia Commons"
        st = db.scalar(select(Station).where(Station.slug == spec["station"])) if spec.get("station") else None
        if st and lat is None:
            lat, lon, location = st.latitude, st.longitude, st.location_name  # the photo depicts this station
        credit = f"{spec['artist']} — via Wikimedia Commons ({spec['license']})"
        m = Media(slug=spec["slug"], title=spec["title"], description=spec["source_description"], media_type="image",
                  category=spec["category"], region=spec["region"], year=spec["year"], credit=credit[:255],
                  license=spec["license"], tags=["photograph", "public source"], scene="ice", file_path=str(dest),
                  visibility="public", is_demo=False, status="indexed", filename=spec["file"], mime_type="image/jpeg",
                  size_bytes=dest.stat().st_size, width=basic["width"], height=basic["height"], thumbnail_path=str(thumb),
                  captured_at=captured, location=location, latitude=lat, longitude=lon, exif=exif or {},
                  processing_status="ready",
                  processing_steps=[{"key": "import", "label": "Imported from Wikimedia Commons", "status": "done",
                                     "detail": spec["commons_title"]}],
                  alt_text=spec["alt"], caption=spec["source_description"], source_url=spec["source_page"],
                  content_hash=sha256_file(dest))
        db.add(m)
        db.flush()
        for tid in _topic_ids(db, spec.get("topics", [])):
            db.add(ResourceTopic(resource_type="media", resource_id=m.id, topic_id=tid))
        if st:
            db.add(ResourceLink(source_type="media", source_id=m.id, target_type="station", target_id=st.id, relation="depicts"))
        _set_prov(db, "media", m, source_organisation=spec["artist"], source_type="Openly licensed photograph (Wikimedia Commons)",
                  source_url=spec["source_page"], original_identifier=spec["commons_title"], license=spec["license"]
                  + (f" — {spec['license_url']}" if spec.get("license_url") else ""),
                  collection_date=captured.date() if captured else None, imported_at=NOW(),
                  verification_status="public_source", data_quality="Licence and attribution as recorded on Commons",
                  provenance_notes=f"Credit: {spec.get('credit_line') or spec['artist']}. Reproduced at 1024 px.")
        db.commit()
        index_resource(db, "media", m.id)
        if visual.available():
            visual.index_media(db, m)
        else:
            m.visual_status = "skipped"
            db.commit()
        versions.record(db, "media", m, "Imported from Wikimedia Commons", "public_source", user_name="Seed import")
        n += 1
    return n


# ------------------------------------------------------------------ public-source datasets (NSIDC Sea Ice Index)
def seed_nsidc(db: Session) -> int:
    import secrets

    from app.ingestion import datasets as di
    from app.services.duplicates import sha256_bytes
    from app.services.storage import get_storage

    n = 0
    for spec in NSIDC_DATASETS:
        if db.scalar(select(Dataset).where(Dataset.slug == spec["slug"])):
            continue
        data = (ASSETS / spec["file"]).read_bytes()
        analysis = di.analyze(spec["file"], data)
        token = secrets.token_urlsafe(18)
        key = f"datasets/public-{spec['file']}"
        get_storage().save_bytes(key, data)
        up = DatasetUpload(token=token, filename=spec["file"], file_key=key, file_format=analysis["format"],
                           size_bytes=len(data), content_hash=sha256_bytes(data), analysis=analysis, status="registering",
                           steps=di.initial_register_steps())
        db.add(up)
        db.commit()
        meta = {"slug": spec["slug"], "title": spec["title"], "description": spec["description"] + " " + NSIDC_NOTE, "region": spec["region"],
                "license": "Open; citation requested", "source": "National Snow and Ice Data Center (NSIDC)",
                "source_url": spec["url"], "doi": "", "creator": "National Snow and Ice Data Center (NSIDC)",
                "keywords": ["sea ice extent", "sea ice area", "Sea Ice Index", "NSIDC", "passive microwave"],
                "topics": ["sea-ice", "remote-sensing", "climate-change"],
                "units": {"extent": "million km²", "area": "million km²"},
                "descriptions": {"extent": "Sea-ice extent as published in the file", "area": "Sea-ice area as published in the file",
                                 "source_dataset": "Source product named in the file", "region": "Hemisphere code in the file (N/S)"},
                "visibility": "public", "drop_duplicates": False}
        ds_id = di.register(up.id, meta, 0, provenance=dict(
            source_organisation="National Snow and Ice Data Center (NSIDC)", source_type="Public scientific dataset",
            source_url=spec["url"], original_identifier=f"G02135 v4 — {spec['file']}",
            license="Openly available; NSIDC requests citation of the Sea Ice Index (see the dataset landing page)",
            verification_status="public_source", data_quality="Unmodified values from the published file",
            provenance_notes=f"Landing page: {NSIDC_LANDING}. DOI not recorded in PolarNexus — see the landing page for the "
                             "current citation. " + NSIDC_NOTE))
        if ds_id:
            db.expire_all()
            n += 1
    return n


def link_public_records(db: Session) -> None:
    """NSIDC landing-page record ↔ NSIDC datasets (same source)."""
    landing = db.scalar(select(Document).where(Document.slug == "nsidc-sea-ice-index-g02135"))
    if not landing:
        return
    have = {(l.target_type, l.target_id) for l in db.scalars(select(ResourceLink).where(
        ResourceLink.source_type == "document", ResourceLink.source_id == landing.id))}
    for spec in NSIDC_DATASETS:
        ds = db.scalar(select(Dataset).where(Dataset.slug == spec["slug"]))
        if ds and ("dataset", ds.id) not in have:
            db.add(ResourceLink(source_type="document", source_id=landing.id, target_type="dataset", target_id=ds.id,
                                relation="describes_dataset"))
    db.commit()


# ------------------------------------------------------------------ demonstration story, campaign and metrics
def seed_demo_story(db: Session) -> int:
    from app.services import stories
    from app.services.catalog import build_catalog

    if db.scalar(select(ResearchStory).where(ResearchStory.is_demo.is_(True))):
        return 0
    flagship = db.scalar(select(Document).where(Document.slug == "antarctic-sea-ice-variability-study"))
    if not flagship:
        return 0
    cat = build_catalog(db, None)
    items = stories.suggest_items(cat, "document", flagship.id)
    # the real NSIDC record and openly licensed sea-ice photographs belong in the same story
    for slug, rtype in (("nsidc-sea-ice-index-antarctic-september-extent", "dataset"),
                        ("broken-pack-ice-with-antarctic-diatoms-ross-sea", "media"),
                        ("weddell-sea-pack-ice-edge-2016", "media")):
        key = cat.by_slug.get((rtype, slug))
        if key and not any(i["type"] == key[0] and i["id"] == key[1] for i in items):
            role = "Dataset" if rtype == "dataset" else "Photograph"
            idx = max((n for n, i in enumerate(items) if i["role"] == role), default=len(items) - 1) + 1
            items.insert(idx, {"type": key[0], "id": key[1], "role": role, "note": "Public-source record"})
    stories.create_story(db, cat, "From satellite records to the classroom: Antarctic sea-ice variability",
                         "document", flagship.id, items, None, is_demo=True, status="published")
    return 1


def seed_demo_campaign(db: Session, today: date | None = None) -> int:
    if db.scalar(select(Campaign).where(Campaign.is_demo.is_(True))):
        return 0
    today = today or NOW().date()
    contents = db.scalars(select(GeneratedContent).order_by(GeneratedContent.id)).all()
    if not contents:
        return 0
    start = today + timedelta(days=8)
    c = Campaign(slug="antarctic-science-week-2026-demo", name="Antarctic Science Week 2026 (demo)",
                 description="Demonstration campaign: a week of evidence-checked explainers about Antarctic sea ice, "
                             "research stations and expeditions for students, teachers and the public.",
                 start_date=start, end_date=start + timedelta(days=10), audiences=["students", "teachers", "public"],
                 topics=["sea-ice", "southern-ocean", "science-education"],
                 channels=["website", "social_media", "education_portal"], status="scheduled", is_demo=True)
    db.add(c)
    db.flush()
    published = [x for x in contents if x.status == "published"]
    approved = [x for x in contents if x.status == "approved"]
    review = [x for x in contents if x.status in {"under_review", "draft", "evidence_checked", "changes_requested"}]
    plan = []
    if published:
        plan.append((published[0], "Sea Ice Explainer", "website", 0, "published"))
    if approved:
        plan.append((approved[0], "Station Spotlight", "social_media", 2, "scheduled"))
    if review:
        plan.append((review[0], "Expedition Story", "education_portal", 5, "planned"))
    plan.append((None, "Dataset Visualisation: September sea-ice extent", "website", 8, "planned"))
    for content, title, channel, offset, status in plan:
        db.add(CampaignItem(campaign_id=c.id, content_id=content.id if content else None,
                            title=f"{title}: {content.title}" if content else title,
                            content_type=content.format if content else "infographic", channel=channel,
                            audience=(content.audience if content else "") or "public",
                            scheduled_for=(content.published_at.date() if status == "published" and content and content.published_at
                                           else start + timedelta(days=offset)), status=status,
                            notes="Demonstration calendar entry."))
    db.commit()
    return 1


def seed_demo_metrics(db: Session, today: date | None = None) -> int:
    """Synthetic engagement for published demo content — flagged is_demo and labelled DEMO METRICS everywhere."""
    if db.scalar(select(func.count()).select_from(OutreachEvent).where(OutreachEvent.is_demo.is_(True))):
        return 0
    rnd = random.Random(26063)
    camp_items = {i.content_id: i.campaign_id for i in db.scalars(select(CampaignItem)) if i.content_id}
    n = 0
    now = NOW()
    for c in db.scalars(select(GeneratedContent).where(GeneratedContent.status == "published")):
        start = c.published_at or now - timedelta(days=30)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)  # SQLite returns naive datetimes
        span = max(1, min(60, (now - start).days))
        base = rnd.randint(40, 160)
        channels = [ch for ch in (c.channels or ["website"])] or ["website"]
        for d in range(span):
            day = start + timedelta(days=d, hours=rnd.randint(8, 20))
            decay = max(0.15, 1 - d / (span + 5))
            for ch in channels:
                views = int(base * decay * rnd.uniform(0.3, 1.0) / (1 if ch == "website" else 2))
                if views <= 0:
                    continue
                for ev, count in (("view", views), ("click", int(views * rnd.uniform(0.05, 0.16))),
                                  ("share", int(views * rnd.uniform(0.0, 0.05))), ("complete", int(views * rnd.uniform(0.2, 0.55)))):
                    if count:
                        db.add(OutreachEvent(content_id=c.id, campaign_id=camp_items.get(c.id),
                                             event=ev, channel=ch, audience=c.audience or "public", is_demo=True, count=count,
                                             created_at=day))
                        n += 1
    db.commit()
    return n


# ------------------------------------------------------------------ entry points
def seed_v3(db: Session) -> dict:
    """Called at the end of a full demo seed."""
    from app.services import versions

    out = {"public_documents": seed_public_documents(db), "public_photos": seed_public_photos(db),
           "public_datasets": seed_nsidc(db)}
    link_public_records(db)
    out["versions_baseline"] = versions.ensure_baseline(db)
    out["demo_story"] = seed_demo_story(db)
    out["demo_campaign"] = seed_demo_campaign(db)
    out["demo_metric_rows"] = seed_demo_metrics(db)
    return out


def upgrade_v3(db: Session) -> dict:
    """Start-up upgrade of an existing database (v1/v2). Additive and idempotent."""
    from app.services import versions

    out: dict = {}
    if not db.scalar(select(func.count()).select_from(Topic)):
        return out  # empty database — the full seed handles it
    for name, fn in (("public_documents", seed_public_documents), ("public_photos", seed_public_photos),
                     ("public_datasets", seed_nsidc)):
        try:
            out[name] = fn(db)
        except Exception as exc:  # one failing import must not block the others
            db.rollback()
            log.warning("v3 %s import skipped: %s", name, exc)
    link_public_records(db)
    out["versions_baseline"] = versions.ensure_baseline(db)
    if db.scalar(select(Document).where(Document.slug == "antarctic-sea-ice-variability-study")):
        out["demo_story"] = seed_demo_story(db)
        out["demo_campaign"] = seed_demo_campaign(db)
        out["demo_metric_rows"] = seed_demo_metrics(db)
    if any(out.values()):
        log.info("v3 data upgrade: %s", out)
    return out


def public_source_counts(db: Session) -> dict:
    rows = db.scalars(select(Provenance).where(Provenance.verification_status == "public_source")).all()
    by: dict[str, int] = {}
    for r in rows:
        by[r.resource_type] = by.get(r.resource_type, 0) + 1
    return by
