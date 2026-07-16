// Domain Overview & Organic Research Workspace types
// Matches backend seo_domain.py contracts (Pydantic models)

export type DataSourceType =
  | "semrush"
  | "ahrefs"
  | "google_search_console"
  | "google_analytics"
  | "data_for_seo"
  | "custom"
  | "estimated";

export type KeywordIntent =
  | "informational"
  | "navigational"
  | "commercial"
  | "transactional";

export type PositionChangeDirection = "up" | "down" | "new" | "lost" | "unchanged";
export type TrafficTrend = "up" | "down" | "stable";

// Core Domain Overview Metrics (matches DomainOverviewMetrics)
export interface DomainOverviewMetrics {
  domain: string;
  organic_keywords: number;
  organic_traffic: number;
  organic_traffic_cost: number;
  paid_keywords: number;
  paid_traffic: number;
  paid_traffic_cost: number;
  authority_score: number;
  backlinks: number;
  referring_domains: number;
  traffic_trend: TrafficTrend;
  trend_percentage: number;
  last_updated: string;
  data_source: DataSourceType;
  country: string;
  language: string;
}

export interface DomainOverviewHistoryPoint {
  date: string;
  organic_keywords: number;
  organic_traffic: number;
  organic_traffic_cost: number;
  paid_keywords: number;
  paid_traffic: number;
  paid_traffic_cost: number;
  backlinks: number;
  referring_domains: number;
  authority_score: number;
}

// Organic Keywords (matches OrganicKeyword)
export interface OrganicKeyword {
  keyword: string;
  position: number;
  previous_position: number | null;
  position_change: number;
  url: string;
  search_volume: number;
  keyword_difficulty: number;
  cpc: number;
  traffic: number;
  traffic_percentage: number;
  traffic_cost: number;
  intent: KeywordIntent;
  serps_features: string[];
  results_count: number;
  last_updated: string;
  data_source: DataSourceType;
  country: string;
  language: string;
}

export interface OrganicKeywordFilters {
  keyword?: string;
  position_min?: number;
  position_max?: number;
  volume_min?: number;
  volume_max?: number;
  difficulty_min?: number;
  difficulty_max?: number;
  intent?: KeywordIntent;
  serps_feature?: string;
  url_contains?: string;
  position_change_min?: number;
  position_change_max?: number;
  traffic_min?: number;
  date_from?: string;
  date_to?: string;
}

export interface OrganicKeywordsRequest {
  domain: string;
  country: string;
  language: string;
  filters?: OrganicKeywordFilters;
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: "asc" | "desc";
  data_sources?: DataSourceType[];
  use_cache: boolean;
}

// Organic Pages (matches OrganicPage)
export interface OrganicPage {
  url: string;
  organic_keywords: number;
  organic_traffic: number;
  organic_traffic_cost: number;
  traffic_percentage: number;
  top_keyword: string;
  top_keyword_position: number;
  top_keyword_volume: number;
  backlinks: number;
  referring_domains: number;
  page_type: string;
  word_count: number | null;
  last_updated: string;
  data_source: DataSourceType;
}

export interface OrganicPageFilters {
  url_contains?: string;
  keywords_min?: number;
  keywords_max?: number;
  traffic_min?: number;
  traffic_max?: number;
  page_type?: string;
  date_from?: string;
  date_to?: string;
  has_backlinks?: boolean;
}

export interface OrganicPagesRequest {
  domain: string;
  country: string;
  language: string;
  filters?: OrganicPageFilters;
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: "asc" | "desc";
  data_sources?: DataSourceType[];
  use_cache: boolean;
}

// Competitors (matches Competitor)
export interface Competitor {
  domain: string;
  common_keywords: number;
  organic_keywords: number;
  organic_traffic: number;
  organic_traffic_cost: number;
  paid_keywords: number;
  paid_traffic: number;
  paid_traffic_cost: number;
  backlinks: number;
  referring_domains: number;
  authority_score: number;
  competition_level: number;
  top_keywords: OrganicKeyword[];
  last_updated: string;
  data_source: DataSourceType;
}

export interface CompetitorFilters {
  domain_contains?: string;
  common_keywords_min?: number;
  traffic_min?: number;
  authority_min?: number;
  date_from?: string;
  date_to?: string;
}

export interface CompetitorsRequest {
  domain: string;
  country: string;
  language: string;
  filters?: CompetitorFilters;
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: "asc" | "desc";
  data_sources?: DataSourceType[];
  use_cache: boolean;
}

// Position Changes (matches PositionChange)
export interface PositionChange {
  keyword: string;
  url: string;
  current_position: number;
  previous_position: number | null;
  change: number;
  direction: PositionChangeDirection;
  search_volume: number;
  traffic_impact: number;
  intent: KeywordIntent;
  date_detected: string;
  data_source: DataSourceType;
}

export interface PositionChangesFilters {
  direction?: PositionChangeDirection;
  keyword_contains?: string;
  url_contains?: string;
  volume_min?: number;
  change_min?: number;
  change_max?: number;
  intent?: KeywordIntent;
  date_from?: string;
  date_to?: string;
}

export interface PositionChangesRequest {
  domain: string;
  country: string;
  language: string;
  filters?: PositionChangesFilters;
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: "asc" | "desc";
  data_sources?: DataSourceType[];
  use_cache: boolean;
}

// Data Sources
export interface DataSourceStatus {
  source: DataSourceType;
  configured: boolean;
  status: string;
  last_sync: string | null;
  quota_remaining: number | null;
  quota_total: number | null;
  error_message: string | null;
  supported_features: string[];
}

export interface DataSourcesResponse {
  sources: DataSourceStatus[];
  primary_source: DataSourceType | null;
}

// Response Types (matches backend PaginatedResponse)
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  filters_applied?: any;
}

export type OrganicKeywordsResponse = PaginatedResponse<OrganicKeyword>;
export type OrganicPagesResponse = PaginatedResponse<OrganicPage>;
export type CompetitorsResponse = PaginatedResponse<Competitor>;
export type PositionChangesResponse = PaginatedResponse<PositionChange>;

export interface DomainOverviewResponse {
  metrics: DomainOverviewMetrics;
  history: DomainOverviewHistoryPoint[];
  data_sources: DataSourcesResponse;
  last_refresh: string;
}

export interface BulkDomainOverviewRequest {
  domains: string[];
  country: string;
  language: string;
  data_sources?: DataSourceType[];
  use_cache: boolean;
}

export interface BulkDomainOverviewResponse {
  results: Record<string, DomainOverviewResponse>;
  errors: Record<string, string>;
  processed: number;
  failed: number;
  completed_at: string;
}

export interface ExportDomainOverviewRequest {
  domain: string;
  format: "json" | "csv" | "xlsx";
  sections: string[];
  date_from?: string;
  date_to?: string;
  filters: Record<string, any>;
}

export interface ExportDomainOverviewResponse {
  export_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  download_url: string | null;
  expires_at: string | null;
  file_size_bytes: number | null;
  error: string | null;
}