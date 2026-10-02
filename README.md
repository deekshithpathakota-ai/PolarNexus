# PolarNexus — SIH26063 Prototype

**Integrated Polar Science Outreach, Knowledge Repository and Media Dissemination Portal**
*From Polar Research to Public Understanding.*

PolarNexus is a full-stack prototype of an **integration, discovery, intelligence and outreach layer** for polar knowledge. It does not replace existing institutional polar-data systems. It shows how documents, datasets, expeditions, stations and media can be:

1. **unified** in one metadata-rich repository,
2. **discovered** through hybrid keyword + semantic search,
3. **understood** with evidence-grounded AI (RAG), where every claim cites a source passage,
4. **turned into outreach** (student, public, social, media formats), and
5. **disseminated only after human review**.

> ⚠️ **Prototype demonstration data — clearly separated from real records.** Documents, most datasets (synthetic values), illustrated media, researchers and most expedition details are illustrative and labelled *Demo* / *Synthetic*. Station facts marked *verified* are limited to widely published, high-level facts. **v3 adds real, publicly accessible records labelled *Public source*:** NSIDC Sea Ice Index v4 monthly extent files (values unmodified), 11 openly licensed Wikimedia Commons photographs (licence, author and source page shown), and metadata-only catalogue entries for official resources (Indian Antarctic Act 2022, India's Arctic Policy, NCPOR, the Antarctic Treaty Secretariat, NSIDC). Nothing here is an official NCPOR/MoES record.

**Journey:** DISCOVER → UNDERSTAND → VERIFY → CREATE → REVIEW → DISSEMINATE → MEASURE.

---

## Contents
- [Architecture](#architecture)
- [Features](#features-implemented)
- [Local setup](#local-setup)
- [Environment variables](#environment-variables)
- [Database & seed data](#database--seed-data)
- [Deployment](#deployment)
- [Demo accounts](#demo-accounts)
- [Hackathon demo flow](#hackathon-demo-flow-3-minutes)
- [Testing](#testing)
- [Implemented vs demonstration](#implemented-vs-demonstration-functionality)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)

---

## Architecture

```
 Browser ──► Next.js 15 (TypeScript, Tailwind)          ──/api/* rewrite──►  FastAPI (Python 3.11)
            Vercel                                                         Render / Railway / Docker
                                                                               │
              ┌────────────────────────────────────────────────────────────────┤
              │ auth/      JWT bearer + HttpOnly session cookie (CSRF header guard), bcrypt, RBAC
              │ search/    keyword (Postgres FTS, BM25 fallback) + vector + CLIP visual → RRF fusion,
              │            authority weighting, "why this matched"
              │ rag/       embeddings (OpenAI-compatible | offline LSA) · pgvector store · grounded answering
              │            · evidence sufficiency + 4-level strength · citation validation · audience modes
              │ content/   outreach generator (LLM | template) · heuristic evidence check
              │ ingestion/ documents (PyMuPDF → OCR fallback) · media (EXIF/ffprobe → key frames → CLIP)
              │            · datasets (CSV/JSON → schema → validation → confirm → register)
              │ services/  provenance · versions (append-only) · FAIR metadata · lineage · duplicates
              │            · storage (local | S3-compatible) · stories · visual (CLIP, fastembed/ONNX)
              │ api/       REST routers · audit log · analytics · campaigns · notifications
              ▼
        PostgreSQL 16 + pgvector   (SQLite + in-process numpy fallback)
```

**RAG pipeline:** question → intent and term extraction → query embedding → vector search (pgvector `<=>`) + full-text search → hybrid fusion (RRF) → evidence assessment (IDF-weighted term coverage, out-of-domain check) → generation (LLM, or extractive/curated without a key) → **citation validation** (any `[n]` that doesn't map to a retrieved passage is removed) → answer + sources + evidence status + related knowledge.

```
backend/app/
  main.py            app, CORS, error handlers, lifespan (auto-seed)
  core/              config (env), database (engine, pgvector detection, EmbeddingType)
  models/            user, knowledge, workflow, telemetry  (18+ tables)
  schemas/           Pydantic request/response models
  auth/              JWT, password hashing, permissions
  api/               auth, knowledge, misc (search/health/notifications/saved/education),
                     ai, workflow (content + reviews + outreach), ingestion, admin
  search/            keyword.py, hybrid.py, service.py (resource-level search, facets, suggest)
  rag/               embeddings.py, llm.py, vector_store.py, indexer.py, answer.py,
                     summary.py, simplify.py, curated.py
  content/           generator.py, evidence_check.py
  ingestion/         pipeline.py
  services/          catalog (cards, relationships, filters), audit, serializers
  seed/              documents, entities, datasets_media, education, seed_demo_data
frontend/src/
  app/               26 routes (public, professional, admin)
  components/        layout · common · search · cards · ai · content · charts · maps · art
  lib/               api client, auth context, hooks, types, formatting
```

---

## Features (implemented)

| Area | What works |
|---|---|
| **Home** | Hero with live search and autocomplete, rotating globe (offline), repository stats (labelled demo), the 7-step "one knowledge layer" pipeline, featured research, regions, AI and outreach previews |
| **Explore / Smart Search** | Keyword · Semantic · Hybrid modes; filters for region, type, topic, year range, station, expedition, language and data type (all applied server-side); facet counts; sort; pagination; highlighted matches; matching concepts; save search; recent searches; suggestions |
| **Resource detail** | Metadata, abstract, key findings, full text by section and page, topics, linked stations/expeditions/datasets/researchers, related-knowledge list and **graph view**, save/share/cite/download |
| **AI Assistant** | Repository-wide and document-scoped questions; citations open the exact passage; evidence status (strong / limited / insufficient); insufficient-evidence handling with suggestions; metadata answers ("which expeditions…", "major themes…"); figure questions; copy, regenerate and feedback |
| **Summaries** | Executive, research, student, 100-word, key findings, methodology, impact, each grounded in the document's own sections |
| **Datasets** | 16 datasets / 2,514 records; time-series, scatter and geographic charts; variable selector, date range, value filters; paginated record table; CSV download |
| **Media** | 43 items (images, videos, infographics), category and type filters, detail pages with linked knowledge |
| **Expeditions** | Decade timeline grouped by programme; detail pages with highlights, provenance notes and linked records |
| **Stations** | 9 stations/locations (7 verified-fact records + 2 labelled demo sites), counts of linked resources, mini map |
| **Polar Map** | Antarctic and Arctic azimuthal projections plus a world view; station, expedition and dataset layers; topic filter; zoom; info panel. Fully offline (bundled Natural Earth), with a coordinate-list fallback |
| **Learn** | Beginner, intermediate and advanced paths; lessons link to records; quizzes with source-cited explanations |
| **Content Studio** | Source picker (document, dataset or topic) → 6 formats → staged generation → editor (Markdown) → sources panel → **evidence check** → submit |
| **Review Center** | Queue by status; approve, request changes or reject (comment required); editor can edit; publish to channels; full history |
| **Outreach Feed** | Public page of published, editor-approved content with sources |
| **Researcher Workspace** | Real file upload (PDF/TXT/MD) with live 9-step pipeline progress |
| **Admin** | Dashboard KPIs and charts; repository management (add, edit metadata, archive, restore, delete, re-index); users and roles (RBAC, activate/deactivate); analytics; audit logs (filter/search/paginate); system health; demo reset |
| **Institutional Activities** *(v2)* | 13 activity types (workshops, seminars, conferences, exhibitions, school outreach, lectures, campaigns, expedition briefings, announcements, training, events, achievements); list with search, filters (type, year, organisation, location, topic, verification, status) and sorting; detail pages linked to researchers, expeditions, stations, documents, datasets, media and topics; admin create / edit / feature / archive / restore / delete, all audit-logged |
| **Media ingestion** *(v2)* | Upload JPG/PNG/WEBP/TIFF (≤ 20 MB) and MP4/MOV/WEBM (≤ 200 MB), streamed to disk; extension + magic-byte + MIME + Pillow-decode validation; EXIF (camera, capture time, GPS → map position); thumbnails; video metadata, poster frame and audio via ffmpeg; transcript from an uploaded .vtt/.srt/.txt or speech-to-text when an API key is set; background processing with live status (Processing → Extracting metadata → Generating transcript → Indexing → Ready / Failed + Retry); indexed into the same hybrid search |
| **Provenance & verification** *(v2)* | One provenance record per resource (source organisation/type/URL, identifier, licence, publication/collection/import dates, verification status, verifier, data quality, notes); "Data Provenance" panel on every detail page; 7 verification states; Verified / Official / Partner / Uploaded / Pending / Demo / Synthetic filters; admin Provenance & Verification Centre. **Demo and synthetic records cannot be marked Verified or Partner — enforced by the API** |
| **Unified multimodal search** *(v2)* | One search across documents, datasets, images, videos, expeditions, stations, researchers, institutional activities, topics and published outreach; per-type result counts; new filters (verification, organisation, researcher, activity type) alongside every existing one; existing keyword / semantic / hybrid + RRF ranking unchanged |
| **Cross-modal AI synthesis** *(v2)* | Answers group "Related Knowledge" by type (documents, datasets, expeditions, stations, media, researchers, activities); compound questions ("How has X changed **and which expeditions** studied it?") answer the first part from passages and append the connected entities, each cited to its own record; citation validation and insufficient-evidence refusal unchanged; activities, topics and AI-generated outreach are searchable but never used as evidence |
| **Research → Outreach** *(v2)* | "Turn Research Into Outreach" on document, dataset, expedition, station, researcher, activity, topic pages and from any AI answer (its cited passages); 10 content types and 6 audiences; workflow stepper; `evidence_checked` state; per-claim evidence ("[Document, p. 12]") with ⚠ Unsupported claim + Remove; channels shown as **Website LIVE / LinkedIn · Instagram · Newsletter CONNECTOR READY (prototype simulation)**; public detail page per published item; translation drafts (Hindi/Telugu) that always require human review |
| **Knowledge Timeline** *(v2)* | Chronological, clickable record view for any topic, expedition, station or researcher, filterable by year range and resource type; on topic/expedition/station/researcher pages and at `/timeline` |
| **Impact & KPIs** *(v2)* | `/impact`: resources by type and verification, AI usage (grounded vs insufficient, citation validation rate on live answers), content workflow counts, discovery, **measured** search/AI latency (live requests only), qualitative before/after table. Labelled "Prototype Demonstration Metrics" |
| **Graph, map, i18n** *(v2)* | Graph includes activities, topics and published outreach (click to open); map adds media and activity layers with verification in the popup; English/Hindi/Telugu navigation switch (English default; content is never machine-translated outside the reviewed workflow) |
| **Public-source data** *(v3)* | NSIDC Sea Ice Index v4 (Antarctic Feb/Sep, Arctic Sep, 1979–2026) ingested through the CSV pipeline with values unmodified; 11 Wikimedia Commons photographs (CC/PD/GODL-India) with licence, author, date, source page and written alt text; 6 metadata-only official resources. New verification status **Public source** (filterable), never confused with Demo/Synthetic |
| **Visual semantic search** *(v3)* | CLIP ViT-B/32 (ONNX via `fastembed`, no PyTorch). Photos are embedded on ingestion; videos are split into representative key frames (scene changes + even sampling, capped) with timestamps. `/visual-search` and the Media page find images from a description ("iceberg near a research vessel") even when the words are not in the metadata; video hits show "Relevant frame — 02:14". Visual relevance joins hybrid search as an extra RRF list. Unavailable → reported, never faked |
| **Hybrid ranking v3** *(v3)* | Verified / partner / public-source records get a modest authority multiplier (demo never does); every result explains "Why this matched" (keyword terms, title, semantic similarity, visual similarity + frame, topic, station/expedition filter match, source status) |
| **AI v3** *(v3)* | `LLM_PROVIDER/LLM_API_KEY/LLM_BASE_URL/EMBEDDING_*` (OpenAI-compatible); 4-level evidence strength (strong · moderate · limited · insufficient — rule-based, not a probability) alongside the unchanged 3-level status; evidence basis (how many cited records are demo vs public/verified, with a warning when all are demo); a visible pipeline trace; Researcher / Teacher / Student / Public modes (teacher mode adds teaching points quoted from sources and discussion questions); per-source verification badges |
| **Research Stories** *(v3)* | Build a story from any record: topic → paper → dataset → expedition → station → photographs → video → researchers, from real graph links (editable). Scientific / Public / Student explanations generated only from the primary paper's cited sections; timeline, map, evidence list, evidence basis; drafts are private, editors publish; archive never deletes |
| **Campaign Planner & Content Calendar** *(v3)* | Campaigns (dates, audiences, topics, channels, draft/scheduled/published/archived), calendar items linked to outreach content. **An item can be scheduled only after an editor approved its content**; publishing calls the Review Center's publish transition. Website is live; Social / Newsletter / Educational Portal are labelled simulations. Month grid on desktop, agenda on mobile |
| **Outreach Impact Analytics** *(v3)* | Views, clicks, shares, engagement and completion by campaign, content, audience, channel, format and week; popular topics; research-to-content conversion. Published pages record real view/click/share/complete events; seeded engagement is flagged and the dashboard shows **DEMO METRICS** (toggle to live-only) |
| **Dataset ingestion** *(v3)* | CSV / TSV / JSON / GeoJSON: format detection, schema + column-type inference, lat/lon/time detection (incl. year+month), preview, validation (missing values, duplicate rows, invalid numbers/dates/coordinates, mixed types, fill values), user-supplied units (never guessed), confirm → background registration → indexing → explorer. Parser registry ready for NetCDF |
| **OCR** *(v3)* | Scanned PDF pages (too little embedded text) are rendered at 200 dpi and read by tesseract; page numbers kept so citations still say "p. 17"; OCR status shown on the document and job |
| **Scientific trust** *(v3)* | Append-only **version history** (import, metadata correction, new file, verification change; snapshots never overwritten); **FAIR metadata** (Dublin Core + DataCite-style DOI/version, completeness, missing fields shown as missing, ORCID only if stored); **provenance pipeline** Source → Ingestion → Processing → Transformation → AI Generation → Human Review → Publication with "Generated from" for outreach |
| **Duplicate detection** *(v3)* | Content hash, DOI, title / file-name similarity and text overlap for documents (pre-upload check), datasets (at analysis) and media; *Keep both · Update existing (new version) · Review · Cancel*; nothing is merged or deleted automatically |
| **Admin platform health** *(v3)* | Repository (verified/public/pending/demo, failed ingestion, queue, storage durability), AI (requests, retrieval success, insufficient evidence, citation-validation failures, LLM/visual/OCR status, rebuild visual index), content states, data quality (duplicate candidates, missing metadata, OCR failures, invalid datasets) |
| **Premium sign-in** *(v3)* | Polar-science scene: dark sky, CSS aurora, ice-shelf silhouette, a small canvas of snow + "observation" particles with faint links, a slowly rotating polar graticule; logo fade/scale, card fade/rise/blur-to-clear, input focus glow, polar-light sheen on the button, PolarNexus loading state. Reduced motion → static scene; fewer particles on small screens; capped at ~30 fps and paused when hidden. Auth logic unchanged |
| **Platform** | RBAC on every endpoint; audit logging; notifications; saved items and search history ("My Knowledge"); loading, empty and error states everywhere; error boundaries; 404 page; responsive layout with mobile bottom nav |

---

## Local setup

**Requirements:** Node.js ≥ 20, Python 3.11+, PostgreSQL 16 with `pgvector` (recommended) — or nothing extra, using SQLite.

### 1. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-visual.txt                   # optional: CLIP visual search (~350 MB model download on first use)
# optional system tools: ffmpeg (video), tesseract-ocr (OCR) — e.g. apt install ffmpeg tesseract-ocr
cp .env.example .env                                     # set DATABASE_URL and JWT_SECRET
python -m app.seed.seed_demo_data                        # optional: the API auto-seeds an empty DB
uvicorn app.main:app --reload --port 8000                # http://localhost:8000/docs
```
For a zero-dependency run, leave `DATABASE_URL` unset: SQLite is used and vector search runs in-process.

Postgres with pgvector quickly: `docker run -d -p 5432:5432 -e POSTGRES_USER=polar -e POSTGRES_PASSWORD=polar -e POSTGRES_DB=polarnexus pgvector/pgvector:pg16`

### 2. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local                               # BACKEND_URL=http://127.0.0.1:8000
npm run dev                                              # http://localhost:3000
```

### Everything with Docker
```bash
docker compose up --build        # db + backend + frontend → http://localhost:3000
```

---

## Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | backend | Postgres URL (`postgres://` or `postgresql://`). Unset = SQLite |
| `JWT_SECRET` | backend | **Required in production.** Long random string |
| `DEMO_MODE` | backend | `true` enables demo accounts, auto-seed and demo reset |
| `DEMO_USER_PASSWORD` | backend | Password for seeded demo users (default `polarnexus-demo`) |
| `CORS_ORIGINS` | backend | Comma-separated origins (`*.vercel.app` is also allowed) |
| `OPENAI_API_KEY` | backend | Optional. Enables LLM generation and neural embeddings |
| `OPENAI_BASE_URL` / `LLM_MODEL` / `EMBEDDING_MODEL` | backend | Any OpenAI-compatible provider |
| `STORAGE_DIR`, `MAX_UPLOAD_MB` | backend | Upload storage and limit |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | backend | v3 provider-neutral LLM settings (OpenAI-compatible). `LLM_PROVIDER=none` forces the offline fallback |
| `EMBEDDING_PROVIDER` / `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | backend | Neural embeddings via an API, or `local` for offline LSA |
| `VISUAL_SEARCH_PROVIDER` (`auto`/`clip`/`none`), `VISUAL_IMAGE_MODEL`, `VISUAL_TEXT_MODEL`, `VISUAL_MODEL_CACHE`, `VISUAL_MIN_SIMILARITY`, `VIDEO_MAX_KEYFRAMES` | backend | CLIP visual search (needs `pip install -r requirements-visual.txt`) |
| `OCR_ENABLED`, `OCR_LANGUAGES`, `OCR_MIN_CHARS_PER_PAGE`, `OCR_MAX_PAGES` | backend | OCR for scanned PDFs (needs the `tesseract` binary) |
| `MAX_DATASET_MB`, `MAX_DATASET_ROWS` | backend | Dataset ingestion limits |
| `STORAGE_BACKEND` (`local`/`s3`), `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_PREFIX` | backend | Object storage (needs `pip install -r requirements-s3.txt`) |
| `RATE_LIMIT_AI_PER_MINUTE`, `RATE_LIMIT_UPLOADS_PER_MINUTE` | backend | Per-IP limits for AI and uploads (0 disables) |
| `AUTH_COOKIE_ENABLED`, `AUTH_COOKIE_NAME` | backend | HttpOnly session cookie alongside the bearer token |
| `BACKEND_URL` | frontend | Where `/api/*` is proxied (server-side; never exposed) |
| `NEXT_PUBLIC_API_URL` | frontend | Optional direct browser → API calls |
| `NEXT_PUBLIC_BRAND_NAME` | frontend | Rename the product in the UI (e.g. `PolarVerse`) |

No secrets are committed. API keys live only on the backend.

---

## Database & seed data

Tables: `users, roles, documents, document_chunks (embedding vector), embedding_models, datasets, dataset_records, media, expeditions, stations, researchers, topics, resource_topics, resource_links, generated_content, citations, reviews, ingestion_jobs, notifications, saved_items, audit_logs, searches, analytics_events, ai_queries`, with foreign keys, cascade rules and indexes (including a GIN full-text index on chunks in Postgres).

```bash
python -m app.seed.seed_demo_data            # drop + recreate + seed (≈10 s)
python -m app.seed.seed_demo_data --if-empty # seed only if there are no users
```
v2 adds `institutional_activities`, `provenance` and `schema_migrations`, plus ingestion columns on `media`, `audience/language/translated_from` on `generated_content`, `page` on `citations` and `duration_ms` on `searches`/`ai_queries`. **Existing databases are upgraded in place on start-up** (columns added, demo activities and provenance rows added, nothing dropped or reset).

Seed contents: 14 institutional activities, a provenance record for every resource, 32 documents (one fully connected flagship: *Antarctic Sea Ice Variability Study*), 16 datasets / 2,514 synthetic records, 43 media, 16 expeditions, 9 stations/locations, 16 researchers, 24 topics, 307 typed relationships, 9 outreach items across all workflow states (generated by the real generator), 90 days of demo analytics, audit history, notifications and saved items. Admins can also reset from **System Health → Reset & reseed**.

---

## Deployment

**Recommended:** frontend on **Vercel**, API on **Render** (or Railway), database on **Render Postgres / Supabase / Neon** (all support `pgvector`).

1. **Database + API (Render):** push this repo, then *New → Blueprint* and select `render.yaml`. It creates Postgres and the API with a generated `JWT_SECRET`. After the first deploy, set `CORS_ORIGINS` to your Vercel URL, and optionally `OPENAI_API_KEY`. The API seeds the demo data automatically on first boot. Health check: `/health`.
   *Railway / Docker:* use `backend/Dockerfile` (respects `$PORT`) with the same env vars.
   *Supabase DB:* use the connection-pooler URI as `DATABASE_URL`; `pgvector` is enabled automatically if permitted.
2. **Frontend (Vercel):** import the repo, set **Root Directory = `frontend`**, add env `BACKEND_URL=https://<your-api>.onrender.com` (and optionally `NEXT_PUBLIC_BRAND_NAME`), then deploy. All deep links work on refresh: every route is an App Router page.
3. **Verify:** open `/health` on the frontend domain (it is proxied to the API), sign in with a demo account, and run the demo flow below. Before a live demo, open the site once to wake free-tier instances.

---

## Demo accounts

Enabled when `DEMO_MODE=true`. Use the one-click buttons on **/login**, or sign in by email with the password from `DEMO_USER_PASSWORD` (default `polarnexus-demo`):

| Role | Email | Can |
|---|---|---|
| Public | `public@polarnexus.demo` | search, explore, read, ask AI |
| Researcher | `researcher@polarnexus.demo` | + upload, manage own uploads, create outreach drafts, save |
| Editor | `editor@polarnexus.demo` | + review, edit, approve/reject, publish |
| Administrator | `admin@polarnexus.demo` | everything, incl. repository, users, analytics, audit, health |

Signed-in demo users can switch roles instantly from the user menu (top right).

---

## Hackathon demo flow (≈3 minutes)

1. **Home**: "Explore India's Polar Science". Point to the pipeline strip (Research → … → Dissemination).
2. Search **`Antarctic sea ice`** and show hybrid ranking, match reasons and filters (tick *Dataset*).
3. Open **Antarctic Sea Ice Variability Study**: metadata, abstract, key findings, linked station/expedition/dataset, graph view.
4. Click **Ask PolarNexus AI** and ask *"Explain the key factors discussed in this resource."*
5. Show the **evidence status**, then click citation chips to open the exact source passages.
6. (Optional) **AI Summaries → Student-Friendly**; ask *"Who won the cricket world cup?"* on /assistant to show **insufficient evidence**.
7. Sign in as **Researcher**, then click **Turn Research Into Outreach**.
8. Choose **Student**, then **Generate draft**.
9. Show the draft, the **Sources** panel and the **Evidence check**.
10. **Submit for review**.
11. Click **Switch to Editor (demo) & review** to open the **Review Center**.
12. **Approve**, then **Publish / Disseminate** (website + LinkedIn — social is simulated).
13. Open the **Outreach Feed** to show the published item with its sources, then sign in as **Admin** and show **Dashboard / Analytics / Audit Logs**.

**v2 additions (≈2 more minutes)**

14. On the resource page, point to the **Data Provenance** panel ("Demo data" — never presented as official); open **Maitri** to show an *Official · verified* station fact record.
15. On **/assistant** ask *"How has Antarctic sea ice changed and which expeditions studied it?"* — a cited synthesis plus the connected expeditions and **Related Knowledge** grouped by type.
16. Open **Institutional Activities** → *Teaching Antarctic Sea Ice* workshop: linked research, people, media, graph.
17. Open **Topics → Sea Ice** (or **/timeline**) for the **Knowledge Timeline**.
18. **Researcher Workspace → Image / Video**: upload a photo and watch the pipeline reach *Ready*; find it in search.
19. **Impact & KPIs**: labelled demonstration metrics, measured latencies, before/after workflow table.
20. As Admin, **Provenance & Verification**: try to mark a synthetic dataset Verified — the API refuses.

---

## Testing

```bash
cd backend && pip install -r requirements-dev.txt && pytest -q          # 61 API tests (13 original + 21 v2 + 27 v3)
BASE_URL=http://localhost:3000 npm run e2e:v3        # (frontend) v3 journey: sign-in, why-matched, public data, teacher mode,
                                                    # stories, visual search, dataset ingestion, campaigns, analytics, admin, mobile
cd frontend && npm run typecheck && npm run lint && npm run build
cd frontend && npx playwright install chromium
BASE_URL=http://localhost:3000 npm run e2e            # original demo flow + 25-route smoke + mobile checks
BASE_URL=http://localhost:3000 npm run e2e:journey    # v2 lifecycle journey + new pages + mobile checks
```
`tests/test_v2.py` covers institutional activities (CRUD, filters, RBAC, audit), image ingestion (EXIF/GPS, thumbnail, search), upload validation (type, signature, decode, MIME mismatch, size, path traversal), video ingestion with a transcript (when ffmpeg is installed), provenance labels and the demo-cannot-be-verified guard, verification filters, unified search across every type, topic pages and the timeline, cross-modal AI synthesis, grounding/refusal, the full outreach workflow (evidence check, review, approval, rejection, publishing state, simulated channels), translation drafts, the impact dashboard, graph/map layers, RBAC on new admin APIs, login throttling and the additive migration on a v1-shaped schema.
The backend tests cover search and filters, internal-document visibility, RAG citations, insufficient evidence, document-scoped questions, RBAC, the full draft → review → publish workflow, request-changes validation, evidence-check flags, and real PDF ingestion with upload rejections. The e2e script walks the whole demo flow, smoke-tests 25 routes, and checks 10 pages for horizontal overflow at 390 px.

Verified during development: tests pass on PostgreSQL 16 + pgvector **and** on SQLite (no pgvector); the LLM path was tested against a mock OpenAI-compatible server (a fabricated `[9]` citation was stripped); an unreachable LLM falls back to extractive answers and keyword search with visible notices; the e2e suite passes against the production build (`next start`) with 0 console errors.

---

## v3 demo flow (≈4 minutes)

1. **/login** — the polar sign-in (aurora, particles, grid); click *Researcher Demo*.
2. Search **`Antarctic sea ice`** — open a card's *Why this matched*; note **Public source** next to **Demo** records.
3. Open **Sea Ice Index v4 — Antarctic … September** — real NSIDC values, *Public source* provenance, *Scientific trust* → Pipeline / Versions / Metadata (DOI shown as *missing*, not invented).
4. **/assistant**, mode **Teacher**: *"What factors influence Antarctic sea-ice variability?"* — strength pill, the demo-evidence warning, teaching points, *How this answer was produced*.
5. **Research Stories** → the demo story: chain, Public / Student explanations with citations, timeline, map, evidence basis.
6. **Visual Media Search**: *"iceberg near a research vessel"* → the RRS Ernest Shackleton photo, although "vessel" is not in its metadata.
7. **Researcher Workspace → Dataset**: upload a CSV → schema, validation issues, preview → add units → confirm → explore.
8. **Content Studio → Evidence check → Review** (unchanged v2 flow).
9. **Campaign Planner** → *Antarctic Science Week 2026 (demo)*: an unapproved item cannot be scheduled; simulated channels are labelled; **Content Calendar**.
10. **Outreach Analytics** (*DEMO METRICS* badge; untick to see live-only), then as Admin the **Dashboard** health panels.

## Implemented vs demonstration functionality

| Real, working | Demonstration / simulated (labelled in the UI) |
|---|---|
| Hybrid search (Postgres FTS / BM25 + pgvector / numpy, RRF), filters, facets | Corpus content: documents, researchers and most expedition details are illustrative |
| RAG with retrieval, evidence assessment, **citation validation**, insufficient-evidence handling | Without an LLM key: answers are **extractive** (quoted sentences), plus 2 **curated demo responses** for the flagship flow, labelled "Demo response" |
| Offline semantic embeddings (TF-IDF + LSA) — real vectors stored in pgvector | Dataset values are **synthetic** (seasonal cycles + noise) |
| Outreach generation (LLM, or template assembly from source sentences) | Media images are **original generated SVG artwork**; video "playback" is a preview |
| Evidence check (lexical support, numbers, citation integrity, overclaiming, region scope) | The evidence check is a **heuristic**, not scientific verification (stated in the UI) |
| Review workflow, RBAC, audit log, notifications, ingestion of PDF/TXT/MD | Publishing to LinkedIn/Instagram/newsletter is **simulated** ("connector ready"); website publishing (Outreach Feed) is real |
| Image/video ingestion, EXIF, thumbnails, ffprobe metadata, transcript indexing | Speech-to-text runs only with an API key; otherwise speech is searchable only from an attached transcript (stated in the UI) |
| Provenance records, verification workflow, demo/synthetic guard | Institutional activities are demonstration records (fictional "(demo)" organisers, generic venues) |
| Timeline and impact metrics computed from the database; latency measured on live requests | Hindi/Telugu cover the navigation only and are a prototype translation pending native-speaker review |
| Analytics computed from DB events | Historical analytics are seeded demo activity (labelled "Prototype Demonstration Analytics") |
| *(v3)* NSIDC datasets, Commons photographs, official-resource records — real, labelled *Public source* | Metadata-only records store a short neutral description, not the full text |
| *(v3)* CLIP visual search, key frames, OCR, CSV/JSON ingestion, duplicates, versions, FAIR, lineage, stories, campaigns, cookie sessions, rate limits | Outreach engagement seeded for the demo campaign is synthetic and shown as **DEMO METRICS**; Social/Newsletter/Educational-Portal publishing is simulated |

---

## Known limitations

- **No live deployment from this build environment**: deployment configs are included and the production build was tested locally, but the Vercel/Render URLs must be created from your accounts.
- *(v3)* OCR needs the `tesseract` binary (installed by the Dockerfile; absent on Render's native runtime → scanned PDFs fail with a clear message). Handwriting and poor scans may OCR badly; OCR text is labelled.
- *(v3)* Visual search needs the optional `fastembed` package and a one-time ~350 MB model download; CLIP ViT-B/32 is a general model — similarity scores are relevance, not certainty. Illustrated demo media has no image file and is not visually indexed. Render's free tier is configured with `VISUAL_SEARCH_PROVIDER=none` (memory).
- *(v3)* NetCDF/HDF5 datasets are not supported yet (the parser registry is ready). Dataset registration keeps up to `MAX_DATASET_ROWS` rows.
- *(v3)* The S3 storage backend is implemented but was **not tested against a real bucket** in this build environment. Existing v1/v2 pipelines write locally and mirror to S3 when configured.
- *(v3)* Knowledge graph, map and timeline gained the new public-source records automatically (they flow through the same catalogue) but no new layout features; campaign items are not on the knowledge timeline.
- *(v3)* Hindi/Telugu cover the navigation (now including the new pages) and are pending native-speaker review; machine translations of outreach are kept only if citation markers, numbers and units survive.
- Video processing needs `ffmpeg`/`ffprobe` on the API host (installed by the Dockerfile; on Render's native Python runtime it is usually absent — those steps are then shown as skipped). Speech-to-text needs `OPENAI_API_KEY`.
- Uploaded media files are served by the API. Browsers load them without the auth header, so internal-visibility uploads are viewable by their uploader only through the API, not inline.
- Uploaded files are stored on local disk; on free hosting tiers they are lost on restart (extracted text and index remain in the database). S3/Supabase storage is configured in env but not implemented.
- Institutional SSO is not implemented (JWT accounts only). *(v3)* An HttpOnly, SameSite=Lax session cookie (Secure in production) is now issued alongside the bearer token, so media files load for their uploader; the SPA still keeps the bearer token in `localStorage` for backward compatibility — removing it is a follow-up.
- *(v3)* Rate limiting is in-memory per API instance; multi-instance deployments need a shared limiter.
- Offline LSA embeddings capture co-occurrence, not deep meaning. Configure an embedding API for production-quality semantic search, then **Admin → Repository → Rebuild index**.
- Multilingual support is a foundation: the navigation shell switches to Hindi/Telugu and outreach can be drafted as a translation (machine-translated only with an LLM, citation markers verified; always human-reviewed). Page content and the corpus remain English.
- Schema changes use an additive start-up migrator (`app/core/migrations.py`, recorded in `schema_migrations`), not Alembic. It only adds tables/columns and runs idempotent backfills. *(v3)* Verified: a v2 PostgreSQL database upgrades in place (all rows kept, public-source records, demo story/campaign and version baselines added).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Unable to reach the PolarNexus service" | Check `BACKEND_URL` on the frontend and `/health` on the API. Free tiers sleep, so open the API URL first and wait ~1 minute |
| Login works, then 401s | `JWT_SECRET` changed between restarts; sign in again |
| Health shows vector search `in-process numpy` | pgvector isn't installed or permitted; search still works. Enable the `vector` extension for pgvector |
| Health shows AI provider `fallback` | No `OPENAI_API_KEY`: expected; answers are extractive or curated demo, and are labelled |
| Empty repository | Run `python -m app.seed.seed_demo_data` or use Admin → System Health → Reset & reseed |
| Upload rejected | Only PDF/TXT/MD ≤ 25 MB; PDFs must have a real `%PDF` signature and extractable text |
| Media upload rejected | Images JPG/PNG/WEBP/TIFF ≤ 20 MB, videos MP4/MOV/WEBM ≤ 200 MB; the file content must match its extension and decode |
| Video shows "skipped: ffmpeg not installed" | Install ffmpeg on the API host (the Dockerfile does) and use **Retry processing** |
| `RuntimeError: JWT_SECRET must be set` | `ENVIRONMENT=production` refuses the default secret — set a long random `JWT_SECRET` |
| HTTP 429 on sign-in | 10 failed attempts per IP+email within 5 min; wait, or tune `LOGIN_MAX_FAILURES` |
| CORS errors (only with `NEXT_PUBLIC_API_URL`) | Add the frontend origin to `CORS_ORIGINS`, or leave `NEXT_PUBLIC_API_URL` empty to use the proxy |
