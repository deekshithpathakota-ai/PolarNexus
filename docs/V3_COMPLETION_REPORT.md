# PolarNexus SIH26063 — v3 Technical Completion Report

Baseline: git tag `v2-baseline-before-v3` (commit `0f824cc`). All v3 work is additive commits on top of it.
Baseline status before any change: backend tests 34/34 PASS · typecheck PASS · lint PASS.

---

## A. Features added

1. **Real public-source data** (verification status *Public source*):
   - NSIDC Sea Ice Index v4 monthly extent and area: Antarctic February, Antarctic September and Arctic September, 1979–2026. The CSVs are bundled unmodified and registered through the new dataset pipeline.
   - 11 openly licensed Wikimedia Commons photographs (CC BY / CC BY-SA / public domain / GODL-India). Each has its licence, author, capture date and source page as recorded on Commons, plus written alt text.
   - 6 metadata-only records for official resources:
     - Indian Antarctic Act 2022
     - India's Arctic Policy (2022)
     - the NCPOR website
     - NCPOR's Himadri station page
     - the Antarctic Treaty Secretariat website
     - the NSIDC G02135 landing page
   - One Bharati photo was **excluded** because its capture date is unreliable at the source.
2. **Visual semantic search.**
   - Uses CLIP ViT-B/32 via `fastembed` (ONNX Runtime, CPU, no PyTorch).
   - Photos are embedded on ingestion. Videos are indexed by representative key frames (scene changes plus even sampling, capped at `VIDEO_MAX_KEYFRAMES`), with timestamps.
   - Available as `/api/visual/search`, the `/visual-search` page and a panel on the Media page. Visual rank is also fused into hybrid search.
   - Video results show "Relevant frame — mm:ss" with the frame image.
3. **Research Story Builder.**
   - Pages: `/stories`, `/stories/new`, `/stories/[slug]`.
   - "Build Research Story" buttons on document, dataset and media pages.
   - Graph-derived story chain; scientific, public and student explanations; timeline; map; evidence basis.
   - Workflow: draft → editor publishes → archive (never deleted).
4. **Campaign Planner.**
   - Pages: `/campaigns` and `/campaigns/[slug]`.
   - Campaigns have dates, audiences, topics, channels and a status (draft, scheduled, published or archived).
   - Calendar items are linked to outreach content.
   - Publishing goes through the Review Center's publish transition.
5. **Content Calendar** (`/calendar`): month grid on desktop, agenda list on mobile; plan, edit, schedule, publish and cancel items.
6. **Outreach Impact Analytics** (`/outreach-analytics`).
   - Live tracking of view, click, share and complete events on public outreach pages.
   - Breakdowns by campaign, content, audience, channel, format and week; popular topics; research-to-content conversion.
   - Seeded engagement is flagged `is_demo` and shown as **DEMO METRICS**, with a toggle for live-only figures.
7. **CSV/JSON dataset ingestion.**
   - Supports CSV, TSV, JSON and GeoJSON.
   - Steps: analyse (format, schema, types, roles, preview, validation) → duplicate check → metadata with user-supplied units → confirm → background registration → indexing → explorer.
   - The parser registry is ready for NetCDF.
8. **OCR for scanned PDFs.** Pages with too little embedded text are rendered at 200 dpi and read with tesseract. Page markers are preserved and the OCR status is stored.
9. **FAIR metadata** (`/api/fair/...`). Dublin Core plus DataCite-style DOI and version fields, with a completeness score. Missing fields are shown as missing, and ORCID iDs are shown only if one has been stored.
10. **Duplicate detection.**
    - Signals: content hash, DOI, title and file-name similarity, text overlap.
    - Covers documents (pre-upload check), datasets (at analysis) and media.
    - Options: Keep both, Update existing (adds a new version), Review, Cancel.
11. **Resource versioning.**
    - Append-only `resource_versions` table, with a baseline v1 row for every existing record.
    - New versions are recorded on metadata edits, verification changes, new files and imports.
    - Snapshots are never overwritten. "Update existing" archives the previous file path and text.
12. **Provenance pipeline (lineage).** Source → Ingestion → Processing → Transformation → AI Generation → Human Review → Publication, with "Generated from" sources for outreach content.
13. **Admin platform health.** Repository health, AI health, content states and data quality, plus a "Rebuild visual index" button.
14. **Premium sign-in page** (see L).
15. **Storage abstraction.** `LocalStorage`, and `S3Storage` for any S3-compatible service, with path-safe keys.
16. **Security.**
    - HttpOnly, SameSite=Lax session cookie (Secure in production) with a CSRF header guard.
    - Per-IP rate limits on AI and upload endpoints.
    - Audit field truncation (fixes a PostgreSQL-only crash).
17. **Visible AI pipeline trace, evidence basis and audience modes** (see F).

## B. Features modified (all backward compatible)

- **Hybrid search:**
  - Adds the visual rank list.
  - Applies an authority multiplier of 1.12 to verified, partner and public-source records; demo records never get it.
  - Adds `match_reasons`, `score_breakdown` and `visual_match`.
  - Existing fields are unchanged, and the flagship document still ranks first for "Antarctic sea ice".
- **RAG `/api/ai/ask`:** new optional `audience`. New response fields `evidence_strength`, `evidence_strength_label`, `evidence_basis`, `pipeline` and per-source `verification`. `evidence_status` is unchanged (still 3 values).
- **Simplifier:** no longer rewrites words inside proper names (it previously changed "Sea Ice Variability Study" to "Sea Ice variation Study").
- **Document ingestion:** new `ocr` step, content hash, DOI detection, `update_existing`, version recording and object-storage mirroring.
- **Media ingestion:**
  - New `visual` step, content hash, alt text and caption fields.
  - An uploaded WebVTT file is used as the caption `<track>`.
  - New `/frames/{i}` and `/captions` endpoints.
- **Dataset download:** the "SYNTHETIC" header is now written only for synthetic datasets (it was previously on every download).
- **Dataset page:**
  - Shows the real verification badge (it previously always said "Synthetic").
  - Adds a schema and validation report.
  - Hides the Geographic chart when there are no coordinates.
  - Year and month columns are no longer offered as plot variables.
- **Translation drafts:** a machine translation is kept only if citation markers, numbers **and units** all survive.
- **Pages updated:**
  - Detail pages: new Scientific Trust panel (pipeline, versions, metadata).
  - Media page: Accessibility panel.
  - Resource page: metadata-only and OCR notices.
  - Outreach page: share link and Provenance pipeline panel.
  - Assistant: updated pipeline explainer and visual search/OCR status.
- **Navigation and i18n:** 5 new entries, translated into Hindi and Telugu (prototype translations).

## C. Files changed (important)

- **Backend, new:**
  - Models and APIs: `models/v3.py`, `api/{stories,campaigns,datasets_ingest,scientific}.py`, `core/ratelimit.py`.
  - Ingestion: `ingestion/{datasets,ocr}.py`.
  - Services: `services/{visual,stories,versions,fair,lineage,duplicates,storage}.py`.
  - Seed data: `seed/v3.py`, `seed/assets/public/*` (3 CSVs, 11 JPEGs, `commons_manifest.json`).
  - Tests: `tests/test_v3.py`, `tests/conftest.py`.
  - Requirements: `requirements-visual.txt`, `requirements-s3.txt`.
- **Backend, extended:**
  - Core: `core/config.py`, `core/migrations.py`, `main.py`.
  - Models: `models/{knowledge,telemetry,workflow,__init__}.py`.
  - RAG and search: `rag/{answer,llm,embeddings,indexer,simplify}.py`, `search/service.py`.
  - Ingestion: `ingestion/{pipeline,media}.py`.
  - APIs: `api/{ai,auth,admin,discovery,ingestion,media_ingest,knowledge,workflow}.py`.
  - Auth: `auth/security.py`.
  - Services: `services/{provenance,catalog,serializers,audit}.py`.
  - Seed: `seed/seed_demo_data.py`.
  - Config and deployment: `.env.example`, `Dockerfile`.
- **Frontend, new pages:** `/stories`, `/stories/new`, `/stories/[slug]`, `/campaigns`, `/campaigns/[slug]`, `/calendar`, `/outreach-analytics`, `/visual-search`.
- **Frontend, new components:**
  - Sign-in: `auth/PolarBackdrop`, `common/PolarLoader`.
  - Trust panels: `provenance/Trust` (ScientificTrust, LineageView, VersionHistory, FairPanel).
  - Datasets: `datasets/{DatasetUploader,DatasetQuality,DuplicateNotice}`.
  - Campaigns: `campaigns/{ContentCalendar,shared}`.
  - Other: `search/VisualSearch`, `stories/StoryButton`, `admin/PlatformHealth`.
- **Frontend, extended:**
  - Pages: login (rewritten visually; auth calls unchanged), resource, dataset, media, outreach item, workspace, assistant, admin, media list.
  - Components: AnswerCard, AskPanel, ResourceCard, DatasetExplorer, Provenance.
  - Libraries and layout: `lib/{api,types,i18n}`, `nav.ts`, `globals.css`.
  - New E2E script: `e2e/v3-journey.mjs` (`npm run e2e:v3`).
- **Deployment:** `docker-compose.yml` (new env vars, storage and model volumes), `render.yaml` (`VISUAL_SEARCH_PROVIDER=none` on the free native runtime).

## D. Database changes (additive only — `SCHEMA_VERSION 2026.10-v3`)

- **New tables:** `research_stories`, `campaigns`, `campaign_items`, `resource_versions`, `visual_embeddings`, `dataset_uploads`, `outreach_events`.
- **New columns:**
  - `documents`: doi, license, publisher, source_url, content_hash, ocr_status, ocr_pages, metadata_only
  - `datasets`: doi, creator, source_url, content_hash, file_path, columns_schema, quality_report, uploaded_by
  - `media`: alt_text, caption, captions_path, content_hash, source_url, visual_status
  - `researchers`: orcid
  - `ai_queries`: evidence_strength, audience, citations_removed
  - `ingestion_jobs`: ocr_status
- The migrator now quotes boolean defaults, because PostgreSQL rejects an integer default on a boolean column.
- `upgrade_v3()` runs at start-up and only adds things: public-source records, version baselines, the demo story, the demo campaign and demo metrics.
- **Verified in-place upgrade on PostgreSQL 16:**
  - A database seeded with the v2 tag was started with v3.
  - Documents went from 32 to 38. All 90 audit log rows were kept.
  - `schema_migrations` now has `2026.10-v3`, 166 version rows were added, and 20 public-source records were added.

## E. Environment variables (new)

| Group | Variables |
|---|---|
| LLM provider | `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL` |
| Embeddings | `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL` |
| Visual search | `VISUAL_SEARCH_PROVIDER`, `VISUAL_IMAGE_MODEL`, `VISUAL_TEXT_MODEL`, `VISUAL_MODEL_CACHE`, `VISUAL_MIN_SIMILARITY`, `VIDEO_MAX_KEYFRAMES` |
| OCR | `OCR_ENABLED`, `OCR_LANGUAGES`, `OCR_MIN_CHARS_PER_PAGE`, `OCR_MAX_PAGES` |
| Dataset limits | `MAX_DATASET_MB`, `MAX_DATASET_ROWS` |
| Storage | `STORAGE_BACKEND`, `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_PREFIX` |
| Rate limits | `RATE_LIMIT_AI_PER_MINUTE`, `RATE_LIMIT_UPLOADS_PER_MINUTE` |
| Session cookie | `AUTH_COOKIE_ENABLED`, `AUTH_COOKIE_NAME` |

All are documented in `backend/.env.example`. The original `OPENAI_*` names still work. No secrets are committed.

## F. AI architecture

```
Question → Intent detection → Query processing → Hybrid retrieval (keyword + vector, RRF)
→ Evidence ranking → Evidence sufficiency check (term coverage, out-of-domain ratio)
→ Generation (LLM with audience instruction | curated demo | extractive with audience style)
→ Citation validation (invalid [n] removed and counted) → Evidence status (3-level, unchanged)
→ Evidence strength (strong · moderate · limited · insufficient — rules, not probabilities)
→ Evidence basis (public/verified vs demo records) → Answer + sources + pipeline trace
```

- Activities, topics, media and AI-generated outreach are still never used as evidence.
- Teacher mode without an LLM adds teaching points that quote cited sentences, and discussion questions that only refer back to the sources. No new facts are introduced.

## G. Visual search

- **Images:** validate → metadata → thumbnail → CLIP image embedding → `visual_embeddings`.
- **Videos:** key frames from ffmpeg's scene score plus even sampling, at least 1.5 s apart and capped. Each frame is embedded and stored with its timestamp and frame JPEG.
- **Queries:** the query goes through the CLIP text encoder, then cosine similarity is computed. Each media item is represented by its best frame. A calibrated floor (0.265; unrelated queries score about 0.20–0.26 on the bundled photos) and a window of 0.04 below the top score filter the results.
- **Measured example:** "iceberg near a research vessel" puts *Iceberg seen from the bow of the RRS Ernest Shackleton* first (similarity 0.33).
- **Fallback:** without `fastembed` the API says visual search is unavailable, and search falls back to metadata, captions and transcripts.

## H. Dataset pipeline

```
Upload → Validate (size, binary sniff, extension vs content) → Detect format → Parse
→ Schema → Column type inference (integer/number/date/datetime/boolean/category/text) + roles
  (latitude/longitude/time/year/month/day) → Preview (20 rows)
→ Validation (missing, duplicate rows, invalid numbers/dates/coordinates, mixed types, fill values, ragged rows)
→ Duplicate candidates → Metadata (title, description, region, creator, licence, source, URL, DOI, keywords, topics, units)
→ User confirmation (errors must be acknowledged) → Background registration (records, time axis, coordinates)
→ Index → Provenance (user_uploaded) + version 1 → Dataset explorer (charts only where meaningful)
```

## I. OCR

- PyMuPDF extracts text from each page first. Pages with fewer than `OCR_MIN_CHARS_PER_PAGE` characters are rendered at 200 dpi and read by tesseract (called with an argument list, never a shell). At most `OCR_MAX_PAGES` pages are processed.
- The job step and the document record list which pages were OCR'd. The status is one of: applied, partial, failed, unavailable or not_needed.
- `[[page N]]` markers are kept, so citations still point at the right page.

## J. Research Story

1. Choose a starting record.
2. The system walks the knowledge graph up to two hops and groups items by role: topic, paper, dataset, expedition, station, photograph, video, researcher, activities. At equal distance, public or verified records come first.
3. Edit the items: remove some, or search and add others.
4. Create. Explanations come from the primary paper's own sections via the existing grounded summariser. Without a paper, the records' descriptions are quoted with citations.
5. An editor publishes the story.

The story page shows the chain, the three explanations with clickable citations, a timeline, a map, the evidence basis and related topics.

## K. Outreach

```
Research → Content (Studio, cited) → Evidence check → Editorial review → Campaign item (schedulable only when
approved) → Publish (Review Center transition; website live, other channels simulated) → Analytics (live events;
seeded engagement labelled DEMO METRICS)
```

## L. Sign-in upgrade

- **Visual design:**
  - Dark polar sky gradient with an ice-shelf and mountain silhouette.
  - Brand statement: "AI-powered polar science knowledge and outreach".
  - Journey chips, from DISCOVER to MEASURE.
  - Real station coordinates as a quiet detail.
  - White card with the existing tokens (Source Serif / IBM Plex, polar palette), so moving into the app feels like the same product.
- **Aurora:** three blurred gradient bands drifting over 26–40 s cycles, screen-blended, no flashing.
- **Particles:**
  - One canvas drawing snow, plus green "observation" points with faint links between nearby ones.
  - Count scales with screen area: at most 28 snow and 10 data points on phones, 70 and 26 on desktop.
  - About 30 fps, paused when the tab is hidden.
- **Scientific visualisation:** an azimuthal graticule (circles of latitude and meridians), rotating once every 260 s.
- **Micro-interactions:**
  - Logo fades and scales in; the copy rises in stages.
  - The card fades, rises and goes from blurred to clear in 0.55 s, so it does not delay input.
  - Inputs get a focus glow and border transition; the Sign in button has a polar-light sheen.
  - A PolarNexus orbit loader appears while signing in and is shown as "Initializing PolarNexus".
- **Responsive:** single column on mobile, smaller heading, no horizontal overflow (checked at 390 px).
- **Accessibility:**
  - Real `<label>`s and keyboard focus states.
  - The backdrop is `aria-hidden`.
  - `prefers-reduced-motion` shows a static frame: aurora, grid, loader orbit and sheen are switched off, and the canvas draws once. This is verified in E2E.
- **Auth:** the login, demo-login, redirect and error handling calls are unchanged.

## M. Testing (all actually executed in this environment)

```
Backend tests  SQLite                            61/61 PASS  (13 original + 21 v2 + 27 v3)
Backend tests  PostgreSQL 16 (no pgvector ext.)  61/61 PASS
Backend tests  visual search + OCR disabled      61/61 PASS  (honest "unavailable/skipped" paths)
In-place upgrade v2 → v3 on PostgreSQL 16        PASS (rows preserved, v3 data added)
Python 3.11 byte-compile of all backend code     PASS
Frontend typecheck (tsc --noEmit)                PASS
Frontend lint (next lint)                        PASS (0 warnings)
Frontend production build (next build)           PASS
E2E original demo-flow (production build)        50/50 PASS, 0 console/page errors
E2E v2 sih-journey                               37/37 PASS, 0 console/page errors
E2E v3 journey                                   25/25 PASS, 0 console/page errors (incl. 12 mobile-overflow checks)
```

v3 backend tests cover:
- Public-source labelling and values.
- The demo-cannot-be-verified guard.
- Version history after a verification change.
- Search reasons and authority weighting.
- Evidence strength and basis, all 4 audience modes, the `audience` validation error, and AI status.
- LLM setting aliases.
- Visual search (real CLIP) and video key frames with frame serving.
- CSV analysis with every issue type, plus confirm, registration and units.
- JSON and GeoJSON input, and rejections (NetCDF, binary, bad JSON, unauthenticated, public role).
- OCR of a generated scanned PDF, with page citation.
- Pre-upload duplicate detection and update-existing with history.
- The refusal to replace demo documents.
- FAIR metadata (no invented DOI or ORCID) and content and resource lineage.
- The research story flow (draft privacy, editor-only publish, archive).
- Campaign scheduling blocked until approval, editor-only publish, simulated channels.
- Calendar and analytics demo/live labelling, plus tracking.
- Admin health.
- Storage-key traversal.
- Cookie session with the CSRF guard.
- Rate limiting.
- v2-shaped schema migration.
- The translation guard.

**Not tested:**
- Live LLM provider: no API key in this environment. The provider wiring is unchanged from v2, which was tested against a mock server; the new `LLM_*` aliases are unit-tested.
- Speech-to-text: no key.
- S3 object storage against a real bucket.
- pgvector: the extension is not installed here; the code path is unchanged from v2.
- Docker image builds: no Docker daemon available.
- Real-device mobile browsers: only headless Chromium at 390 px.

## N. Remaining limitations

- **Content and data:**
  - The demo corpus is still mostly illustrative and labelled as such.
  - Public-source documents are metadata-only, by design (no copyrighted full text).
  - The NSIDC DOI is not recorded, because it could not be verified from here; the metadata panel shows it as missing.
- **Visual search:** CLIP ViT-B/32 is general-purpose, so similarity is relevance, not certainty. The model download is about 350 MB. Illustrated demo media is not visually indexed.
- **Datasets and OCR:** NetCDF is not implemented yet. OCR quality depends on the scan, and only English is configured by default.
- **Outreach:** social, newsletter and educational-portal publishing are simulated. Seeded engagement is demonstration data.
- **Translations:** Hindi and Telugu translations are prototype strings pending native-speaker review.
- **Graph, map and timeline:** no new layout features. New records flow through automatically; campaign items are not on the knowledge timeline.
- **Security:**
  - Rate limiting is in-memory, per instance.
  - The SPA still stores the bearer token in `localStorage` alongside the new HttpOnly cookie, for backward compatibility.
  - SSO is not implemented.
- **Database:** no Alembic; the additive start-up migrator is used.
