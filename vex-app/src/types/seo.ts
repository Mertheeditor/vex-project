export type SeoAuditStageKey =
  | "connection"
  | "robots_sitemap"
  | "crawl"
  | "technical_seo"
  | "on_page"
  | "keyword_content"
  | "report_completed";

export type SeoAuditStatus =
  | "initial"
  | "loading"
  | "crawling"
  | "completed"
  | "url_error"
  | "unreachable"
  | "partial"
  | "backend_error"
  | "empty";

export type SeoIssuePriority = "P0" | "P1" | "P2" | "P3" | string;

export interface SeoAuditRequest {
  url: string;
  country: string;
  language: string;
  business_description: string;
  max_pages: number;
}

export interface SeoCrawlStats {
  discovered_urls?: number;
  crawled_urls?: number;
  skipped_urls?: number;
  blocked_urls?: number;
  errored_urls?: number;
}

export interface SeoAuditStage {
  key?: SeoAuditStageKey | string;
  name?: string;
  status?: string;
  message?: string;
}

export interface SeoAuditSummary {
  score?: number;
  pages?: number;
  pages_crawled?: number;
  total_pages?: number;
  p0?: number;
  p1?: number;
  p2?: number;
  p3?: number;
  issues?: number;
  [key: string]: unknown;
}

export interface SeoAuditPage {
  url?: string;
  status?: number | string;
  score?: number;
  page_score?: number | null;
  page_type?: string;
  platform?: string;
  score_reasons?: string[];
  title?: string;
  h1?: string | string[];
  index?: boolean | string;
  indexable?: boolean | string;
  word_count?: number;
  words?: number;
  issues?: number | SeoAuditIssue[];
  [key: string]: unknown;
}

export interface SeoAuditIssue {
  id?: string;
  priority?: SeoIssuePriority;
  name?: string;
  title?: string;
  url?: string;
  current?: string;
  recommended?: string;
  recommendation?: string;
  explanation?: string;
  how?: string;
  how_to_fix?: string;
  platform?: string;
  category?: string;
  page_url?: string;
  current_value?: string;
  page_type?: string;
  scope?: string;
  [key: string]: unknown;
}

export interface SeoKeywordRecommendation {
  keyword?: string;
  placement?: string;
  recommendation?: string;
  reason?: string;
  source?: "heuristic" | "ai" | string;
  page_url?: string;
  [key: string]: unknown;
}

export interface SeoContentRecommendation {
  title?: string;
  page_url?: string;
  recommendation?: string;
  reason?: string;
  source?: "heuristic" | "ai" | string;
  [key: string]: unknown;
}

export interface SeoImplementationPlanItem {
  priority?: SeoIssuePriority;
  title?: string;
  task?: string;
  impact?: string;
  effort?: string;
  steps?: string[];
  [key: string]: unknown;
}

export interface SeoAuditResult {
  audit_id: string;
  status: SeoAuditStatus | string;
  stages?: SeoAuditStage[] | Record<string, SeoAuditStage | string>;
  summary?: SeoAuditSummary;
  crawl_stats?: SeoCrawlStats;
  pages?: SeoAuditPage[];
  issues?: SeoAuditIssue[];
  keyword_recommendations?: SeoKeywordRecommendation[];
  content_recommendations?: SeoContentRecommendation[];
  implementation_plan?: SeoImplementationPlanItem[];
  [key: string]: unknown;
}
