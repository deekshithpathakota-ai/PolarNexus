# PolarNexus SIH26063 — v2 Technical Completion Report

Baseline checkpoint: git commit `f76235f` ("Baseline before PolarNexus enhancement"). All v2 work sits on top of it as additive commits.

## Baseline (recorded before any change)
- 26 frontend routes, 70 API endpoints, 25 tables (`create_all`, no migration tool), 13 backend tests.
- Baseline status: backend tests 13/13 PASS · typecheck PASS · lint PASS · build PASS · E2E 50/50 PASS, 0 console errors.

## 1. Features added
1. **Institutional Activities**: model, 13 activity types, 14 linked demo records, list (search, filters, sort), detail pages, admin create/edit/feature/archive/restore/delete, all audit-logged.
2. **Media ingestion**: images (JPG/PNG/WEBP/TIFF) and videos (MP4/MOV/WEBM). Uploads are streamed with size limits and validated by magic bytes, MIME type and decoding. The pipeline extracts EXIF/GPS, makes thumbnails, reads ffprobe metadata, extracts audio and builds a transcript (from an uploaded transcript file, or speech-to-text when an API key is set). It then indexes the media, runs in the background with live status, and supports retry.
3. **Data Provenance & Verification**: a provenance record for every resource, 7 verification states, a provenance panel on every detail page, verification filters, an admin Provenance Centre, and a server-side guard so demo or synthetic records can never be marked Verified or Partner.
4. **Unified multimodal search** across 10 resource types (adds activities, topics, published outreach, uploaded media and transcripts), with per-type counts and verification/organisation/researcher/activity-type filters.
5. **Cross-modal AI synthesis**: related knowledge grouped by type, and compound questions ("…and which expeditions studied it?") with every added entity cited.
6. **Research → Outreach**: a "Turn Research Into Outreach" action on 7 page types and on AI answers; 10 content types and 6 audiences; a workflow stepper; an `evidence_checked` state; per-claim evidence with remove-claim; honest channel status; a public detail page per published item; Hindi/Telugu translation drafts that always need review.
7. **Knowledge Timeline**: a component on topic, expedition, station and researcher pages, plus `/timeline`.
8. **Impact & KPI dashboard** (`/impact`): labelled demonstration metrics, latency measured on live requests only, and a qualitative before/after table.
9. **Knowledge graph and map**: the graph now includes activities, topics and outreach; the map gains media and activity layers with verification status.
10. **Topic pages** (`/topics/[slug]`).
11. **Multilingual foundation**: English, Hindi and Telugu for the navigation shell; English is the default.
12. **Hardening**: production refuses to start with the default JWT secret, sign-in is throttled, the CORS preview regex is tightened and configurable, file serving is protected against path traversal, media files get CSP/nosniff headers, and audit coverage is extended.

## 2. Existing features preserved
Hybrid search (keyword + semantic + RRF), RAG with citation validation and insufficient-evidence handling, document-scoped questions, curated/extractive fallbacks, summaries, dataset explorer, polar map (Antarctic/Arctic/world), expeditions, stations, Learn, Content Studio, Review Center, outreach feed, PDF/TXT/MD ingestion, RBAC, audit log, notifications, saved items, admin dashboard/repository/users/analytics/health, demo login and role switching, and demo reset. All 70 baseline endpoints and all 26 routes still exist, and the original E2E passes unchanged.

## 3. Files changed (important)
- Backend, new: `app/core/migrations.py`, `app/services/provenance.py`, `app/ingestion/media.py`, `app/api/activities.py`, `app/api/media_ingest.py`, `app/api/discovery.py`, `app/seed/activities.py`, `app/seed/extensions.py`, `tests/test_v2.py`, `pytest.ini`.
- Backend, extended: models (`knowledge`, `workflow`, `telemetry`), `services/catalog.py`, `services/serializers.py`, `search/service.py`, `rag/indexer.py`, `rag/answer.py`, `content/generator.py`, `api/workflow.py`, `api/knowledge.py`, `api/admin.py`, `api/auth.py`, `api/misc.py`, `main.py`, `core/config.py`, `seed/seed_demo_data.py`, `Dockerfile`, `.env.example`, `requirements.txt` (Pillow).
- Frontend, new pages: `/activities`, `/activities/[slug]`, `/topics/[slug]`, `/timeline`, `/impact`, `/outreach/[id]`, `/admin/provenance`, `/admin/activities`.
- Frontend, new components: `provenance/Provenance`, `media/MediaUploader`, `media/ProcessingSteps`, `timeline/KnowledgeTimeline`, `outreach/OutreachButton`, `cards/ActivityCard`, `lib/i18n`.
- Frontend, extended: every detail page, ExploreView, AnswerCard, EvidencePanel, Studio, Review, Workspace, Map, PolarMap, KnowledgeGraph, ResourceCard, AppShell, nav, types, format, home.
- New E2E: `frontend/e2e/sih-journey.mjs`.

## 4. Database changes (additive only)
- New tables: `institutional_activities`, `provenance`, `schema_migrations`.
- New columns: on `media`, 19 ingestion fields (status, filename, mime_type, size_bytes, duration_seconds, width, height, thumbnail_path, captured_at, location, latitude, longitude, exif, transcript, transcript_source, processing_status/steps/error, uploaded_by); on `generated_content`, audience, language, translated_from; on `citations`, page; on `searches` and `ai_queries`, duration_ms.
- Existing databases are upgraded on start-up. Tested by seeding with the baseline code on SQLite **and** PostgreSQL 16, then starting v2: 25 columns were added, every existing row was preserved, and activities and provenance were added.

## 5. API changes
New endpoints: `/api/activities` (GET, POST), `/api/activities/types`, `/api/activities/{slug}` (GET, PUT, PATCH, DELETE), `/api/media/upload`, `/api/media/{slug}/file|thumbnail|processing|reprocess`, `/api/my/media-uploads`, `/api/media-options`, `/api/provenance/statuses`, `/api/provenance/{type}/{key}`, `/api/admin/provenance` (GET), `/api/admin/provenance/{type}/{key}` (PATCH), `/api/topics/{slug}`, `/api/timeline`, `/api/impact`, `/api/filters/options`, `/api/outreach/channels`, `/api/outreach/{id}`, `/api/content/{id}/translate`.

Extended (backward compatible): search/list endpoints accept `verification`, `organisation`, `activity_type` and return `facets.resource_groups/verification/organisations`; detail endpoints return `provenance` (datasets also return `quality`); `/api/ai/ask` returns `related_groups` and `synthesis`; `/api/content/generate` accepts `audience` and 4 new formats plus 4 new source types; `/api/content/{id}/check` advances a draft to `evidence_checked`; `/api/map` adds `media` and `activities`; `/api/admin/repository` accepts `kind=activity`.

## 6. AI changes
- **Retrieval**: unchanged hybrid pipeline. New passage types (activities, topics, published outreach, media transcripts) are indexed for discovery but excluded from answer evidence.
- **Multimodal search**: image and video descriptions, tags, EXIF facts and transcripts share the same chunk index.
- **Grounding**: compound questions answer only the explanatory part from passages; listed entities each cite their own record; all markers pass the existing citation validator.
- **Content generation**: audience changes wording and adds only questions (for teachers) or cited source sentences (for policy readers). No new facts are added.

## 7. Security changes
Production refuses to start with the default `JWT_SECRET`. Sign-in is throttled per IP and email (429). The CORS preview regex is restricted to `https://<name>.vercel.app` and can be switched off. Uploads are streamed with size caps; type is validated by extension, magic bytes, MIME type and decoding (with a decompression-bomb guard); filenames are sanitised; and files are served only from inside `STORAGE_DIR` with `nosniff` and a sandbox CSP. New admin APIs require `manage_repository`. Audit events were added for create, update, archive, restore, feature, visibility change, delete, verify, reject, verification change, upload, reprocess, evidence check and translate. RBAC is unchanged. Tokens stay in `localStorage` for demo stability (the README documents moving to httpOnly cookies).

## 8. Testing (all actually executed)
```
Backend tests:  PASS — 34/34 on SQLite, 34/34 on PostgreSQL 16 (no pgvector extension available → in-process vector fallback)
Frontend tests: none exist in the project (no unit-test runner configured)
Type checking:  PASS (tsc --noEmit)
Lint:           PASS (no warnings or errors)
Build:          PASS (next build)
E2E:            PASS — original demo-flow 50/50, new sih-journey 37/37, 0 console/page errors (Chromium, production build)
```

## 9. Known limitations / simulated
- LinkedIn, Instagram and Newsletter publishing is a labelled **prototype simulation**; only the website feed is live.
- Speech-to-text needs `OPENAI_API_KEY`. Without it, speech is searchable only from an attached transcript.
- Video steps need ffmpeg on the host (the Dockerfile installs it; Render's native runtime may not have it, in which case those steps are shown as skipped).
- Activities, documents, researchers and most expeditions are demonstration data; datasets are synthetic. Only high-level station and expedition facts are marked Verified.
- Hindi and Telugu cover the navigation only and are pending native-speaker review.
- pgvector was not available in this test environment; the pgvector code path is unchanged from the baseline.
- Uploaded files use local disk storage; there is no Alembic migration history and no SSO.

## 10. Run instructions
```bash
# Database (optional — SQLite is used when DATABASE_URL is unset)
docker run -d -p 5432:5432 -e POSTGRES_USER=polar -e POSTGRES_PASSWORD=polar -e POSTGRES_DB=polarnexus pgvector/pgvector:pg16

# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && cp .env.example .env     # set DATABASE_URL / JWT_SECRET
uvicorn app.main:app --reload --port 8000                        # auto-seeds or upgrades the DB

# Frontend
cd frontend && npm install && cp .env.example .env.local && npm run dev   # http://localhost:3000

# Tests
cd backend && pytest -q
cd frontend && npm run typecheck && npm run lint && npm run build && npm start &
BASE_URL=http://localhost:3000 npm run e2e && BASE_URL=http://localhost:3000 npm run e2e:journey
```
