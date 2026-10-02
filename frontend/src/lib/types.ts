export type ResourceType = "document" | "dataset" | "media" | "expedition" | "station" | "researcher" | "topic" | "activity" | "content";

export type VerificationStatus =
  | "verified" | "public_source" | "partner_source" | "user_uploaded" | "pending_review" | "demo_data" | "synthetic_demo" | "unverified";

export interface Provenance {
  source_organisation: string;
  source_type: string;
  source_url: string;
  original_identifier: string;
  license: string;
  publication_date: string | null;
  collection_date: string | null;
  imported_at: string | null;
  last_verified_at: string | null;
  verification_status: VerificationStatus;
  verification_label: string;
  verification_description: string;
  verified_by: string;
  data_quality: string;
  provenance_notes: string;
  is_demo: boolean;
  official: boolean;
  notice: string;
}
export type Role = "public" | "researcher" | "editor" | "admin";

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  role_label: string;
  institution: string;
  permissions: string[];
  is_demo: boolean;
}

export interface Card {
  type: ResourceType;
  id: number;
  slug: string;
  title: string;
  kind: string;
  summary: string;
  region: string;
  year: number | null;
  source: string;
  topics: string[];
  topic_slugs: string[];
  views: number;
  is_demo: boolean;
  url: string;
  language?: string;
  visibility?: string;
  status?: string;
  extra: Record<string, unknown>;
  relation?: string;
  organisation?: string;
  verification?: VerificationStatus;
  verification_label?: string;
  official?: boolean;
}

export interface SearchResult extends Card {
  score: number;
  relevance: number | null;
  matched_terms: string[];
  matching_concepts: string[];
  match_type: string;
  highlight: string;
  matched_section: string;
  match_reasons?: string[];
  score_breakdown?: { text: number; title: number; authority_multiplier: number };
  visual_match?: { similarity: number; timestamp: string | null; frame_seconds: number | null; frame_url: string | null };
}

export interface Facets {
  regions: Record<string, number>;
  types: Record<string, number>;
  topics: Record<string, number>;
  year_min: number | null;
  year_max: number | null;
  resource_groups?: Record<string, number>;
  verification?: Record<string, number>;
  organisations?: Record<string, number>;
}

export interface SearchResponse {
  query: string;
  mode: string;
  mode_used: string;
  notice: string;
  sort: string;
  total: number;
  page: number;
  page_size: number;
  pages: number;
  results: SearchResult[];
  facets: Facets;
  took_ms: number;
}

export interface Related {
  groups: Record<string, Card[]>;
  similar: Card[];
}

export interface TopicRef {
  slug: string;
  name: string;
  category: string;
}

export interface DocumentDetail {
  type: "document";
  id: number;
  slug: string;
  title: string;
  doc_type: string;
  abstract: string;
  authors: string[];
  institution: string;
  region: string;
  year: number;
  language: string;
  keywords: string[];
  source: string;
  file_name: string;
  page_count: number;
  status: string;
  visibility: string;
  is_demo: boolean;
  views: number;
  created_at: string;
  updated_at: string;
  sections: { chunk_id: number; section: string; page: number; text: string }[];
  topics: TopicRef[];
  related: Related;
  citation: string;
  provenance?: Provenance;
  doi?: string;
  license?: string;
  publisher?: string;
  source_url?: string;
  ocr_status?: string;
  ocr_pages?: number[];
  metadata_only?: boolean;
}

export interface Variable {
  name: string;
  unit: string;
  description: string;
}

export interface DatasetDetail {
  type: "dataset";
  id: number;
  slug: string;
  title: string;
  description: string;
  region: string;
  data_type: string;
  temporal_start: string | null;
  temporal_end: string | null;
  spatial_coverage: string;
  variables: Variable[];
  source: string;
  format: string;
  license: string;
  size_label: string;
  record_count: number;
  year: number;
  keywords: string[];
  is_demo: boolean;
  views: number;
  updated_at: string;
  topics: TopicRef[];
  related: Related;
  provenance?: Provenance;
  quality?: { records: number; variables: { name: string; unit: string; completeness: number | null }[]; georeferenced: number | null; note: string };
  doi?: string;
  creator?: string;
  source_url?: string;
  has_coordinates?: boolean;
  columns_schema?: { name: string; type: string; role: string; missing: number; unique: number; stats?: Record<string, number | string> }[];
  quality_report?: { issues?: DatasetIssue[]; summary?: { errors: number; warnings: number; verdict: string }; duplicates_dropped?: number; rows_in_file?: number; time_derivation?: string | null };
}

export interface DatasetIssue {
  severity: "error" | "warning" | "info";
  code: string;
  message: string;
  column: string | null;
  count: number | null;
  examples: string[];
}

export interface ColumnInfo {
  name: string;
  type: "integer" | "number" | "date" | "datetime" | "boolean" | "category" | "text" | "empty";
  role: string;
  missing: number;
  missing_pct: number;
  unique: number;
  examples: string[];
  invalid?: number;
  stats?: Record<string, number | string>;
}

export interface DatasetAnalysis {
  filename: string;
  format: string;
  rows: number;
  columns: number;
  schema: ColumnInfo[];
  roles: Record<string, string>;
  preview: Record<string, string>[];
  issues: DatasetIssue[];
  duplicate_rows: number;
  duplicates: DuplicateCandidate[];
  summary: { errors: number; warnings: number; verdict: "pass" | "warn" | "fail" };
  temporal: { column: string | null; start: string | null; end: string | null };
  spatial: { bbox: { min_lat: number; max_lat: number; min_lon: number; max_lon: number } | null; suggested_region: string | null };
  numeric_variables: string[];
  suggested_charts: string[];
  suggested_title: string;
}

export interface DuplicateCandidate {
  type: string;
  id: number;
  slug: string;
  title: string;
  url: string;
  similarity: number;
  signals: string[];
  year?: number;
  status?: string;
}

export interface DatasetUploadState {
  token: string;
  filename: string;
  format: string;
  size_bytes: number;
  status: "analyzed" | "registering" | "registered" | "failed" | "cancelled";
  steps: ProcessingStep[];
  error: string;
  analysis?: DatasetAnalysis;
  dataset?: { slug: string; title: string; status: string; url: string } | null;
}

export interface VersionEntry {
  version: number;
  change: string;
  status: string;
  user: string;
  date: string | null;
  changed_fields: string[];
  snapshot: Record<string, unknown>;
}

export interface FairRecord {
  standard: string;
  fields: { key: string; label: string; term: string; value: unknown; required: boolean }[];
  missing: string[];
  completeness: number;
  verification: { status: VerificationStatus; label: string; is_demo: boolean };
  orcid_note: string;
}

export interface LineageStage {
  key: string;
  label: string;
  state: "done" | "pending" | "in_progress" | "missing" | "not_applicable" | "rejected" | "info" | "demo";
  detail: string;
  at: string | null;
  actor: string;
}

export interface Lineage {
  kind: string;
  id: number;
  title?: string;
  stages: LineageStage[];
  generated_from?: { type: string; id: number; slug: string; title: string; url: string; citations: number; sections: string[]; pages: number[]; verification_status?: VerificationStatus; verification_label?: string }[];
  versions?: number;
}

export interface SeriesResponse {
  x: string;
  y: string;
  unit: string;
  numeric_variables: string[];
  points: { x: string | number; y: number; group: string | null; lat: number | null; lon: number | null }[];
  stats: { count: number; min: number | null; max: number | null; mean: number | null };
}

export interface MediaItem {
  type: "media";
  id: number;
  slug: string;
  title: string;
  description: string;
  media_type: "image" | "video" | "infographic";
  category: string;
  region: string;
  year: number;
  credit: string;
  license: string;
  tags: string[];
  scene: string;
  duration: string;
  is_demo: boolean;
  views: number;
  topics?: TopicRef[];
  related?: Related;
  provenance?: Provenance;
  status?: string;
  filename?: string;
  mime_type?: string;
  size_bytes?: number;
  duration_seconds?: number | null;
  width?: number | null;
  height?: number | null;
  captured_at?: string | null;
  uploaded_at?: string | null;
  location?: string;
  latitude?: number | null;
  longitude?: number | null;
  exif?: Record<string, unknown>;
  has_file?: boolean;
  file_url?: string | null;
  thumbnail_url?: string | null;
  transcript?: string;
  transcript_source?: string;
  processing_status?: string;
  processing_steps?: ProcessingStep[];
  processing_error?: string;
  uploaded_by?: number | null;
  alt_text?: string;
  caption?: string;
  source_url?: string;
  captions_url?: string | null;
  visual_status?: string;
}

export interface ProcessingStep {
  key: string;
  label: string;
  status: "pending" | "running" | "done" | "skipped" | "failed";
  detail: string;
}

export interface Activity {
  type: "activity";
  id: number;
  slug: string;
  title: string;
  description: string;
  activity_type: string;
  activity_type_label: string;
  date: string | null;
  end_date: string | null;
  year: number | null;
  location: string;
  latitude: number | null;
  longitude: number | null;
  region: string;
  organisation: string;
  department: string;
  audience: string;
  outcomes: string[];
  status: string;
  visibility: string;
  featured: boolean;
  cover_scene: string;
  is_demo: boolean;
  views: number;
  url: string;
  topics?: TopicRef[] | string[];
  topic_slugs?: string[];
  related?: Related;
  related_count?: number;
  provenance?: Provenance;
  verification?: VerificationStatus;
  verification_label?: string;
}

export interface Expedition {
  type: "expedition";
  id: number;
  slug: string;
  name: string;
  number: number;
  program: string;
  region: string;
  season: string;
  year: number;
  objective: string;
  themes: string[];
  participants: number;
  leader: string;
  vessel: string;
  highlights: string[];
  latitude: number | null;
  longitude: number | null;
  verified_note: string;
  is_demo: boolean;
  views: number;
  topics?: TopicRef[];
  related?: Related;
  provenance?: Provenance;
}

export interface Station {
  type: "station";
  id: number;
  slug: string;
  name: string;
  kind: string;
  region: string;
  country: string;
  location_name: string;
  latitude: number;
  longitude: number;
  established: string;
  status: string;
  themes: string[];
  description: string;
  facts_source: string;
  verified: boolean;
  views: number;
  counts?: Record<string, number>;
  topics?: TopicRef[];
  related?: Related;
  provenance?: Provenance;
}

export interface Researcher {
  type: "researcher";
  id: number;
  slug: string;
  name: string;
  position: string;
  institution: string;
  expertise: string[];
  bio: string;
  is_demo: boolean;
  topics?: TopicRef[];
  related?: Related;
  provenance?: Provenance;
}

export interface Source {
  n: number;
  chunk_id: number;
  resource_type: ResourceType;
  resource_id: number;
  slug: string;
  title: string;
  url: string;
  section: string;
  page: number;
  snippet: string;
  score: number;
  kind: string;
  is_demo: boolean;
  verification?: VerificationStatus;
  verification_label?: string;
}

export type Audience = "researcher" | "teacher" | "student" | "public";
export type EvidenceStrength = "strong" | "moderate" | "limited" | "insufficient";

export interface AskResponse {
  question: string;
  document: { slug: string; title: string; url: string } | null;
  intent: string | null;
  answer: string;
  mode: "llm" | "extractive" | "curated_demo" | "metadata" | "insufficient";
  mode_label: string;
  evidence_status: "strong" | "limited" | "insufficient";
  evidence_label: string;
  sources: Source[];
  related: Pick<Card, "type" | "id" | "slug" | "title" | "kind" | "region" | "year" | "url" | "summary">[];
  notice: string;
  suggestions?: string[];
  retrieval: { mode: string; passages_considered: number; passages_used: number };
  query_id: number;
  related_groups?: Record<string, (Pick<Card, "type" | "id" | "slug" | "title" | "kind" | "region" | "year" | "url" | "summary" | "is_demo" | "verification" | "verification_label">)[]>;
  synthesis?: { compound: boolean; answered_part: string | null; list_type: string | null; evidence_types: string[]; related_types: string[] };
  evidence_strength?: EvidenceStrength;
  evidence_strength_label?: string;
  evidence_basis?: { records: number; authoritative: number; demonstration: number; other: number; note: string };
  audience?: Audience | null;
  pipeline?: { step: string; detail: string }[];
}

export interface SummaryResponse {
  kind: string;
  label: string;
  text: string;
  sources: { n: number; chunk_id: number; section: string; page: number; snippet: string; title: string; slug: string; url: string }[];
  mode: string;
  notice: string;
}

export interface EvidenceCheck {
  overall: "pass" | "warn" | "fail";
  checks: { id: string; label: string; status: "pass" | "warn" | "fail"; detail: string }[];
  sentences: { text: string; support: number; supported: boolean; best_source: number | null }[];
  method_note: string;
}

export interface ContentCitation {
  n: number;
  chunk_id: number | null;
  resource_type: string;
  resource_id: number;
  slug: string;
  label: string;
  section: string;
  page?: number | null;
  quote: string;
  url: string | null;
}

export type ContentStatus = "draft" | "evidence_checked" | "under_review" | "changes_requested" | "approved" | "published" | "rejected";

export interface ChannelStatus {
  channel: string;
  label: string;
  status: "live" | "connector_ready";
  note: string;
}

export interface ContentItem {
  id: number;
  title: string;
  format: string;
  status: ContentStatus;
  generation_mode: string;
  resource_type: string;
  resource_id: number | null;
  resource_title: string;
  created_by: string | null;
  created_by_id: number | null;
  reviewer: string | null;
  version: number;
  channels: string[];
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  approved_at: string | null;
  published_at: string | null;
  evidence_overall: "pass" | "warn" | "fail" | null;
  excerpt: string;
  audience?: string;
  language?: string;
  translated_from?: number | null;
  channel_status?: ChannelStatus[];
  provenance?: Provenance;
  body?: string;
  evidence_check?: EvidenceCheck;
  citations?: ContentCitation[];
  history?: { action: string; comment: string; by: string; at: string }[];
}

export interface Notification {
  id: number;
  title: string;
  body: string;
  link: string;
  kind: string;
  read: boolean;
  at: string;
}

export interface Health {
  status: string;
  api: string;
  database: { status: string; engine: string };
  vector_search: { status: string; backend: string; embedding_model: string | null };
  ai_provider: { status: string; model: string | null; fallback: string | null };
  storage: { status: string; backend: string };
  demo_mode: boolean;
  environment: string;
}

export interface Paged<T> {
  total: number;
  page: number;
  pages: number;
  results: T[];
}


export interface StoryItem {
  type: ResourceType;
  id: number;
  slug: string;
  title: string;
  kind: string;
  region: string;
  year: number | null;
  url: string;
  summary: string;
  is_demo: boolean;
  verification: VerificationStatus;
  verification_label: string;
  topics: string[];
  role: string;
  note: string;
  extra: { media_type?: string; scene?: string; thumbnail?: string | null; duration?: string };
}

export interface StorySummary {
  label: string;
  text: string;
  mode: string;
  notice: string;
  based_on?: { type: string; slug: string; title: string };
  sources: { n: number; chunk_id: number; section: string; page: number; snippet: string; title: string; slug: string; url: string; resource_type: string }[];
}

export interface Story {
  id: number;
  slug: string;
  title: string;
  status: "draft" | "published" | "archived";
  is_demo: boolean;
  created_at: string | null;
  updated_at: string | null;
  item_count: number;
  cover: StoryItem | null;
  roles: string[];
  basis: { items: number; demonstration: number; authoritative: number };
  items?: StoryItem[];
  timeline?: { date: string; label: string; title: string; type: string; url: string; kind: string }[];
  map_points?: { lat: number; lon: number; title: string; type: string; url: string; verification: VerificationStatus }[];
  topics?: StoryItem[];
  summaries?: Record<"scientific" | "public" | "student", StorySummary>;
  evidence?: StorySummary["sources"];
  chain?: { role: string; items: StoryItem[] }[];
  notice?: string;
  can_edit?: boolean;
}

export interface CampaignItemT {
  id: number;
  campaign_id: number;
  title: string;
  content_type: string;
  channel: string;
  channel_label: string;
  simulated_channels: string[];
  audience: string;
  scheduled_for: string | null;
  status: "planned" | "scheduled" | "published" | "cancelled";
  notes: string;
  content: { id: number; title: string; status: ContentStatus; format: string; audience: string; published_at: string | null; is_demo: boolean } | null;
  blockers: string[];
  can_schedule: boolean;
  can_publish: boolean;
  campaign?: { slug: string; name: string; is_demo: boolean };
}

export interface CampaignT {
  id: number;
  slug: string;
  name: string;
  description: string;
  start_date: string | null;
  end_date: string | null;
  audiences: { key: string; label: string }[];
  topics: string[];
  channels: { key: string; label: string; simulated: boolean }[];
  status: "draft" | "scheduled" | "published" | "archived";
  is_demo: boolean;
  item_counts: Record<string, number>;
  items_total: number;
  items?: CampaignItemT[];
}
