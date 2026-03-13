export interface ParsedQuery {
  cities: string[];
  state: string | null;
  neighborhoods: string[];
  property_types: string[];
  operation: string | null;
  street: string | null;
  min_bedrooms: number | null;
  max_bedrooms: number | null;
  min_bathrooms: number | null;
  max_bathrooms: number | null;
  min_price: number | null;
  max_price: number | null;
  min_surface: number | null;
  max_surface: number | null;
  min_roofed_surface: number | null;
  max_roofed_surface: number | null;
  condition: string | null;
  currency: string | null;
  semantic_query: string;
  clean_query: string;
}

export interface PropertyResult {
  score: number;
  id: string | null;
  title: string | null;
  property_type: string | null;
  operation: string | null;
  price: number | null;
  currency: string | null;
  city: string | null;
  state: string | null;
  neighborhood: string | null;
  address: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  surface: number | null;
  roofed_surface: number | null;
  condition: string | null;
  internal_id: string | null;
  agent_first_name: string | null;
  agent_last_name: string | null;
  agent_company: string | null;
  agent_phone: string | null;
  address_name: string | null;
}

export interface SearchMetrics {
  parse_time_ms: number;
  embed_time_ms: number;
  search_time_ms: number;
  total_time_ms: number;
  candidates_before_filter: number;
  score_min: number;
  score_max: number;
  score_avg: number;
}

export interface FacetBucket {
  value: string;
  count: number;
}

export interface DisambiguationInfo {
  field: string;
  buckets: FacetBucket[];
}

export interface SearchResult {
  query: string;
  parsed_filters: ParsedQuery;
  filters_applied: boolean;
  results: PropertyResult[];
  total: number;
  metrics: SearchMetrics;
  disambiguation: DisambiguationInfo[];
  /** Pre-fetched top-K results per state. Keys = exact Qdrant state values. */
  state_results: Record<string, PropertyResult[]>;
}

export interface EmbeddingModelInfo {
  id: string;
  collection: string;
  dimensions: number;
  is_default: boolean;
}

export interface HealthStatus {
  status: string;
}

// Chat types

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  results?: PropertyResult[];
  filters?: ParsedQuery;
  disambiguation?: DisambiguationInfo[];
  stateResults?: Record<string, PropertyResult[]>;
  metrics?: SearchMetrics;
  isStreaming?: boolean;
  isSearching?: boolean;
}

export interface ChatRequest {
  message: string;
  session_id?: string | null;
  model: string;
  top_k: number;
}

export type ChatEventType =
  | "session"
  | "token"
  | "tool_start"
  | "results"
  | "filters"
  | "disambiguation"
  | "state_results"
  | "metrics"
  | "done"
  | "error";

// Multimodal types

export interface MultimodalPropertyResult {
  score: number;
  id: string | null;
  firebase_id: string | null;
  title: string | null;
  description: string | null;
  house_type: string | null;
  city: string | null;
  state: string | null;
  suburb: string | null;
  address: string | null;
  bedroom: number | null;
  bathroom: number | null;
  half_bathroom: number | null;
  construction_area: number | null;
  land_area: number | null;
  price: number | null;
  currency: string | null;
  operation: string | null;
  condition: string | null;
  antiquity: string | null;
  pictures: string[];
  amenities: string[];
  exterior_selected: string[];
  general_selected: string[];
  near_places: string[];
  parking_lot: number | null;
  lat: number | null;
  lng: number | null;
  ad_copy: string | null;
}

export interface MultimodalSearchMetrics {
  embed_time_ms: number;
  search_time_ms: number;
  total_time_ms: number;
  total_candidates: number;
}

export interface MultimodalSearchResult {
  query: string;
  search_mode: "text" | "image" | "hybrid";
  results: MultimodalPropertyResult[];
  total: number;
  metrics: MultimodalSearchMetrics;
}
