export type ResourceType = "document" | "dataset" | "media" | "expedition" | "station" | "researcher" | "topic";
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
}

export interface SearchResult extends Card {
  score: number;
  relevance: number | null;
  matched_terms: string[];
  matching_concepts: string[];
  match_type: string;
  highlight: string;
  matched_section: string;
}

export interface Facets {
  regions: Record<string, number>;
  types: Record<string, number>;
  topics: Record<string, number>;
  year_min: number | null;
  year_max: number | null;
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
}

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
  quote: string;
  url: string | null;
}

export type ContentStatus = "draft" | "under_review" | "changes_requested" | "approved" | "published" | "rejected";

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
