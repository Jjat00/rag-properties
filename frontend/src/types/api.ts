export interface ParsedQuery {
  city: string | null;
  state: string | null;
  neighborhood: string | null;
  property_type: string | null;
  operation: string | null;
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

export interface SearchResult {
  query: string;
  parsed_filters: ParsedQuery;
  filters_applied: boolean;
  results: PropertyResult[];
  total: number;
  metrics: SearchMetrics;
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
