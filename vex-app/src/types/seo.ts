// Core SEO types matching backend seo_core.py contracts
// These are the canonical types shared between frontend and backend

export type IssueSeverity = "P0" | "P1" | "P2" | "P3";

export type IssueCategory =
  | "technical"
  | "content"
  | "on_page"
  | "technical_seo"
  | "performance"
  | "mobile"
  | "structured_data"
  | "international"
  | "ecommerce"
  | "security"
  | "accessibility"
  | "links"
  | "images";

export type PageType =
  | "homepage"
  | "collection"
  | "product"
  | "blog_article"
  | "content_page"
  | "cart"
  | "account"
  | "policy"
  | "search"
  | "unknown"
  | "category"
  | "tag"
  | "author"
  | "archive"
  | "landing"
  | "thank_you"
  | "404"
  | "500";

export type CrawlStatus =
  | "pending"
  | "queued"
  | "crawling"
  | "completed"
  | "failed"
  | "skipped"
  | "blocked"
  | "redirected"
  | "timeout"
  | "error";

export type IndexabilityStatus =
  | "indexable"
  | "noindex"
  | "canonicalized"
  | "redirected"
  | "blocked_robots"
  | "blocked_robots_txt"
  | "noindex_nofollow"
  | "canonical_mismatch"
  | "unknown";

export type RedirectType =
  | "301"
  | "302"
  | "303"
  | "307"
  | "308"
  | "meta_refresh"
  | "js_redirect"
  | "unknown";

export type StructuredDataType =
  | "WebSite"
  | "Organization"
  | "LocalBusiness"
  | "Product"
  | "ProductGroup"
  | "BlogPosting"
  | "Article"
  | "NewsArticle"
  | "BreadcrumbList"
  | "ItemList"
  | "FAQPage"
  | "HowTo"
  | "VideoObject"
  | "ImageObject"
  | "Person"
  | "Brand"
  | "Offer"
  | "AggregateRating"
  | "Review"
  | "WebPage"
  | "CollectionPage"
  | "ProductPage"
  | "Blog"
  | "SiteNavigationElement"
  | "Table"
  | "DataSet"
  | "SoftwareApplication"
  | "MobileApplication"
  | "WebApplication"
  | "Service"
  | "Event"
  | "Course"
  | "JobPosting"
  | "FAQ"
  | "HowToSection"
  | "HowToStep"
  | "unknown";

export type CoreWebVitalsMetric = "LCP" | "FID" | "CLS" | "INP" | "FCP" | "TTFB";

export type CWVRating = "good" | "needs_improvement" | "poor";

export type HttpStatusCategory = "1xx" | "2xx" | "3xx" | "4xx" | "5xx";

// Crawl Configuration
export interface CrawlConfig {
  start_url: string;
  max_pages: number;
  max_depth: number;
  follow_redirects: boolean;
  max_redirects: number;
  respect_robots_txt: boolean;
  respect_nofollow: boolean;
  respect_noindex: boolean;
  crawl_subdomains: boolean;
  crawl_external_links: boolean;
  allowed_domains: string[];
  blocked_domains: string[];
  allowed_paths: string[];
  blocked_paths: string[];
  user_agent: string;
  request_timeout: number;
  max_concurrent: number;
  delay_between_requests: number;
  render_javascript: boolean;
  wait_for_network_idle: boolean;
  wait_for_selector: string | null;
  screenshot_on_error: boolean;
  custom_headers: Record<string, string>;
  cookies: Record<string, string>;
  auth: Record<string, string> | null;
  country: string;
  language: string;
  viewport_width: number;
  viewport_height: number;
  business_description: string;
  include_ai_recommendations: boolean;
  ai_model: string;
  max_ai_tokens: number;
  prioritize_urls: string[];
  max_content_length: number;
  extract_structured_data: boolean;
  extract_performance_metrics: boolean;
  extract_accessibility: boolean;
  extract_security_headers: boolean;
  follow_canonical: boolean;
  follow_pagination: boolean;
  max_pagination_pages: number;
}

// Core SEO Issue
export interface SeoIssueCore {
  id: string;
  severity: IssueSeverity;
  category: IssueCategory;
  code: string;
  message: string;
  description: string;
  recommendation: string;
  url: string;
  page_type: PageType;
  scope: "page" | "site" | "crawl" | "pattern";
  affected_urls: string[];
  current_value: string;
  expected_value: string;
  platform_hint: string;
  confidence: number;
  impact_score: number;
  effort_score: number;
  tags: string[];
  references: string[];
  detected_at: string;
  is_auto_fixable: boolean;
  auto_fix_suggestion: string;
}

// SEO Recommendation
export interface SeoRecommendationCore {
  id: string;
  priority: IssueSeverity;
  category: IssueCategory;
  title: string;
  description: string;
  detailed_explanation: string;
  impact: "critical" | "high" | "medium" | "low";
  effort: "low" | "medium" | "high" | "very_high";
  urls_affected: string[];
  page_types_affected: PageType[];
  platform_hint: string;
  implementation_steps: string[];
  code_examples: Record<string, string>;
  tools_to_verify: string[];
  related_issues: string[];
  estimated_impact_score: number;
  confidence: number;
  ai_generated: boolean;
  ai_model: string | null;
  created_at: string;
}

// Page Score Breakdown
export interface PageScoreBreakdown {
  overall: number;
  technical: number;
  content: number;
  on_page: number;
  performance: number;
  mobile: number;
  structured_data: number;
  links: number;
  images: number;
  security: number;
  accessibility: number;
  factors: string[];
  penalties: string[];
  bonuses: string[];
}

// Site Score Breakdown
export interface SiteScoreBreakdown {
  overall: number;
  technical_health: number;
  content_quality: number;
  on_page_optimization: number;
  site_architecture: number;
  crawlability: number;
  indexability: number;
  performance: number;
  mobile_usability: number;
  structured_data_coverage: number;
  internal_linking: number;
  international_seo: number;
  security: number;
  factors: string[];
  critical_issues: number;
  high_issues: number;
  medium_issues: number;
  low_issues: number;
}

// SEO Project (new shared type)
export interface SeoProject {
  id: string;
  name: string;
  domain: string;
  description: string;
  created_at: string;
  updated_at: string;
  settings: {
    max_pages: number;
    max_depth: number;
    crawl_config?: Partial<CrawlConfig>;
  };
  audit_history: SeoAuditHistoryItem[];
  active_audit_id: string | null;
  last_audit_at: string | null;
  last_score: number | null;
}

export interface SeoAuditHistoryItem {
  audit_id: string;
  score: number;
  crawled_pages: number;
  completed_at: string;
}

// Capabilities response
export interface SeoCapabilities {
  max_pages_per_audit: number;
  max_depth: number;
  max_concurrent_requests: number;
  supported_page_types: PageType[];
  issue_severities: IssueSeverity[];
  issue_categories: IssueCategory[];
  crawl_statuses: CrawlStatus[];
  indexability_statuses: IndexabilityStatus[];
  redirect_types: RedirectType[];
  structured_data_types: StructuredDataType[];
  core_web_vitals_metrics: CoreWebVitalsMetric[];
  cwv_ratings: CWVRating[];
  http_status_categories: HttpStatusCategory[];
  supported_export_formats: string[];
  supported_report_templates: string[];
  ai_models: string[];
  features: Record<string, boolean>;
}

// Provider status
export interface ProviderStatus {
  google_search_console: ProviderInfo;
  google_analytics: ProviderInfo;
  ahrefs: ProviderInfo;
  semrush: ProviderInfo;
  screaming_frog: ProviderInfo;
  sitebulb: ProviderInfo;
}

export interface ProviderInfo {
  configured: boolean;
  connected: boolean;
  last_sync: string | null;
  error: string | null;
  scopes: string[];
}

// Site Audit Workspace types
export interface AuditComparison {
  baseline_audit_id: string;
  comparison_audit_id: string;
  baseline_date: string;
  comparison_date: string;
  score_change: number;
  score_change_pct: number;
  issues_resolved: number;
  issues_new: number;
  issues_worsened: number;
  issues_improved: number;
  pages_improved: number;
  pages_declined: number;
  top_improvements: string[];
  top_regressions: string[];
  category_changes: Record<string, number>;
}

export interface AuditProgress {
  audit_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress_pct: number;
  current_url: string;
  current_depth: number;
  urls_queued: number;
  urls_crawled: number;
  urls_failed: number;
  urls_skipped: number;
  elapsed_seconds: number;
  estimated_remaining_seconds: number | null;
  pages_per_second: number;
  recent_errors: Array<Record<string, unknown>>;
  timestamp: string;
}

export interface SeoAudit {
  id: string;
  requested_url: string;
  normalized_url: string;
  status: "completed" | "failed" | "running" | "pending";
  created_at: string;
  max_pages: number;
  crawled_pages: number;
  score: number;
  project_id: string | null;
  issues: SeoIssue[];
  recommendations: Array<{
    priority: string;
    title: string;
    detail: string;
    platform_hint: string;
  }>;
  pages: SeoAuditPage[];
  site_signals: Record<string, unknown>;
  crawl_errors: string[];
  ai_recommendations: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  progress: AuditProgress | null;
}

export interface AuditListParams {
  page?: number;
  page_size?: number;
  status?: string[];
  project_id?: string;
  date_from?: string;
  date_to?: string;
  min_score?: number;
  max_score?: number;
  search?: string;
  sort_by?: "created_at" | "score" | "crawled_pages" | "status";
  sort_order?: "asc" | "desc";
}

export interface AuditListResponse {
  audits: SeoAudit[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ExportFormat {
  format: "csv" | "json" | "markdown";
  type: "issues" | "pages" | "both";
  include_details: boolean;
}

// Re-export existing types for compatibility
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

export type SeoIssuePriority = IssueSeverity;

// Frontend type alias for SeoAuditIssue compatibility
export type SeoIssue = SeoAuditIssue;

export interface SeoAuditRequest {
  url: string;
  country: string;
  language: string;
  business_description: string;
  max_pages: number;
  project_id?: string;
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