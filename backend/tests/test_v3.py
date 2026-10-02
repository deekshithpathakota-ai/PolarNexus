"""Tests for the v3 features: public-source data, provenance statuses, evidence strength and audience modes,
visual semantic search, dataset ingestion (CSV/JSON), OCR, duplicate detection, version history, FAIR metadata,
lineage, research stories, campaigns/calendar/analytics, admin platform health, cookie sessions and rate limits.

Optional subsystems (CLIP visual search, tesseract OCR, ffmpeg) are tested when installed and otherwise checked for
an honest "unavailable/skipped" report.

Run with:  pytest -q
"""
import io
import json
import re
import shutil
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.seed.seed_demo_data import run
from app.services import visual


@pytest.fixture(scope="module")
def client():
    run()  # reset + seed (includes the v3 public-source records)
    with TestClient(app) as c:
        yield c


def login(client, role):
    r = client.post("/api/auth/demo-login", json={"role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def wait(fn, done, timeout=60):
    for _ in range(timeout * 4):
        out = fn()
        if done(out):
            return out
        time.sleep(0.25)
    raise AssertionError("background job did not finish")


# ------------------------------------------------------------------ real public-source data + provenance
def test_public_source_records_are_labelled_and_never_demo(client):
    ds = client.get("/api/datasets/nsidc-sea-ice-index-antarctic-september-extent").json()
    assert ds["is_demo"] is False and ds["provenance"]["verification_status"] == "public_source"
    assert ds["provenance"]["source_url"].startswith("https://noaadata.apps.nsidc.org/")
    assert ds["record_count"] >= 45 and ds["temporal_start"].startswith("1979")
    # values are the file's own numbers (first row of S_09: 1979, extent 18.20)
    recs = client.get("/api/datasets/nsidc-sea-ice-index-antarctic-september-extent/records", params={"page_size": 1}).json()
    assert recs["records"][0]["extent"] == 18.2 and recs["records"][0]["year"] == 1979
    series = client.get("/api/datasets/nsidc-sea-ice-index-antarctic-september-extent/series", params={"x": "year"}).json()
    assert series["y"] in {"extent", "area"} and "year" not in series["numeric_variables"]  # no meaningless year chart
    csv = client.get("/api/datasets/nsidc-sea-ice-index-antarctic-september-extent/download").text
    assert "SYNTHETIC" not in csv.splitlines()[0] and "Public source" in csv.splitlines()[0]
    synth = client.get("/api/datasets/antarctic-sea-ice-observations/download").text
    assert "SYNTHETIC" in synth.splitlines()[0]

    photo = client.get("/api/media/rv-polarstern-in-sea-ice-mosaic-2020").json()
    assert photo["is_demo"] is False and photo["alt_text"] and photo["license"] == "CC BY-SA 4.0"
    assert photo["provenance"]["verification_status"] == "public_source"
    assert photo["provenance"]["source_url"].startswith("https://commons.wikimedia.org/")
    doc = client.get("/api/resources/indian-antarctic-act-2022").json()
    assert doc["metadata_only"] is True and doc["source_url"].startswith("https://www.indiacode.nic.in")
    statuses = client.get("/api/provenance/statuses").json()
    assert "public_source" in {s["key"] for s in statuses["statuses"]} and "Public Source" in statuses["filters"]
    pub = client.get("/api/search", params={"verification": "Public Source", "page_size": 48}).json()
    assert pub["total"] >= 15 and all(r["verification"] == "public_source" for r in pub["results"])


def test_demo_records_still_cannot_be_verified_and_public_can(client):
    admin = login(client, "admin")
    r = client.patch("/api/admin/provenance/dataset/antarctic-sea-ice-observations", headers=admin,
                     json={"verification_status": "verified"})
    assert r.status_code == 422
    ok = client.patch("/api/admin/provenance/media/rv-polarstern-in-sea-ice-mosaic-2020", headers=admin,
                      json={"verification_status": "verified", "comment": "Licence checked"})
    assert ok.status_code == 200
    hist = client.get("/api/versions/media/rv-polarstern-in-sea-ice-mosaic-2020").json()
    assert hist["versions"][0]["status"] == "verified" and hist["versions"][-1]["version"] == 1
    assert len(hist["versions"]) >= 2  # never overwritten


def test_search_explains_why_and_does_not_let_demo_outrank_by_default(client):
    r = client.get("/api/search", params={"q": "Antarctic sea ice"}).json()
    top = r["results"][:8]
    assert all(x["match_reasons"] for x in top)
    assert any("Public source" in x["match_reasons"] for x in top)
    assert any(x["score_breakdown"]["authority_multiplier"] > 1 for x in top)
    demo = [x for x in top if x["verification"] in {"demo_data", "synthetic_demo"}]
    assert all(x["score_breakdown"]["authority_multiplier"] == 1.0 for x in demo)


# ------------------------------------------------------------------ AI: evidence strength, basis, audiences
def test_ai_evidence_strength_basis_and_pipeline(client):
    r = client.post("/api/ai/ask", json={"question": "How does the Southern Ocean absorb carbon dioxide?"}).json()
    assert r["evidence_status"] in {"strong", "limited"}  # unchanged contract
    assert r["evidence_strength"] in {"strong", "moderate", "limited"}
    assert r["evidence_basis"]["demonstration"] >= 1 and "demonstration" in r["evidence_basis"]["note"]
    assert [p["step"] for p in r["pipeline"]][-1] == "Citation validation"
    assert all("verification" in s for s in r["sources"])
    bad = client.post("/api/ai/ask", json={"question": "Who won the cricket world cup in 2011?"}).json()
    assert bad["evidence_strength"] == "insufficient" and bad["sources"] == []


@pytest.mark.parametrize("audience", ["researcher", "teacher", "student", "public"])
def test_ai_audience_modes_stay_grounded(client, audience):
    r = client.post("/api/ai/ask", json={"question": "What factors influence Antarctic sea-ice variability?",
                                         "audience": audience}).json()
    assert r["audience"] == audience and r["evidence_status"] != "insufficient"
    markers = {int(n) for n in re.findall(r"\[(\d+)\]", r["answer"])}
    assert markers and markers <= {s["n"] for s in r["sources"]}
    if audience == "teacher":
        assert "Teaching points" in r["answer"] and "Discussion questions" in r["answer"]
    if audience in {"student", "public"}:
        assert r["answer"].startswith("**In simple terms**")
    assert client.post("/api/ai/ask", json={"question": "x y", "audience": "wizard"}).status_code == 422


def test_ai_status_reports_optional_subsystems(client):
    s = client.get("/api/ai/status").json()
    assert {"visual_search", "ocr", "audiences", "llm_provider"} <= set(s)
    assert "key" not in json.dumps(s).lower() or "api_key" not in json.dumps(s).lower()


def test_llm_provider_settings_aliases():
    assert settings.llm_api_key == (settings.LLM_API_KEY or settings.OPENAI_API_KEY)
    old = settings.LLM_API_KEY, settings.LLM_PROVIDER
    try:
        settings.LLM_API_KEY, settings.LLM_PROVIDER = "test-key", "none"
        assert settings.llm_enabled is False  # explicit opt-out wins
        settings.LLM_PROVIDER = "openai-compatible"
        assert settings.llm_enabled is True and settings.llm_api_key == "test-key"
    finally:
        settings.LLM_API_KEY, settings.LLM_PROVIDER = old


# ------------------------------------------------------------------ visual semantic search
def test_visual_search_real_or_honestly_unavailable(client):
    r = client.get("/api/visual/search", params={"q": "iceberg near a research vessel"}).json()
    if not visual.available():
        assert r["available"] is False and r["results"] == [] and r["notice"]
        return
    assert r["available"] is True and r["results"]
    assert r["results"][0]["slug"] in {"iceberg-from-rrs-ernest-shackleton-2012", "iceberg-a23a-weddell-sea-polarstern-2016"}
    assert all(0 < x["similarity"] < 1 for x in r["results"])
    st = client.get("/api/visual/status").json()
    assert st["indexed_media"] >= 10


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_video_keyframes_get_visual_step(client, tmp_path):
    vid = tmp_path / "scenes.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=3", "-f", "lavfi",
                    "-i", "color=c=navy:s=320x240:d=3", "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]",
                    "-pix_fmt", "yuv420p", str(vid)], check=True, timeout=60)
    h = login(client, "researcher")
    r = client.post("/api/media/upload", headers=h, files={"file": ("scenes.mp4", vid.read_bytes(), "video/mp4")},
                    data={"title": "Scene test video", "region": "Antarctic", "category": "Other"})
    assert r.status_code == 200, r.text
    st = wait(lambda: client.get(f"/api/media/{r.json()['slug']}/processing", headers=h).json(),
              lambda s: s["processing_status"] in {"ready", "failed"})
    steps = {s["key"]: s for s in st["steps"]}
    assert st["processing_status"] == "ready"
    if visual.available():
        assert steps["visual"]["status"] == "done" and "key frame" in steps["visual"]["detail"]
        frame = client.get(f"/api/media/{r.json()['slug']}/frames/0", headers=h)
        assert frame.status_code == 200 and frame.headers["content-type"] == "image/jpeg"
    else:
        assert steps["visual"]["status"] == "skipped" and steps["visual"]["detail"]


# ------------------------------------------------------------------ dataset ingestion
CSV = (b"# Test buoy file\nstation,date,latitude,longitude,temp_c,salinity\n"
       b"A,2024-01-01,-69.4,76.2,-1.2,34.1\nA,2024-01-02,-69.4,76.2,-1.1,34.0\nA,2024-01-02,-69.4,76.2,-1.1,34.0\n"
       b"B,2024-01-03,-95.0,76.3,bad,34.2\nB,not-a-date,-69.5,76.4,-0.9,\n")


def test_dataset_analysis_detects_quality_issues(client):
    h = login(client, "researcher")
    r = client.post("/api/datasets/ingest/analyze", headers=h, files={"file": ("buoy.csv", CSV, "text/csv")})
    assert r.status_code == 200, r.text
    a = r.json()["analysis"]
    codes = {i["code"] for i in a["issues"]}
    assert {"missing_values", "duplicate_rows", "invalid_coordinates"} <= codes
    assert "invalid_numeric" in codes and "invalid_date" in codes
    assert a["roles"] == {"time": "date", "latitude": "latitude", "longitude": "longitude"}
    assert a["rows"] == 5 and a["columns"] == 6 and a["summary"]["verdict"] == "fail"
    tok = r.json()["token"]
    # errors must be acknowledged
    assert client.post(f"/api/datasets/ingest/{tok}/confirm", headers=h, json={"title": "Buoy test", "region": "Antarctic"}).status_code == 422
    c = client.post(f"/api/datasets/ingest/{tok}/confirm", headers=h,
                    json={"title": "Buoy test dataset", "region": "Antarctic", "acknowledge_errors": True,
                          "drop_duplicates": True, "units": {"temp_c": "°C", "salinity": "PSU"}, "topics": ["southern-ocean"]})
    assert c.status_code == 200, c.text
    st = wait(lambda: client.get(f"/api/datasets/ingest/{tok}", headers=h).json(), lambda s: s["status"] in {"registered", "failed"})
    assert st["status"] == "registered", st
    slug = st["dataset"]["slug"]
    ds = client.get(f"/api/datasets/{slug}").json()
    assert ds["record_count"] == 4 and ds["quality_report"]["duplicates_dropped"] == 1
    assert ds["provenance"]["verification_status"] == "user_uploaded" and ds["has_coordinates"]
    assert {v["name"]: v["unit"] for v in ds["variables"]}["temp_c"] == "°C"
    assert client.get(f"/api/versions/dataset/{slug}").json()["versions"][0]["change"].startswith("Imported")
    # same file again → duplicate candidate by content hash
    again = client.post("/api/datasets/ingest/analyze", headers=h, files={"file": ("buoy-copy.csv", CSV, "text/csv")}).json()
    assert again["analysis"]["duplicates"] and again["analysis"]["duplicates"][0]["similarity"] == 100


def test_dataset_json_and_rejections(client):
    h = login(client, "researcher")
    js = json.dumps({"data": [{"time": "2023-02-01T00:00:00", "lat": 78.9, "lon": 11.9, "aod": 0.04},
                              {"time": "2023-02-02T00:00:00", "lat": 78.9, "lon": 11.9, "aod": 0.05}]}).encode()
    r = client.post("/api/datasets/ingest/analyze", headers=h, files={"file": ("aod.json", js, "application/json")})
    assert r.status_code == 200 and r.json()["analysis"]["format_detail"]["json_shape"] == "object.data"
    assert r.json()["analysis"]["suggested_charts"] == ["time_series", "map"]
    assert client.post("/api/datasets/ingest/analyze", headers=h, files={"file": ("x.nc", b"CDF\x01abc", "application/x-netcdf")}).status_code == 422
    assert client.post("/api/datasets/ingest/analyze", headers=h, files={"file": ("x.csv", b"\x00\x01\x02", "text/csv")}).status_code == 422
    assert client.post("/api/datasets/ingest/analyze", headers=h, files={"file": ("x.json", b"{not json", "application/json")}).status_code == 422
    assert client.post("/api/datasets/ingest/analyze", files={"file": ("x.csv", CSV, "text/csv")}).status_code == 401
    assert client.post("/api/datasets/ingest/analyze", headers=login(client, "public"),
                       files={"file": ("x.csv", CSV, "text/csv")}).status_code == 403


# ------------------------------------------------------------------ OCR + duplicate detection + update existing
def scanned_pdf(text_lines: list[str]) -> bytes:
    """A PDF whose only page is an *image* of text (no text layer) — what a scanner produces."""
    import fitz
    from PIL import Image, ImageDraw, ImageFont

    im = Image.new("L", (1700, 2200), 255)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 42)
    except OSError:
        font = ImageFont.load_default()
    y = 150
    for line in text_lines:
        d.text((120, y), line, fill=0, font=font)
        y += 70
    buf = io.BytesIO()
    im.save(buf, "PNG")
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=buf.getvalue())
    return pdf.tobytes()


LINES = ["Antarctic Field Notebook Scan", "Observations of katabatic winds near the station",
         "were recorded during the winter season of 1998.", "Wind speeds increased sharply before blizzards",
         "and the snow surface was redistributed across the ice shelf.", "These handwritten logs were later typed",
         "and archived for research use by the station team.", "Katabatic flows dominate the coastal climate here."]


def test_ocr_scanned_pdf(client):
    from app.ingestion.ocr import available

    h = login(client, "researcher")
    r = client.post("/api/ingestion/upload", headers=h, files={"file": ("field-notebook-scan.pdf", scanned_pdf(LINES), "application/pdf")},
                    data={"title": "Antarctic Field Notebook Scan", "doc_type": "Technical Report", "region": "Antarctic"})
    assert r.status_code == 200, r.text
    job = wait(lambda: client.get(f"/api/ingestion/jobs/{r.json()['id']}", headers=h).json(),
               lambda j: j["status"] in {"completed", "failed"})
    steps = {s["key"]: s for s in job["steps"]}
    if not available():
        assert job["status"] == "failed" and "OCR is not available" in job["error"] and steps["ocr"]["status"] == "skipped"
        return
    assert job["status"] == "completed", job
    assert steps["ocr"]["status"] == "done" and "page(s) 1" in steps["ocr"]["detail"] and job["ocr_status"] == "applied"
    doc = client.get(f"/api/resources/{job['document']['slug']}", headers=h).json()
    assert doc["ocr_status"] == "applied" and doc["ocr_pages"] == [1]
    ask = client.post("/api/ai/ask", headers=h, json={"question": "What was observed about katabatic winds?",
                                                       "document_slug": doc["slug"]}).json()
    assert ask["sources"] and ask["sources"][0]["page"] == 1

    # duplicate check before uploading the same scan again
    dup = client.post("/api/ingestion/check-duplicates", headers=h,
                      files={"file": ("field-notebook-scan.pdf", scanned_pdf(LINES), "application/pdf")},
                      data={"title": "Antarctic Field Notebook Scan"}).json()
    assert dup["potential_duplicate"] and dup["duplicates"][0]["slug"] == doc["slug"]
    assert {"keep_both", "update_existing", "review", "cancel"} == set(dup["options"])
    # "update existing": a new file becomes version N+1 while the old content is preserved in history
    r2 = client.post("/api/ingestion/upload", headers=h, files={"file": ("field-notebook-scan-v2.pdf", scanned_pdf(LINES + ["Revised edition with corrections."]), "application/pdf")},
                     data={"doc_type": "Technical Report", "update_existing": doc["slug"]})
    assert r2.status_code == 200, r2.text
    wait(lambda: client.get(f"/api/ingestion/jobs/{r2.json()['id']}", headers=h).json(), lambda j: j["status"] in {"completed", "failed"})
    hist = client.get(f"/api/versions/document/{doc['slug']}", headers=h).json()["versions"]
    assert [v["change"].split(" ")[0] for v in hist[:2]] == ["New", "Snapshot"]
    assert hist[1]["version"] == hist[0]["version"] - 1


def test_update_existing_refuses_demo_documents(client):
    h = login(client, "admin")
    r = client.post("/api/ingestion/upload", headers=h, files={"file": ("x.txt", b"Some polar text " * 30, "text/plain")},
                    data={"doc_type": "Technical Report", "update_existing": "antarctic-sea-ice-variability-study"})
    assert r.status_code == 422


# ------------------------------------------------------------------ FAIR metadata, lineage
def test_fair_metadata_never_invents_fields(client):
    f = client.get("/api/fair/dataset/nsidc-sea-ice-index-antarctic-september-extent").json()
    vals = {x["key"]: x["value"] for x in f["fields"]}
    assert vals["doi"] is None and vals["rights"] and vals["source"].startswith("https://")
    assert vals["temporal"].startswith("1979-09-01/") and 0 < f["completeness"] <= 1
    r = client.get("/api/fair/researcher/" + client.get("/api/researchers").json()["results"][0]["slug"]).json()
    assert all(c.get("orcid") is None for c in (r["dublin_core"]["dc:creator"] or []))
    assert client.get("/api/fair/document/no-such-thing").status_code == 404


def test_content_lineage_lists_sources_and_review(client):
    feed = client.get("/api/outreach").json()["results"]
    lin = client.get(f"/api/lineage/content/{feed[0]['id']}").json()
    keys = [s["key"] for s in lin["stages"]]
    assert keys == ["source", "ingestion", "processing", "transformation", "generation", "review", "publication"]
    assert lin["generated_from"] and lin["stages"][-1]["state"] == "done"
    res = client.get("/api/lineage/document/antarctic-sea-ice-variability-study").json()
    assert res["stages"][-1]["state"] == "demo"


# ------------------------------------------------------------------ research stories
def test_research_story_flow(client):
    stories = client.get("/api/stories").json()["results"]
    demo = next(s for s in stories if s["is_demo"])
    s = client.get(f"/api/stories/{demo['slug']}").json()
    roles = s["roles"]
    assert roles[0] == "Research topic" and "Research paper" in roles and "Dataset" in roles
    assert {"scientific", "public", "student"} <= set(s["summaries"])
    for m in ("scientific", "public", "student"):
        txt = s["summaries"][m]["text"]
        assert re.search(r"\[\d+\]", txt), m
    assert s["timeline"] and s["map_points"] and s["evidence"]
    assert any(i["verification"] == "public_source" for i in s["items"])
    # create from a dataset, edit, publish (editor), archive
    h = login(client, "researcher")
    sug = client.get("/api/stories/suggest", params={"seed_type": "dataset", "seed_slug": "nsidc-sea-ice-index-antarctic-september-extent"}).json()
    assert sug["items"]
    r = client.post("/api/stories", headers=h, json={"seed_type": "dataset", "seed_slug": "nsidc-sea-ice-index-antarctic-september-extent"})
    assert r.status_code == 200, r.text
    slug = r.json()["slug"]
    assert client.get(f"/api/stories/{slug}").status_code == 404  # drafts are private
    assert client.patch(f"/api/stories/{slug}", headers=h, json={"status": "published"}).status_code == 403
    ed = login(client, "editor")
    assert client.patch(f"/api/stories/{slug}", headers=ed, json={"status": "published"}).json()["status"] == "published"
    assert client.get(f"/api/stories/{slug}").status_code == 200
    assert client.delete(f"/api/stories/{slug}", headers=h).json()["status"] == "archived"
    assert client.post("/api/stories", headers=login(client, "public"), json={"seed_type": "dataset", "seed_slug": "x"}).status_code == 403


# ------------------------------------------------------------------ campaigns, calendar, analytics
def test_campaign_respects_review_workflow(client):
    h = login(client, "researcher")
    opts = client.get("/api/campaigns/options", headers=h).json()
    assert {c["key"] for c in opts["channels"]} == {"website", "social_media", "newsletter", "education_portal"}
    c = client.post("/api/campaigns", headers=h, json={"name": "Arctic Week Test", "audiences": ["students"],
                                                       "channels": ["website", "social_media"], "start_date": "2026-11-01",
                                                       "end_date": "2026-11-07"}).json()
    draft = next(x for x in opts["content"] if x["status"] in {"draft", "evidence_checked", "under_review"})
    it = client.post(f"/api/campaigns/{c['slug']}/items", headers=h,
                     json={"title": "Explainer", "content_id": draft["id"], "scheduled_for": "2026-11-02", "channel": "social_media"}).json()
    assert it["can_schedule"] is False and it["blockers"]
    r = client.patch(f"/api/campaigns/{c['slug']}/items/{it['id']}", headers=h, json={"status": "scheduled"})
    assert r.status_code == 409  # not approved → cannot be scheduled
    approved = next((x for x in opts["content"] if x["status"] == "approved"), None)
    if approved:
        ok = client.patch(f"/api/campaigns/{c['slug']}/items/{it['id']}", headers=h,
                          json={"content_id": approved["id"], "status": "scheduled"}).json()
        assert ok["status"] == "scheduled" and ok["simulated_channels"] == ["linkedin", "instagram"]
        assert client.post(f"/api/campaigns/{c['slug']}/items/{it['id']}/publish", headers=h).status_code == 403
        pub = client.post(f"/api/campaigns/{c['slug']}/items/{it['id']}/publish", headers=login(client, "editor")).json()
        assert pub["status"] == "published" and pub["content"]["status"] == "published"
    cal = client.get("/api/calendar", headers=h, params={"start": "2026-10-01", "end": "2026-12-31"}).json()
    assert any(e["campaign"]["slug"] == c["slug"] for e in cal["events"])
    assert client.get("/api/campaigns", headers=login(client, "public")).status_code == 403
    assert client.delete(f"/api/campaigns/{c['slug']}", headers=h).json()["status"] == "archived"


def test_outreach_analytics_labels_demo_metrics(client):
    h = login(client, "editor")
    a = client.get("/api/outreach-analytics", headers=h).json()
    assert a["basis"]["demo_events"] > 0 and "DEMO METRICS" in a["basis"]["label"]
    assert a["totals"]["view"] > 0 and a["campaigns"] and a["formats"] and "rate" in a["conversion"]
    pub_id = client.get("/api/outreach").json()["results"][0]["id"]
    assert client.post(f"/api/outreach/{pub_id}/track", json={"event": "view"}).status_code == 200
    live = client.get("/api/outreach-analytics", headers=h, params={"include_demo": False}).json()
    assert live["basis"]["label"] == "LIVE METRICS" and live["totals"]["view"] >= 1
    assert client.post("/api/outreach/999999/track", json={"event": "view"}).status_code == 404
    assert client.get("/api/outreach-analytics", headers=login(client, "public")).status_code == 403


# ------------------------------------------------------------------ admin, storage, security
def test_admin_platform_health(client):
    r = client.get("/api/admin/platform-health", headers=login(client, "admin")).json()
    assert r["repository"]["public_source"] >= 15 and r["repository"]["demo"] > 0
    assert {"requests", "insufficient_evidence", "citation_validation_failures"} <= set(r["ai"])
    assert {"draft", "pending_review", "approved", "published"} <= set(r["content"])
    assert {"duplicate_candidates", "missing_metadata", "ocr_failures", "invalid_datasets"} <= set(r["data_quality"])
    assert r["repository"]["storage"]["backend"] == "local"
    assert client.get("/api/admin/platform-health", headers=login(client, "editor")).status_code == 403


def test_storage_keys_cannot_escape_root(tmp_path):
    from app.services.storage import LocalStorage, StorageError

    st = LocalStorage(str(tmp_path))
    assert st.save_bytes("datasets/a.csv", b"x") == "datasets/a.csv"
    for bad in ("../etc/passwd", "/abs/path", "a/../../b", "datasets/../../x"):
        with pytest.raises(StorageError):
            st.save_bytes(bad, b"x")


def test_cookie_session_with_csrf_guard():
    old = settings.AUTH_COOKIE_ENABLED
    settings.AUTH_COOKIE_ENABLED = True
    try:
        with TestClient(app) as c:
            r = c.post("/api/auth/demo-login", json={"role": "researcher"})
            assert r.status_code == 200 and "pn_session" in r.cookies
            assert "httponly" in r.headers["set-cookie"].lower() and "samesite=lax" in r.headers["set-cookie"].lower()
            assert c.get("/api/auth/me").json()["role"] == "researcher"  # cookie alone authenticates reads
            assert c.post("/api/saved", json={"item_type": "document", "item_slug": "x", "label": "x"}).status_code == 403
            ok = c.post("/api/saved", json={"item_type": "document", "item_slug": "antarctic-sea-ice-variability-study",
                                            "label": "Flagship"}, headers={"X-PolarNexus-Client": "web"})
            assert ok.status_code == 200
            c.post("/api/auth/logout", headers={"X-PolarNexus-Client": "web"})
            assert c.get("/api/auth/me").status_code == 401
    finally:
        settings.AUTH_COOKIE_ENABLED = old


def test_rate_limit_on_ai(client):
    from app.core.ratelimit import reset

    old = settings.RATE_LIMIT_AI_PER_MINUTE
    settings.RATE_LIMIT_AI_PER_MINUTE = 2
    try:
        reset()
        codes = [client.post("/api/ai/ask", json={"question": "What is sea ice?"}).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
    finally:
        settings.RATE_LIMIT_AI_PER_MINUTE = old
        reset()


def test_v3_migration_adds_columns_without_data_loss(tmp_path):
    """A v2-shaped database (no v3 columns/tables) is upgraded in place, rows preserved."""
    from sqlalchemy import create_engine, inspect, text

    from app.core.database import Base
    from app.core.migrations import migrate

    eng = create_engine(f"sqlite:///{tmp_path / 'v2.db'}")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE documents (id INTEGER PRIMARY KEY, slug VARCHAR(160), title VARCHAR(300))"))
        conn.execute(text("INSERT INTO documents (id, slug, title) VALUES (1, 'kept', 'Kept row')"))
    Base.metadata.create_all(eng)
    out = migrate(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("documents")}
    assert {"doi", "ocr_status", "content_hash", "metadata_only"} <= cols
    assert "documents.doi" in out["columns_added"] and out["schema_version"] == "2026.10-v3"
    with eng.connect() as conn:
        assert conn.execute(text("SELECT title, metadata_only FROM documents WHERE id = 1")).one() == ("Kept row", 0)
    assert {"research_stories", "campaigns", "resource_versions", "visual_embeddings"} <= set(inspect(eng).get_table_names())
