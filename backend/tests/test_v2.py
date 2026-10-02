"""Tests for the v2 features: institutional activities, media ingestion, provenance & verification, unified search,
cross-modal AI synthesis, research-to-outreach workflow, timeline, impact KPIs, migrations and hardening.

Run with:  pytest -q
"""
import io
import re
import shutil
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.seed.seed_demo_data import run


@pytest.fixture(scope="module")
def client():
    run()  # reset + seed
    with TestClient(app) as c:
        yield c


def login(client, role):
    r = client.post("/api/auth/demo-login", json={"role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def wait_media(client, slug, headers, timeout=60):
    for _ in range(timeout * 2):
        st = client.get(f"/api/media/{slug}/processing", headers=headers).json()
        if st["processing_status"] in {"ready", "failed"}:
            return st
        time.sleep(0.5)
    raise AssertionError("media processing did not finish")


def jpeg_with_exif(lat=-70.7667, lon=11.7333) -> bytes:
    from PIL import Image

    im = Image.new("RGB", (800, 500), (40, 110, 160))
    exif = Image.Exif()
    exif[271] = "PolarCam"
    exif[272] = "Model X"
    exif[306] = "2024:01:15 10:30:00"

    def dms(v):
        v = abs(v)
        d = int(v)
        m = int((v - d) * 60)
        s = round(((v - d) * 60 - m) * 60 * 100)
        from fractions import Fraction
        return (Fraction(d), Fraction(m), Fraction(s, 100))
    gps = {1: "S" if lat < 0 else "N", 2: dms(lat), 3: "W" if lon < 0 else "E", 4: dms(lon)}
    exif[0x8825] = gps
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif.tobytes())
    return buf.getvalue()


# ---------------------------------------------------------------- institutional activities
def test_activities_list_filter_and_detail(client):
    r = client.get("/api/activities").json()
    assert r["total"] >= 12 and r["facets"]["activity_types"]
    ws = client.get("/api/activities", params={"activity_type": "workshop"}).json()
    assert ws["total"] >= 1 and all(a["activity_type"] == "workshop" for a in ws["results"])
    yr = client.get("/api/activities", params={"year": 2024}).json()
    assert yr["total"] >= 1 and all(a["year"] == 2024 for a in yr["results"])
    org = client.get("/api/activities", params={"organisation": "Konkan"}).json()
    assert org["total"] >= 1 and all("Konkan" in a["organisation"] for a in org["results"])
    demo = client.get("/api/activities", params={"verification": "Demo"}).json()
    assert demo["total"] == r["total"]  # every seeded activity is labelled demo
    up = client.get("/api/activities", params={"sort": "upcoming"}).json()
    assert up["results"][0]["status"] == "upcoming"
    d = client.get("/api/activities/sea-ice-teachers-workshop-2025").json()
    assert d["provenance"]["verification_status"] == "demo_data" and d["provenance"]["notice"]
    groups = {k for k, v in d["related"]["groups"].items() if v}
    assert {"document", "dataset", "researcher", "media"} <= groups


def test_activity_admin_crud_audit_and_rbac(client):
    body = {"title": "Polar Careers Webinar for Students", "description": "A webinar introducing careers in polar science "
            "and how research becomes public outreach.", "activity_type": "public_lecture", "date": "2026-03-10",
            "organisation": "Aurora Institute of Polar Studies (demo)", "location": "Online", "topics": ["science-education"],
            "researchers": ["ananya-rao"], "documents": ["what-is-polar-science"]}
    assert client.post("/api/activities", json=body).status_code == 401
    assert client.post("/api/activities", json=body, headers=login(client, "researcher")).status_code == 403
    bad = client.post("/api/activities", json={**body, "documents": ["does-not-exist"]}, headers=login(client, "admin"))
    assert bad.status_code == 422
    adm = login(client, "admin")
    a = client.post("/api/activities", json=body, headers=adm).json()
    assert a["slug"] and not a["is_demo"]
    det = client.get(f"/api/activities/{a['slug']}").json()
    assert det["provenance"]["verification_status"] == "pending_review"
    assert any(x["slug"] == "ananya-rao" for x in det["related"]["groups"]["researcher"])
    assert client.patch(f"/api/activities/{a['slug']}", json={"featured": True}, headers=adm).json()["featured"]
    # verify through the provenance centre
    v = client.patch(f"/api/admin/provenance/activity/{a['slug']}", json={"verification_status": "verified"}, headers=adm)
    assert v.status_code == 200 and v.json()["verification_status"] == "verified" and v.json()["verified_by"]
    # searchable
    hits = client.get("/api/search", params={"q": "polar careers webinar", "type": "Institutional Activity"}).json()
    assert any(h["slug"] == a["slug"] for h in hits["results"])
    # archive hides from the public
    client.patch(f"/api/activities/{a['slug']}", json={"status": "archived"}, headers=adm)
    assert client.get(f"/api/activities/{a['slug']}").status_code == 404
    logs = client.get("/api/admin/audit-logs", params={"q": a["slug"]}, headers=adm).json()
    actions = {x["action"] for x in logs["results"]}
    assert {"create", "feature", "verify", "archive"} <= actions
    assert client.delete(f"/api/activities/{a['slug']}", headers=adm).json()["deleted"]


# ---------------------------------------------------------------- media ingestion
def test_image_ingestion_exif_thumbnail_search(client):
    res = login(client, "researcher")
    files = {"file": ("ice-edge-survey.jpg", jpeg_with_exif(), "image/jpeg")}
    data = {"title": "Sea-ice edge survey photograph", "description": "Pancake ice forming along the sea-ice edge near Maitri.",
            "category": "Ice & Glaciers", "region": "Antarctic", "tags": "sea ice, survey", "station": "maitri",
            "topics": "sea-ice", "license": "CC BY 4.0"}
    r = client.post("/api/media/upload", files=files, data=data, headers=res)
    assert r.status_code == 200, r.text
    m = r.json()
    assert m["processing_status"] in {"processing", "ready"} and m["mime_type"] == "image/jpeg"
    st = wait_media(client, m["slug"], res)
    assert st["processing_status"] == "ready", st
    md = st["media"]
    assert md["width"] == 800 and md["height"] == 500
    assert md["exif"]["camera_make"] == "PolarCam" and md["captured_at"].startswith("2024-01-15")
    assert abs(md["latitude"] - (-70.7667)) < 0.01  # from EXIF GPS
    assert {s["key"]: s["status"] for s in st["steps"]}["ready"] == "done"
    thumb = client.get(f"/api/media/{m['slug']}/thumbnail")
    assert thumb.status_code == 200 and thumb.content[:3] == b"\xff\xd8\xff"
    assert client.get(f"/api/media/{m['slug']}/file").status_code == 200
    detail = client.get(f"/api/media/{m['slug']}").json()
    assert detail["provenance"]["verification_status"] == "user_uploaded"
    assert any(x["slug"] == "maitri" for x in detail["related"]["groups"]["station"])
    hits = client.get("/api/search", params={"q": "pancake ice sea-ice edge survey", "type": "Image"}).json()
    assert any(h["slug"] == m["slug"] for h in hits["results"][:5])


def test_media_upload_validation(client):
    res = login(client, "researcher")
    assert client.post("/api/media/upload", files={"file": ("a.jpg", jpeg_with_exif(), "image/jpeg")},
                       headers=login(client, "public")).status_code == 403
    gif = client.post("/api/media/upload", files={"file": ("anim.gif", b"GIF89a....", "image/gif")}, headers=res)
    assert gif.status_code == 422 and "Unsupported" in gif.json()["detail"]
    fake = client.post("/api/media/upload", files={"file": ("photo.png", b"not really a png", "image/png")}, headers=res)
    assert fake.status_code == 422 and "signature" in fake.json()["detail"]
    trunc = client.post("/api/media/upload", files={"file": ("broken.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 64, "image/jpeg")}, headers=res)
    assert trunc.status_code == 422
    mism = client.post("/api/media/upload", files={"file": ("photo.jpg", jpeg_with_exif(), "video/mp4")}, headers=res)
    assert mism.status_code == 422
    old = settings.MAX_IMAGE_MB
    settings.MAX_IMAGE_MB = 0
    try:
        big = client.post("/api/media/upload", files={"file": ("big.jpg", jpeg_with_exif(), "image/jpeg")}, headers=res)
        assert big.status_code == 413
    finally:
        settings.MAX_IMAGE_MB = old
    weird = client.post("/api/media/upload", files={"file": ("../../etc/passwd.jpg", jpeg_with_exif(), "image/jpeg")},
                        data={"title": "Traversal attempt"}, headers=res)
    assert weird.status_code == 200 and "/" not in weird.json()["filename"] and ".." not in weird.json()["filename"]


def test_media_file_serving_rejects_paths_outside_storage(client):
    from app.core.database import SessionLocal
    from app.models import Media

    with SessionLocal() as db:
        m = db.query(Media).filter(Media.is_demo.is_(True)).first()
        m.file_path, m.thumbnail_path = "/etc/hostname", "/etc/hostname"
        db.commit()
        slug = m.slug
    assert client.get(f"/api/media/{slug}/file").status_code == 404
    assert client.get(f"/api/media/{slug}/thumbnail").status_code == 404


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_video_ingestion_with_transcript(client, tmp_path):
    out = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10", "-f", "lavfi",
                    "-i", "sine=frequency=440", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(out)], check=True, timeout=60)
    vtt = ("WEBVTT\n\n00:00.000 --> 00:01.000\nKatabatic winds sweep down from the ice plateau.\n\n"
           "00:01.000 --> 00:02.000\nThe station anemometer recorded gusts during the blizzard.\n")
    res = login(client, "researcher")
    r = client.post("/api/media/upload", files={"file": ("winds.mp4", out.read_bytes(), "video/mp4"),
                                                "transcript": ("winds.vtt", vtt.encode(), "text/vtt")},
                    data={"title": "Blizzard field clip", "category": "Research Stations", "region": "Antarctic",
                          "expedition": "isea-43"}, headers=res)
    assert r.status_code == 200, r.text
    st = wait_media(client, r.json()["slug"], res)
    assert st["processing_status"] == "ready", st
    md = st["media"]
    assert md["media_type"] == "video" and md["duration_seconds"] and md["thumbnail_url"]
    assert md["transcript_source"] == "uploaded" and "anemometer" in md["transcript"]
    steps = {s["key"]: s["status"] for s in st["steps"]}
    assert steps["audio"] == "done" and steps["transcript"] == "done"
    hits = client.get("/api/search", params={"q": "anemometer gusts katabatic", "type": "Video"}).json()
    assert any(h["slug"] == md["slug"] for h in hits["results"])


def test_corrupt_video_handling(client):
    """A file with a video signature but no decodable stream is rejected (ffmpeg present) or processed with every
    unavailable step marked 'skipped' with its reason (ffmpeg absent) — never faked."""
    res = login(client, "researcher")
    r = client.post("/api/media/upload", files={"file": ("x.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200, "video/mp4")},
                    data={"title": "Corrupt clip"}, headers=res)
    if shutil.which("ffmpeg"):
        assert r.status_code == 422 and "video" in r.json()["detail"].lower()
    else:
        assert r.status_code == 200
        st = wait_media(client, r.json()["slug"], res)
        assert any(s["status"] == "skipped" and "ffmpeg" in s["detail"] for s in st["steps"])


# ---------------------------------------------------------------- provenance & verification
def test_provenance_labels_and_demo_guard(client):
    ds = client.get("/api/datasets/antarctic-sea-ice-observations").json()
    assert ds["provenance"]["verification_status"] == "synthetic_demo" and "synthetic" in ds["provenance"]["notice"].lower()
    assert ds["quality"]["variables"] and ds["quality"]["records"] > 0
    st = client.get("/api/stations/maitri").json()
    assert st["provenance"]["verification_status"] == "verified" and st["provenance"]["official"]
    doc = client.get("/api/resources/antarctic-sea-ice-variability-study").json()
    assert doc["provenance"]["verification_status"] == "demo_data"
    adm = login(client, "admin")
    refused = client.patch("/api/admin/provenance/dataset/antarctic-sea-ice-observations",
                           json={"verification_status": "verified"}, headers=adm)
    assert refused.status_code == 422 and "cannot be marked" in refused.json()["detail"]
    refused2 = client.patch("/api/admin/provenance/document/antarctic-sea-ice-variability-study",
                            json={"verification_status": "partner_source"}, headers=adm)
    assert refused2.status_code == 422
    assert client.get("/api/admin/provenance", headers=login(client, "editor")).status_code == 403
    q = client.get("/api/admin/provenance", params={"status": "synthetic_demo"}, headers=adm).json()
    assert q["total"] >= 16 and all(x["verification_status"] == "synthetic_demo" for x in q["results"])


def test_provenance_filters_in_search(client):
    syn = client.get("/api/search", params={"verification": "Synthetic", "page_size": 60}).json()
    assert syn["total"] >= 16 and all(r["type"] == "dataset" for r in syn["results"])
    off = client.get("/api/search", params={"verification": "Official", "page_size": 60}).json()
    assert off["total"] >= 7 and all(r["type"] in {"station", "expedition"} and r["official"] for r in off["results"])
    demo = client.get("/api/search", params={"verification": "Demo", "q": "sea ice"}).json()
    assert demo["total"] > 0 and all(r["verification"] == "demo_data" for r in demo["results"])
    assert client.get("/api/search").json()["facets"]["verification"]["Synthetic"] >= 16


# ---------------------------------------------------------------- unified search
def test_unified_search_types_and_groups(client):
    r = client.get("/api/search", params={"q": "Antarctic sea ice", "page_size": 60}).json()
    assert r["results"][0]["slug"] == "antarctic-sea-ice-variability-study"  # existing ranking preserved
    groups = r["facets"]["resource_groups"]
    assert {"Documents", "Datasets", "Images", "Expeditions"} <= set(groups)
    for t, expected in [("Institutional Activity", "activity"), ("Topic", "topic"), ("Video", "media"),
                        ("Researcher", "researcher"), ("Research Station", "station"), ("Expedition", "expedition")]:
        res = client.get("/api/search", params={"type": t, "page_size": 5}).json()
        assert res["total"] > 0 and all(x["type"] == expected for x in res["results"]), t
    combo = client.get("/api/search", params={"q": "sea ice", "region": "Antarctic", "type": "Dataset", "year_from": 2015}).json()
    assert all(x["type"] == "dataset" and x["region"] == "Antarctic" and x["year"] >= 2015 for x in combo["results"])
    org = client.get("/api/search", params={"organisation": "Konkan", "page_size": 60}).json()
    assert org["total"] > 0 and all("konkan" in x["organisation"].lower() for x in org["results"])
    out = client.get("/api/search", params={"q": "sea ice", "type": "Outreach Content"}).json()
    assert out["total"] >= 1 and all(x["url"].startswith("/outreach/") for x in out["results"])
    for mode in ("keyword", "semantic", "hybrid"):
        assert client.get("/api/search", params={"q": "workshop for teachers", "mode": mode}).json()["total"] > 0


def test_topic_page_and_timeline(client):
    t = client.get("/api/topics/sea-ice").json()
    assert t["name"] == "Sea Ice" and t["total"] > 3 and t["groups"]["document"]
    tl = client.get("/api/timeline", params={"topic": "sea-ice"}).json()
    years = [i["year"] for i in tl["items"]]
    assert years == sorted(years) and len({i["type"] for i in tl["items"]}) >= 3
    ex = client.get("/api/timeline", params={"expedition": "isea-43"}).json()
    assert ex["anchors"] == ["Antarctic Expedition 43"] and any(i["key"].startswith("expedition:") for i in ex["items"])
    only = client.get("/api/timeline", params={"station": "maitri", "type": "dataset"}).json()
    assert only["items"] and all(i["type"] == "dataset" for i in only["items"])
    assert client.get("/api/timeline", params={"expedition": "nope"}).status_code == 404


# ---------------------------------------------------------------- AI
def test_cross_modal_synthesis(client):
    r = client.post("/api/ai/ask", json={"question": "How has Antarctic sea ice changed and which expeditions studied it?"}).json()
    assert r["evidence_status"] in {"strong", "limited"}
    assert r["synthesis"]["compound"] and r["synthesis"]["list_type"] == "expedition"
    assert "Expeditions connected to this evidence" in r["answer"]
    markers = {int(n) for n in re.findall(r"\[(\d+)\]", r["answer"])}
    assert markers and markers <= {s["n"] for s in r["sources"]}  # every citation maps to a source
    assert any(s["resource_type"] == "expedition" for s in r["sources"])
    assert {"dataset", "expedition"} & set(r["related_groups"])


def test_ai_still_grounded_and_refuses(client):
    r = client.post("/api/ai/ask", json={"question": "What is the GDP of France in 2019?"}).json()
    assert r["evidence_status"] == "insufficient" and r["sources"] == [] and r["related_groups"] == {}
    d = client.post("/api/ai/ask", json={"question": "Explain the key factors discussed in this resource.",
                                         "document_slug": "antarctic-sea-ice-variability-study"}).json()
    assert d["sources"][0]["slug"] == "antarctic-sea-ice-variability-study" and d["evidence_status"] == "strong"
    # activities / topics / outreach are discoverable but never used as evidence for answers
    g = client.post("/api/ai/ask", json={"question": "What factors influence Antarctic sea-ice variability?"}).json()
    assert all(s["resource_type"] not in {"activity", "topic", "content"} for s in g["sources"])


# ---------------------------------------------------------------- outreach workflow
def test_research_to_outreach_full_workflow(client):
    res = login(client, "researcher")
    fm = client.get("/api/content/formats").json()
    assert {"summary", "newsletter", "expedition_update", "highlight"} <= {f["key"] for f in fm["formats"]}
    assert {"teachers", "policy"} <= {a["key"] for a in fm["audiences"]}
    c = client.post("/api/content/generate", json={"format": "expedition_update", "resource_type": "expedition",
                                                   "resource_slug": "isea-43", "audience": "teachers"}, headers=res).json()
    assert c["status"] == "draft" and c["audience"] == "teachers" and c["citations"]
    assert "Discussion questions" in c["body"]
    assert all(x["page"] is not None for x in c["citations"] if x["resource_type"] == "document")
    chk = client.post(f"/api/content/{c['id']}/check", headers=res).json()
    assert chk["status"] == "evidence_checked" or chk["overall"] == "fail"
    sub = client.post(f"/api/content/{c['id']}/submit", headers=res).json()
    assert sub["status"] == "under_review" and any(h["action"] == "evidence_checked" for h in sub["history"])
    ed = login(client, "editor")
    appr = client.post(f"/api/reviews/{c['id']}/approve", json={"acknowledge_warnings": True}, headers=ed).json()
    assert appr["status"] == "approved"
    pub = client.post(f"/api/reviews/{c['id']}/publish", json={"channels": ["linkedin"]}, headers=ed).json()
    assert pub["status"] == "published" and pub["channels"][0] == "website"
    statuses = {x["channel"]: x["status"] for x in pub["channel_status"]}
    assert statuses == {"website": "live", "linkedin": "connector_ready"}
    assert any("prototype simulation" in h["comment"] for h in pub["history"])
    item = client.get(f"/api/outreach/{c['id']}").json()
    assert item["provenance"]["verification_status"] == "verified" and item["citations"]
    assert client.get(f"/api/outreach/{c['id'] + 999}").status_code == 404


def test_outreach_reject_and_edit_rules(client):
    res = login(client, "researcher")
    c = client.post("/api/content/generate", json={"format": "summary", "resource_type": "dataset",
                                                   "resource_slug": "southern-ocean-surface-pco2", "audience": "policy"},
                    headers=res).json()
    assert c["format"] == "summary"
    client.post(f"/api/content/{c['id']}/check", headers=res)
    edited = client.put(f"/api/content/{c['id']}", json={"body": c["body"] + "\n\nAn added sentence for the reviewers here."}, headers=res).json()
    assert edited["status"] == "draft"  # editing after an evidence check requires a new check
    client.post(f"/api/content/{c['id']}/submit", headers=res)
    ed = login(client, "editor")
    assert client.post(f"/api/reviews/{c['id']}/reject", json={"comment": ""}, headers=ed).status_code == 422
    rej = client.post(f"/api/reviews/{c['id']}/reject", json={"comment": "Out of scope for this campaign."}, headers=ed).json()
    assert rej["status"] == "rejected"
    assert client.put(f"/api/content/{c['id']}", json={"body": "Changed text that should not be accepted."}, headers=res).status_code == 409
    assert client.post(f"/api/reviews/{c['id']}/publish", json={}, headers=ed).status_code == 409


def test_generate_from_ai_answer_chunks_and_translation(client):
    a = client.post("/api/ai/ask", json={"question": "How does the Southern Ocean absorb carbon dioxide?"}).json()
    res = login(client, "researcher")
    c = client.post("/api/content/generate", json={"format": "highlight", "resource_type": "chunks",
                                                   "chunk_ids": [s["chunk_id"] for s in a["sources"]]}, headers=res).json()
    assert c["citations"] and c["format"] == "highlight"
    tr = client.post(f"/api/content/{c['id']}/translate", json={"language": "Hindi"}, headers=res).json()
    assert tr["language"] == "Hindi" and tr["status"] == "draft" and tr["translated_from"] == c["id"]
    assert len(tr["citations"]) == len(c["citations"])


# ---------------------------------------------------------------- impact, graph, map
def test_impact_dashboard_is_labelled_and_measured(client):
    client.get("/api/search", params={"q": "ozone"})
    imp = client.get("/api/impact").json()
    assert imp["label"] == "Prototype Demonstration Metrics" and imp["disclaimer"]
    assert imp["knowledge"]["by_type"]["Institutional Activities"] >= 14
    assert imp["ai"]["questions_answered"] > 0 and imp["ai"]["insufficient_evidence"] > 0
    assert imp["content"]["published"] >= 1
    assert imp["measured"]["search_latency_ms"]["samples"] >= 1  # only live, measured timings


def test_graph_and_map_include_new_types(client):
    g = client.get("/api/graph/activity/sea-ice-teachers-workshop-2025").json()
    types = {n["type"] for n in g["nodes"]}
    assert {"activity", "document", "dataset", "researcher", "topic"} <= types
    m = client.get("/api/map").json()
    assert m["activities"] and m["media"] and m["stations"][0]["verification"]


# ---------------------------------------------------------------- platform
def test_rbac_on_new_admin_functions(client):
    pub = login(client, "public")
    for method, url, body in [("post", "/api/activities", {}), ("patch", "/api/admin/provenance/station/maitri", {"license": "x"}),
                              ("get", "/api/admin/provenance", None), ("get", "/api/my/media-uploads", None)]:
        r = getattr(client, method)(url, headers=pub, **({"json": body} if body is not None else {}))
        assert r.status_code in {403, 422} if method == "post" else r.status_code == 403, (url, r.status_code)
    assert client.get("/api/admin/provenance").status_code == 401


def test_login_throttling(client):
    old = settings.LOGIN_MAX_FAILURES
    settings.LOGIN_MAX_FAILURES = 3
    try:
        for _ in range(3):
            assert client.post("/api/auth/login", json={"email": "throttle@polarnexus.demo", "password": "bad"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": "throttle@polarnexus.demo", "password": "bad"}).status_code == 429
    finally:
        settings.LOGIN_MAX_FAILURES = old


def test_additive_migration_on_old_schema(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    from app.core.database import Base
    from app.core.migrations import migrate

    eng = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as conn:  # a v1-shaped media table with one existing row
        conn.execute(text("CREATE TABLE media (id INTEGER PRIMARY KEY, slug VARCHAR(160), title VARCHAR(300), "
                          "description TEXT, media_type VARCHAR(24), category VARCHAR(48), region VARCHAR(48), year INTEGER, "
                          "credit VARCHAR(255), license VARCHAR(128), tags JSON, scene VARCHAR(32), duration VARCHAR(16), "
                          "file_path VARCHAR(500), visibility VARCHAR(16), is_demo BOOLEAN, views INTEGER, "
                          "created_at DATETIME, updated_at DATETIME)"))
        conn.execute(text("INSERT INTO media (slug, title, description, media_type) VALUES ('keep-me', 'Keep', 'd', 'image')"))
    Base.metadata.create_all(eng)
    out = migrate(eng)
    assert "media.processing_status" in out["columns_added"]
    cols = {c["name"] for c in inspect(eng).get_columns("media")}
    assert {"processing_status", "thumbnail_path", "transcript"} <= cols
    with eng.connect() as conn:
        assert conn.execute(text("SELECT title, processing_status FROM media WHERE slug='keep-me'")).one() == ("Keep", "ready")
    assert migrate(eng)["columns_added"] == []  # idempotent
