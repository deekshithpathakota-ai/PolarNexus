"""API tests. Run with:  pytest -q   (uses DATABASE_URL from env/.env; seeds a fresh demo database)."""
import io
import time

import pytest
from fastapi.testclient import TestClient

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


def test_health(client):
    h = client.get("/health").json()
    assert h["database"]["status"] == "ok"
    assert h["vector_search"]["embedding_model"]


def test_password_login_and_bad_password(client):
    assert client.post("/api/auth/login", json={"email": "editor@polarnexus.demo", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "editor@polarnexus.demo", "password": "polarnexus-demo"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "editor"


def test_search_and_filters(client):
    r = client.get("/api/search", params={"q": "Antarctic sea ice"}).json()
    assert r["results"][0]["slug"] == "antarctic-sea-ice-variability-study"
    ds = client.get("/api/search", params={"q": "Antarctic sea ice", "type": "Dataset"}).json()
    assert ds["total"] > 0 and all(x["type"] == "dataset" for x in ds["results"])
    arc = client.get("/api/search", params={"region": "Arctic", "year_from": 2023}).json()
    assert all(x["region"] == "Arctic" and x["year"] >= 2023 for x in arc["results"])
    for mode in ("keyword", "semantic", "hybrid"):
        assert client.get("/api/search", params={"q": "glacier melting", "mode": mode}).json()["total"] > 0


def test_internal_documents_hidden_from_public(client):
    pub = client.get("/api/resources/internal-draft-black-carbon-on-snow")
    assert pub.status_code == 404
    adm = client.get("/api/resources/internal-draft-black-carbon-on-snow", headers=login(client, "admin"))
    assert adm.status_code == 200


def test_rag_grounded_and_citations_valid(client):
    r = client.post("/api/ai/ask", json={"question": "How does the Southern Ocean absorb carbon dioxide?"}).json()
    assert r["evidence_status"] in {"strong", "limited"}
    import re
    markers = {int(n) for n in re.findall(r"\[(\d+)\]", r["answer"])}
    assert markers and markers <= {s["n"] for s in r["sources"]}
    for s in r["sources"]:
        assert client.get(f"/api{s['url']}" if s["url"].startswith("/resources") else "/health").status_code == 200


def test_rag_insufficient_evidence(client):
    r = client.post("/api/ai/ask", json={"question": "Who won the cricket world cup in 2011?"}).json()
    assert r["evidence_status"] == "insufficient" and r["sources"] == []
    assert "couldn't find sufficient supporting evidence" in r["answer"]


def test_document_scoped_question(client):
    r = client.post("/api/ai/document-question", json={"question": "What limitations are mentioned?",
                                                       "document_slug": "antarctic-sea-ice-variability-study"}).json()
    assert all(s["slug"] == "antarctic-sea-ice-variability-study" for s in r["sources"])
    assert r["sources"][0]["section"] == "Limitations"


def test_summary(client):
    r = client.post("/api/ai/summary", json={"document_slug": "antarctic-sea-ice-variability-study", "kind": "key-findings"}).json()
    assert r["text"] and r["sources"]


def test_rbac(client):
    assert client.post("/api/content/generate", json={"format": "public", "resource_slug": "what-is-polar-science"}).status_code == 401
    pub = login(client, "public")
    assert client.post("/api/content/generate", json={"format": "public", "resource_slug": "what-is-polar-science"}, headers=pub).status_code == 403
    assert client.get("/api/admin/users", headers=login(client, "editor")).status_code == 403
    assert client.get("/api/admin/audit-logs", headers=login(client, "admin")).status_code == 200


def test_full_content_workflow(client):
    res = login(client, "researcher")
    c = client.post("/api/content/generate", json={"format": "website", "resource_type": "document",
                                                   "resource_slug": "southern-ocean-carbon-dynamics"}, headers=res).json()
    assert c["status"] == "draft" and c["citations"] and c["evidence_check"]["checks"]
    # researcher cannot approve
    assert client.post(f"/api/reviews/{c['id']}/approve", json={}, headers=res).status_code == 403
    assert client.post(f"/api/content/{c['id']}/submit", headers=res).json()["status"] == "under_review"
    ed = login(client, "editor")
    assert client.post(f"/api/reviews/{c['id']}/publish", json={}, headers=ed).status_code == 409  # must approve first
    assert client.post(f"/api/reviews/{c['id']}/approve", json={}, headers=ed).json()["status"] == "approved"
    pub = client.post(f"/api/reviews/{c['id']}/publish", json={"channels": ["website", "linkedin"]}, headers=ed).json()
    assert pub["status"] == "published" and pub["channels"] == ["website", "linkedin"]
    assert any(x["id"] == c["id"] for x in client.get("/api/outreach", params={"page_size": 50}).json()["results"])
    logs = client.get("/api/admin/audit-logs", params={"action": "content_publish"}, headers=login(client, "admin")).json()
    assert logs["total"] >= 1


def test_request_changes_requires_comment(client):
    res = login(client, "researcher")
    c = client.post("/api/content/generate", json={"format": "student", "resource_slug": "how-sea-ice-changes-explainer"}, headers=res).json()
    client.post(f"/api/content/{c['id']}/submit", headers=res)
    ed = login(client, "editor")
    assert client.post(f"/api/reviews/{c['id']}/request-changes", json={"comment": ""}, headers=ed).status_code == 422
    assert client.post(f"/api/reviews/{c['id']}/request-changes", json={"comment": "Please simplify."}, headers=ed).json()["status"] == "changes_requested"


def test_evidence_check_flags_problems():
    from app.content.evidence_check import run_evidence_check
    ev = ["Sea ice reflects sunlight and limits heat exchange between ocean and atmosphere."]
    good = run_evidence_check("Sea ice reflects sunlight and limits heat exchange between the ocean and atmosphere [1].", ev, 1)
    assert good["overall"] == "pass"
    bad = run_evidence_check("This definitely proves that 87% of penguins will disappear from Greenland by next year [3].", ev, 1)
    ids = {c["id"]: c["status"] for c in bad["checks"]}
    assert ids["citation_integrity"] == "fail" and ids["numbers"] == "warn" and ids["overclaiming"] == "warn"


def _pdf_bytes(text: str) -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 800), text, fontsize=10)
    out = doc.tobytes()
    doc.close()
    return out


def test_ingestion_pdf_and_rejections(client):
    res = login(client, "researcher")
    bad = client.post("/api/ingestion/upload", files={"file": ("evil.exe", b"MZ....", "application/octet-stream")}, headers=res)
    assert bad.status_code == 422
    fake = client.post("/api/ingestion/upload", files={"file": ("fake.pdf", b"not a pdf at all", "application/pdf")}, headers=res)
    assert fake.status_code == 422 and "signature" in fake.json()["detail"]
    text = ("Kongsfjorden Glacier Front Observations 2025\n\nAbstract\nThis report describes summer observations of a "
            "tidewater glacier front in Kongsfjorden, Svalbard, near the Himadri station. Meltwater plumes freshened the "
            "surface layer and turbidity increased near the calving front during July. " * 3)
    r = client.post("/api/ingestion/upload", files={"file": ("kongsfjorden-2025.pdf", _pdf_bytes(text), "application/pdf")},
                    data={"doc_type": "Technical Report"}, headers=res)
    assert r.status_code == 200, r.text
    job = r.json()
    for _ in range(60):
        job = client.get(f"/api/ingestion/jobs/{job['id']}", headers=res).json()
        if job["status"] != "processing":
            break
        time.sleep(0.5)
    assert job["status"] == "completed", job
    slug = job["document"]["slug"]
    doc = client.get(f"/api/resources/{slug}").json()
    assert doc["region"] == "Arctic" and doc["sections"]
    hits = client.get("/api/search", params={"q": "meltwater plumes calving front turbidity"}).json()
    assert any(h["slug"] == slug for h in hits["results"][:5])
