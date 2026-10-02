# PolarNexus — SIH26063 Prototype

**Integrated Polar Science Outreach, Knowledge Repository and Media Dissemination Portal**
*From Polar Research to Public Understanding.*

PolarNexus is a full-stack prototype of an **integration, discovery, intelligence and outreach layer** for polar knowledge. It does not replace existing institutional polar-data systems. It shows how documents, datasets, expeditions, stations and media can be:

1. **unified** in one metadata-rich repository,
2. **discovered** through hybrid keyword + semantic search,
3. **understood** with evidence-grounded AI (RAG), where every claim cites a source passage,
4. **turned into outreach** (student, public, social, media formats), and
5. **disseminated only after human review**.

> ⚠️ **Prototype demonstration data.** Documents, datasets (synthetic values), media (original generated artwork), researchers and most expedition details are illustrative. Station facts marked *verified* are limited to widely published, high-level facts (location, approximate coordinates, year established). Nothing here is an official NCPOR/MoES record.

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
              │ auth/      JWT + bcrypt, RBAC (public · researcher · editor · admin)
              │ search/    keyword (Postgres FTS, BM25 fallback) + vector → Reciprocal Rank Fusion
              │ rag/       embeddings (OpenAI-compatible | offline LSA) · pgvector store
              │            · grounded answering · citation validation · curated demo fallback
              │ content/   outreach generator (LLM | template) · heuristic evidence check
              │ ingestion/ validate → extract (PyMuPDF) → metadata → chunk → embed → index
              │ api/       REST routers · audit log · analytics · notifications
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
| **Platform** | RBAC on every endpoint; audit logging; notifications; saved items and search history ("My Knowledge"); loading, empty and error states everywhere; error boundaries; 404 page; responsive layout with mobile bottom nav |

---

## Local setup

**Requirements:** Node.js ≥ 20, Python 3.11+, PostgreSQL 16 with `pgvector` (recommended) — or nothing extra, using SQLite.

### 1. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
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
| `STORAGE_URL` / `STORAGE_KEY` / `STORAGE_SECRET` | backend | Reserved for S3/Supabase storage (see limitations) |
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
Seed contents: 32 documents (one fully connected flagship: *Antarctic Sea Ice Variability Study*), 16 datasets / 2,514 synthetic records, 43 media, 16 expeditions, 9 stations/locations, 16 researchers, 24 topics, 307 typed relationships, 9 outreach items across all workflow states (generated by the real generator), 90 days of demo analytics, audit history, notifications and saved items. Admins can also reset from **System Health → Reset & reseed**.

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
7. Sign in as **Researcher**, then click **Generate Outreach Content**.
8. Choose **Student**, then **Generate draft**.
9. Show the draft, the **Sources** panel and the **Evidence check**.
10. **Submit for review**.
11. Click **Switch to Editor (demo) & review** to open the **Review Center**.
12. **Approve**, then **Publish / Disseminate** (website + LinkedIn — social is simulated).
13. Open the **Outreach Feed** to show the published item with its sources, then sign in as **Admin** and show **Dashboard / Analytics / Audit Logs**.

---

## Testing

```bash
cd backend && pip install -r requirements-dev.txt && pytest -q          # 13 API tests
cd frontend && npm run typecheck && npm run lint && npm run build
cd frontend && npx playwright install chromium && BASE_URL=http://localhost:3000 npm run e2e
```
The backend tests cover search and filters, internal-document visibility, RAG citations, insufficient evidence, document-scoped questions, RBAC, the full draft → review → publish workflow, request-changes validation, evidence-check flags, and real PDF ingestion with upload rejections. The e2e script walks the whole demo flow, smoke-tests 25 routes, and checks 10 pages for horizontal overflow at 390 px.

Verified during development: tests pass on PostgreSQL 16 + pgvector **and** on SQLite (no pgvector); the LLM path was tested against a mock OpenAI-compatible server (a fabricated `[9]` citation was stripped); an unreachable LLM falls back to extractive answers and keyword search with visible notices; the e2e suite passes against the production build (`next start`) with 0 console errors.

---

## Implemented vs demonstration functionality

| Real, working | Demonstration / simulated (labelled in the UI) |
|---|---|
| Hybrid search (Postgres FTS / BM25 + pgvector / numpy, RRF), filters, facets | Corpus content: documents, researchers and most expedition details are illustrative |
| RAG with retrieval, evidence assessment, **citation validation**, insufficient-evidence handling | Without an LLM key: answers are **extractive** (quoted sentences), plus 2 **curated demo responses** for the flagship flow, labelled "Demo response" |
| Offline semantic embeddings (TF-IDF + LSA) — real vectors stored in pgvector | Dataset values are **synthetic** (seasonal cycles + noise) |
| Outreach generation (LLM, or template assembly from source sentences) | Media images are **original generated SVG artwork**; video "playback" is a preview |
| Evidence check (lexical support, numbers, citation integrity, overclaiming, region scope) | The evidence check is a **heuristic**, not scientific verification (stated in the UI) |
| Review workflow, RBAC, audit log, notifications, ingestion of PDF/TXT/MD | Publishing to LinkedIn/Instagram/newsletter is **simulated**; website publishing (Outreach Feed) is real |
| Analytics computed from DB events | Historical analytics are seeded demo activity (labelled "Prototype Demonstration Analytics") |

---

## Known limitations

- **No live deployment from this build environment**: deployment configs are included and the production build was tested locally, but the Vercel/Render URLs must be created from your accounts.
- OCR for scanned PDFs is not enabled (such uploads fail with a clear message). Upload of datasets (CSV/JSON) and media files through the UI is not wired; datasets and media are managed as metadata records.
- Uploaded files are stored on local disk; on free hosting tiers they are lost on restart (extracted text and index remain in the database). S3/Supabase storage is configured in env but not implemented.
- Institutional SSO is not implemented (JWT accounts only). The JWT is stored in `localStorage`; production should use httpOnly cookies.
- Offline LSA embeddings capture co-occurrence, not deep meaning. Configure an embedding API for production-quality semantic search, then **Admin → Repository → Rebuild index**.
- Multilingual explanations are not implemented (the language filter exists; the corpus is English).

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
| CORS errors (only with `NEXT_PUBLIC_API_URL`) | Add the frontend origin to `CORS_ORIGINS`, or leave `NEXT_PUBLIC_API_URL` empty to use the proxy |
