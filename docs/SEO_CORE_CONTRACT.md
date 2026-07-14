# SEO Core Contract

Bu doküman Vex SEO sistemi için backend ve frontend arasındaki paylaşılan sözleşmeyi (contract) tanımlar. API endpoint'leri, types, enum değerleri ve veri modelleri burada yer alır.

## Version: 1.0.0
## Last Updated: 2025-07-14

---

## 1. Base URL ve Authentication

```
Base URL: http://127.0.0.1:8000
Content-Type: application/json
Authentication: None (local development)
```

---

## 2. Enums ve Sabit Değerler

### 2.1 Issue Severity (Öncelik Seviyeleri)
```typescript
type IssueSeverity = "P0" | "P1" | "P2" | "P3";

const ISSUE_SEVERITY_LABELS: Record<IssueSeverity, string> = {
  P0: "Kritik - Indexleme/sıralamayı engeller",
  P1: "Yüksek - SEO'yu ciddi etkiler",
  P2: "Orta - Ölçülü SEO etkisi",
  P3: "Düşük - Küçük iyileştirme",
};
```

### 2.2 Issue Category (Kategoriler)
```typescript
type IssueCategory =
  | "technical"           // Crawling, indexing, rendering
  | "content"             // İçerik kalitesi, ilgili, yapı
  | "on_page"             // Title, meta, headings, yapı
  | "technical_seo"       // Robots, sitemap, canonical, hreflang
  | "performance"         // Hız, Core Web Vitals
  | "mobile"              // Mobil kullanabilirlik, viewport
  | "structured_data"     // Schema.org, JSON-LD
  | "international"       // Hreflang, geo-targeting
  | "ecommerce"           // Product schema, inventory, reviews
  | "security"            // HTTPS, mixed content, security headers
  | "accessibility"       // A11y SEO'yu etkileyenler
  | "links"               // İç/dış linkler, anchor, redirect
  | "images";             // Alt text, sizing, formats, lazy-loading
```

### 2.3 Page Type (Sayfa Türleri)
```typescript
type PageType =
  | "homepage" | "collection" | "product" | "blog_article"
  | "content_page" | "cart" | "account" | "policy"
  | "search" | "unknown" | "category" | "tag" | "author"
  | "archive" | "landing" | "thank_you" | "404" | "500";
```

### 2.4 Crawl Status
```typescript
type CrawlStatus =
  | "pending" | "queued" | "crawling" | "completed"
  | "failed" | "skipped" | "blocked" | "redirected"
  | "timeout" | "error";
```

### 2.5 Indexability Status
```typescript
type IndexabilityStatus =
  | "indexable" | "noindex" | "canonicalized" | "redirected"
  | "blocked_robots" | "blocked_robots_txt" | "noindex_nofollow"
  | "canonical_mismatch" | "unknown";
```

### 2.6 Redirect Type
```typescript
type RedirectType =
  | "301" | "302" | "303" | "307" | "308"
  | "meta_refresh" | "js_redirect" | "unknown";
```

### 2.7 Structured Data Type
```typescript
type StructuredDataType =
  | "WebSite" | "Organization" | "LocalBusiness" | "Product"
  | "ProductGroup" | "BlogPosting" | "Article" | "NewsArticle"
  | "BreadcrumbList" | "ItemList" | "FAQPage" | "HowTo"
  | "VideoObject" | "ImageObject" | "Person" | "Brand"
  | "Offer" | "AggregateRating" | "Review" | "WebPage"
  | "CollectionPage" | "ProductPage" | "Blog"
  | "SiteNavigationElement" | "Table" | "DataSet"
  | "SoftwareApplication" | "MobileApplication" | "WebApplication"
  | "Service" | "Event" | "Course" | "JobPosting" | "FAQ"
  | "HowToSection" | "HowToStep" | "unknown";
```

### 2.8 Core Web Vitals Metric
```typescript
type CoreWebVitalsMetric = "LCP" | "FID" | "CLS" | "INP" | "FCP" | "TTFB";
```

### 2.9 CWV Rating
```typescript
type CWVRating = "good" | "needs_improvement" | "poor";
```

### 2.10 HTTP Status Category
```typescript
type HttpStatusCategory = "1xx" | "2xx" | "3xx" | "4xx" | "5xx";
```

---

## 3. Core Data Models

### 3.1 CrawlConfig
```typescript
interface CrawlConfig {
  start_url: string;                    // HTTP/HTTPS URL
  max_pages: number;                    // 1-5000 (default: 100)
  max_depth: number;                    // 0-50 (default: 10)
  follow_redirects: boolean;            // default: true
  max_redirects: number;                // 0-50 (default: 10)
  respect_robots_txt: boolean;          // default: true
  respect_nofollow: boolean;            // default: true
  respect_noindex: boolean;             // default: true
  crawl_subdomains: boolean;            // default: false
  crawl_external_links: boolean;        // default: false
  allowed_domains: string[];            // default: []
  blocked_domains: string[];            // default: []
  allowed_paths: string[];              // default: []
  blocked_paths: string[];              // default: []
  user_agent: string;                   // default: "VexBot/1.0"
  request_timeout: number;              // 5-120s (default: 30)
  max_concurrent: number;               // 1-50 (default: 5)
  delay_between_requests: number;       // 0-10s (default: 0.5)
  render_javascript: boolean;           // default: false
  wait_for_network_idle: boolean;       // default: true
  wait_for_selector?: string;           // Optional CSS selector
  screenshot_on_error: boolean;         // default: false
  custom_headers: Record<string, string>; // default: {}
  cookies: Record<string, string>;      // default: {}
  auth?: Record<string, string>;        // Optional auth
  country: string;                      // default: ""
  language: string;                     // default: ""
  viewport_width: number;               // 320-3840 (default: 1920)
  viewport_height: number;              // 240-2160 (default: 1080)
  business_description: string;         // default: ""
  include_ai_recommendations: boolean;  // default: false
  ai_model: string;                     // default: "gpt-4o-mini"
  max_ai_tokens: number;                // 500-8000 (default: 2000)
  prioritizeUrls: string[];             // default: []
  max_content_length: number;           // 100000-100000000 (default: 10MB)
  extract_structured_data: boolean;     // default: true
  extract_performance_metrics: boolean; // default: true
  extract_accessibility: boolean;       // default: true
  extract_security_headers: boolean;    // default: true
  follow_canonical: boolean;            // default: true
  follow_pagination: boolean;           // default: true
  max_pagination_pages: number;         // 0-1000 (default: 100)
}
```

### 3.2 SeoIssueCore (Core SEO Issue)
```typescript
interface SeoIssueCore {
  id: string;                           // Auto-generated
  severity: IssueSeverity;              // default: P2
  category: IssueCategory;              // default: technical
  code: string;                         // Issue code (e.g., "missing_title")
  message: string;                      // Human-readable message
  description: string;                  // Detailed description
  recommendation: string;               // Actionable fix recommendation
  url: string;                          // Affected URL
  page_type: PageType;                  // default: unknown
  scope: "page" | "site" | "crawl" | "pattern"; // default: page
  affected_urls: string[];              // Related URLs
  current_value: string;                // Current problematic value
  expected_value: string;               // Expected correct value
  platform_hint: string;                // default: "generic"
  confidence: number;                   // 0.0-1.0 (default: 1.0)
  impact_score: number;                 // 1-10 (default: 5)
  effort_score: number;                 // 1-10 (default: 5)
  tags: string[];                       // default: []
  references: string[];                 // default: []
  detected_at: string;                  // ISO datetime
  is_auto_fixable: boolean;             // default: false
  auto_fix_suggestion: string;          // default: ""
}
```

### 3.3 SeoRecommendationCore
```typescript
interface SeoRecommendationCore {
  id: string;                           // Auto-generated
  priority: IssueSeverity;              // default: P2
  category: IssueCategory;              // default: technical
  title: string;                        // Short title
  description: string;                  // Summary
  detailed_explanation: string;         // Full explanation
  impact: "critical" | "high" | "medium" | "low"; // default: medium
  effort: "low" | "medium" | "high" | "very_high"; // default: medium
  urls_affected: string[];              // default: []
  page_types_affected: PageType[];      // default: []
  platform_hint: string;                // default: "generic"
  implementation_steps: string[];       // default: []
  code_examples: Record<string, string>; // default: {}
  tools_to_verify: string[];            // default: []
  related_issues: string[];             // default: []
  estimated_impact_score: number;       // 1-10 (default: 5)
  confidence: number;                   // 0.0-1.0 (default: 0.8)
  ai_generated: boolean;                // default: false
  ai_model?: string;                    // Optional
  created_at: string;                   // ISO datetime
}
```

### 3.4 CrawlUrlResult (Single URL Crawl Result)
```typescript
interface CrawlUrlResult {
  url: string;
  normalized_url: string;
  final_url: string;
  status: CrawlStatus;
  status_code: number | null;
  status_category: HttpStatusCategory | null;
  redirect_chain: string[];
  redirect_type: RedirectType | null;
  content_type: string;
  content_length: number;
  load_time_ms: number;
  ttfb_ms: number;
  dom_content_loaded_ms: number;
  depth: number;
  page_type: PageType;
  indexability: IndexabilityStatus;
  canonical_url: string;
  canonical_status: "valid" | "self" | "missing" | "mismatch" | "redirect" | "blocked" | "multiple";
  robots_meta: string;
  x_robots_tag: string;
  hreflang_tags: Array<Record<string, string>>;
  title: string;
  meta_description: string;
  meta_keywords: string;
  h1_tags: string[];
  h2_tags: string[];
  h3_tags: string[];
  h4_tags: string[];
  h5_tags: string[];
  h6_tags: string[];
  word_count: number;
  text_html_ratio: number;
  internal_links: LinkInfo[];
  external_links: LinkInfo[];
  images: ImageInfo[];
  structured_data: StructuredDataItem[];
  open_graph: Record<string, string>;
  twitter_card: Record<string, string>;
  json_ld: Record<string, any>[];
  microdata: Record<string, any>[];
  rdfa: Record<string, any>[];
  viewport: string;
  charset: string;
  language: string;
  hreflang: string;
  response_headers: Record<string, string>;
  security_headers: SecurityHeaders;
  performance_metrics?: PerformanceMetrics;
  accessibility_issues: AccessibilityIssue[];
  seo_issues: SeoIssueCore[];
  content_hash: string;
  simhash: string;
  crawled_at: string;
  error?: string;
  error_type?: string;
  skipped_reason?: string;
}
```

### 3.5 Supporting Models

#### LinkInfo
```typescript
interface LinkInfo {
  url: string;
  normalized_url: string;
  anchor_text: string;
  title_attribute: string;
  rel_attributes: string[];
  is_internal: boolean;
  is_nofollow: boolean;
  is_sponsored: boolean;
  is_ugc: boolean;
  is_external: boolean;
  link_type: "nav" | "footer" | "sidebar" | "content" | "breadcrumb" | "pagination" | "other";
  status_code: number | null;
  redirect_chain: string[];
  is_broken: boolean;
  is_redirect: boolean;
}
```

#### ImageInfo
```typescript
interface ImageInfo {
  src: string;
  alt: string;
  title: string;
  width: number | null;
  height: number | null;
  file_size: number | null;
  format: string;
  is_lazy_loaded: boolean;
  has_srcset: boolean;
  has_sizes: boolean;
  is_webp: boolean;
  is_avif: boolean;
  missing_alt: boolean;
  empty_alt: boolean;
  alt_too_long: boolean;
  alt_keyword_stuffing: boolean;
}
```

#### StructuredDataItem
```typescript
interface StructuredDataItem {
  type: StructuredDataType;
  raw_type: string;
  format: "json-ld" | "microdata" | "rdfa";
  data: Record<string, any>;
  is_valid: boolean;
  validation_errors: string[];
  namespace: string;
}
```

#### SecurityHeaders
```typescript
interface SecurityHeaders {
  strict_transport_security: string;
  content_security_policy: string;
  x_frame_options: string;
  x_content_type_options: string;
  referrer_policy: string;
  permissions_policy: string;
  cross_origin_opener_policy: string;
  cross_origin_embedder_policy: string;
  cross_origin_resource_policy: string;
  has_hsts: boolean;
  has_csp: boolean;
  hsts_max_age: number;
  hsts_includes_subdomains: boolean;
  hsts_preload: boolean;
  csp_report_only: boolean;
  issues: string[];
}
```

#### PerformanceMetrics
```typescript
interface PerformanceMetrics {
  lcp_ms: number | null;
  fid_ms: number | null;
  inp_ms: number | null;
  cls_score: number | null;
  fcp_ms: number | null;
  ttfb_ms: number | null;
  dom_content_loaded_ms: number | null;
  load_event_ms: number | null;
  total_blocking_time_ms: number | null;
  speed_index: number | null;
  lcp_rating: CWVRating | null;
  fid_rating: CWVRating | null;
  inp_rating: CWVRating | null;
  cls_rating: CWVRating | null;
  overall_rating: CWVRating | null;
  lab_data: boolean;
  field_data: boolean;
  measured_at: string;
}
```

#### AccessibilityIssue
```typescript
interface AccessibilityIssue {
  type: string;
  severity: IssueSeverity;
  message: string;
  element: string;
  selector: string;
  wcag_criterion: string;
  impact: "critical" | "serious" | "moderate" | "minor";
}
```

---

## 4. API Endpoints

### 4.1 SEO Project Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/seo/projects` | Yeni SEO projesi oluştur |
| GET | `/seo/projects` | Tüm SEO projelerini listele |
| GET | `/seo/projects/{project_id}` | Proje detayı getir |
| PATCH | `/seo/projects/{project_id}` | Proje güncelle |
| DELETE | `/seo/projects/{project_id}` | Proje sil |
| GET | `/seo/projects/{project_id}/config` | Proje için varsayılan crawl config |
| POST | `/seo/projects/{project_id}/audits` | Proje için audit başlat |
| GET | `/seo/projects/{project_id}/audits` | Proje audit geçmişi |

**Create Project Request:**
```json
{
  "name": "string (required)",
  "domain": "string (required)",
  "description": "string",
  "max_pages": 100,
  "max_depth": 10,
  "crawl_config": {}
}
```

**Create Project Response:**
```json
{
  "id": "seo-proj-abc123",
  "name": "My SEO Project",
  "domain": "example.com",
  "description": "",
  "max_pages": 100,
  "max_depth": 10,
  "crawl_config": {},
  "audit_history": [],
  "created_at": "2025-07-14T10:30:00",
  "updated_at": "2025-07-14T10:30:00"
}
```

### 4.2 Core Capabilities & Provider Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/seo/projects/capabilities` | Backend yeteneklerini getir |
| GET | `/seo/projects/providers/status` | Harici sağlayıcı durumları |

**Capabilities Response:**
```json
{
  "crawl": {
    "max_pages_per_job": 5000,
    "max_depth": 50,
    "max_concurrent_jobs": 10,
    "javascript_rendering": true,
    "screenshot_on_error": true,
    "custom_headers": true,
    "authentication": true,
    "robots_txt_respect": true,
    "sitemap_discovery": true
  },
  "analysis": {
    "technical_seo": true,
    "on_page_seo": true,
    "content_quality": true,
    "core_web_vitals": true,
    "mobile_usability": true,
    "structured_data": true,
    "international_seo": true,
    "ecommerce_seo": true,
    "accessibility_audit": true,
    "security_headers": true,
    "duplicate_content_detection": true,
    "canonical_analysis": true,
    "hreflang_validation": true,
    "redirect_chain_analysis": true
  },
  "scoring": {
    "page_level_scoring": true,
    "site_level_scoring": true,
    "custom_weights": true,
    "issue_thresholds": true
  },
  "exports": {
    "formats": ["html", "pdf", "markdown", "json", "csv"],
    "templates": ["executive", "technical", "content", "full"]
  },
  "integrations": {
    "google_search_console": false,
    "google_analytics": false,
    "ahrefs": false,
    "semrush": false,
    "screaming_frog": false
  },
  "ai_features": {
    "recommendations": true,
    "content_suggestions": true,
    "custom_models": false
  },
  "version": "1.0.0"
}
```

**Provider Status Response:**
```json
{
  "google_search_console": {
    "configured": false,
    "status": "not_configured",
    "last_sync": null,
    "quota_remaining": null
  },
  "google_analytics": {
    "configured": false,
    "status": "not_configured",
    "last_sync": null
  },
  "ahrefs": {
    "configured": false,
    "status": "not_configured",
    "last_sync": null
  },
  "semrush": {
    "configured": false,
    "status": "not_configured",
    "last_sync": null
  },
  "custom_api": {
    "configured": false,
    "status": "not_configured",
    "last_sync": null
  }
}
```

### 4.3 SEO Audit (Legacy - Geriye Dönük Uyumluluk)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/seo/audits` | Yeni SEO audit başlat |
| GET | `/seo/audits/{audit_id}` | Audit detayı getir |
| GET | `/seo/audits/{audit_id}/report` | Markdown rapor getir |
| GET | `/seo/audits/{audit_id}/export/markdown` | Markdown indir |
| GET | `/seo/audits/{audit_id}/export/json` | JSON indir |

**Audit Request:**
```json
{
  "url": "https://example.com",
  "country": "",
  "language": "",
  "business_description": "",
  "max_pages": 100,
  "include_ai_recommendations": false
}
```

**Audit Response (SeoAuditSummary):**
```json
{
  "success": true,
  "audit": {
    "id": "seo-abc123",
    "requested_url": "https://example.com",
    "normalized_url": "https://example.com/",
    "status": "completed",
    "created_at": "2025-07-14T10:30:00",
    "max_pages": 100,
    "crawled_pages": 50,
    "score": 72,
    "issues": [...],
    "recommendations": [...],
    "pages": [...],
    "site_signals": {...},
    "crawl_errors": [],
    "ai_recommendations": [],
    "metadata": {...}
  }
}
```

---

## 5. Frontend Types (vex-app/src/types/seo.ts)

Frontend tarafından kullanılan TypeScript arayüzler:

```typescript
// Audit stages
type SeoAuditStageKey =
  | "connection"
  | "robots_sitemap"
  | "crawl"
  | "technical_seo"
  | "on_page"
  | "keyword_content"
  | "report_completed";

type SeoAuditStatus =
  | "initial" | "loading" | "crawling" | "completed"
  | "url_error" | "unreachable" | "partial"
  | "backend_error" | "empty";

type SeoIssuePriority = "P0" | "P1" | "P2" | "P3" | string;

// Request
interface SeoAuditRequest {
  url: string;
  country: string;
  language: string;
  business_description: string;
  max_pages: number;
}

// Response types
interface SeoCrawlStats {
  discovered_urls?: number;
  crawled_urls?: number;
  skipped_urls?: number;
  blocked_urls?: number;
  errored_urls?: number;
}

interface SeoAuditStage {
  key?: SeoAuditStageKey | string;
  name?: string;
  status?: string;
  message?: string;
}

interface SeoAuditSummary {
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

interface SeoAuditPage {
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
  meta_description?: string;
  canonical?: string;
  robots?: string;
  [key: string]: unknown;
}

interface SeoAuditIssue {
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
  expected_impact?: string;
  [key: string]: unknown;
}

interface SeoKeywordRecommendation {
  keyword?: string;
  placement?: string;
  recommendation?: string;
  reason?: string;
  source?: "heuristic" | "ai" | string;
  page_url?: string;
  [key: string]: unknown;
}

interface SeoContentRecommendation {
  title?: string;
  page_url?: string;
  recommendation?: string;
  reason?: string;
  source?: "heuristic" | "ai" | string;
  [key: string]: unknown;
}

interface SeoImplementationPlanItem {
  priority?: SeoIssuePriority;
  title?: string;
  task?: string;
  impact?: string;
  effort?: string;
  steps?: string[];
  [key: string]: unknown;
}

interface SeoAuditResult {
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
```

---

## 6. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SEO_AUDIT_ERROR` | 400 | Audit request validation error |
| `SEO_PROJECT_NOT_FOUND` | 404 | Project not found |
| `SEO_AUDIT_NOT_FOUND` | 404 | Audit not found |
| `SEO_NO_URL_PROVIDED` | 400 | URL required |
| `SEO_INVALID_URL` | 400 | URL format invalid |
| `SEO_SSRF_BLOCKED` | 400 | SSRF protection blocked request |
| `SEO_MAX_PAGES_EXCEEDED` | 400 | Max pages limit exceeded |
| `SEO_INVALID_CONFIG` | 400 | Invalid crawl configuration |
| `SEO_PROVIDER_NOT_CONFIGURED` | 400 | External provider not configured |
| `SEO_INTERNAL_ERROR` | 500 | Internal server error |

---

## 7. Frontend Components

### 6.1 Shared Components (vex-app/src/components/seo/)

| Component | Props | Description |
|-----------|-------|-------------|
| `IssueBadge` | `severity`, `category`, `label`, `size` | SEO issue severity badge |
| `ScoreDisplay` | `score`, `size`, `showLabel` | Numeric score with color coding |
| `ScoreRing` | `score`, `size`, `strokeWidth` | Circular progress ring |
| `PageTypeBadge` | `pageType`, `size` | Page type label |
| `SeverityIndicator` | `severity`, `showLabel` | Colored severity indicator |
| `CategoryBadge` | `category` | Issue category label |
| `MetricItem` | `label`, `value`, `trend`, `tooltip` | Key-value metric display |
| `IssueItem` | `issue`, `onClick` | Full issue display card |
| `SeoSummaryCard` | `title`, `value`, `subtitle`, `trend`, `icon` | Dashboard summary card |

### 6.2 Project Selector (SeoProjectSelector)

```tsx
<SeoProjectSelector
  value={selectedProjectId}
  onChange={handleProjectChange}
  placeholder="SEO projesi seçin..."
  includeEmpty={true}
  emptyLabel="Tüm projeler"
  showDetails={true}
  onCreateNew={handleCreateNewProject}
/>
```

### 6.3 Provider Status (ProviderStatusField)

```tsx
<ProviderStatusField
  compact={false}
  onRefresh={fetchProviderStatus}
/>

// Compact version for headers
<CompactProviderStatus />
```

### 6.4 Project List (SeoProjectList)

```tsx
<SeoProjectList
  selectedId={selectedProjectId}
  onSelect={handleProjectSelect}
  onEdit={handleEditProject}
  onDelete={handleDeleteProject}
  onCreateNew={handleCreateNewProject}
/>
```

---

## 8. Backend Storage

### 8.1 SEO Projects (`data/seo_projects.json`)

```json
[
  {
    "id": "seo-proj-abc123",
    "name": "My Project",
    "domain": "example.com",
    "description": "E-commerce site audit",
    "max_pages": 100,
    "max_depth": 10,
    "crawl_config": {},
    "audit_history": [
      {
        "audit_id": "seo-def456",
        "score": 72,
        "crawled_pages": 50,
        "completed_at": "2025-07-14T10:30:00"
      }
    ],
    "active_audit_id": "seo-def456",
    "last_audit_at": "2025-07-14T10:30:00",
    "last_score": 72,
    "created_at": "2025-07-14T09:00:00",
    "updated_at": "2025-07-14T10:30:00"
  }
]
```

### 8.2 SEO Audits (`data/seo_audits.json`)

Legacy audit storage (geriye dönük uyumluluk için):
```json
[
  {
    "id": "seo-abc123",
    "requested_url": "https://example.com",
    "normalized_url": "https://example.com/",
    "status": "completed",
    "created_at": "2025-07-14T10:30:00",
    "max_pages": 100,
    "crawled_pages": 50,
    "score": 72,
    "issues": [...],
    "recommendations": [...],
    "pages": [...],
    "site_signals": {...},
    "crawl_errors": [],
    "ai_recommendations": [],
    "metadata": {...}
  }
]
```

---

## 9. Validation Rules

### 9.1 CrawlConfig Validation
- `start_url`: Must be valid HTTP/HTTPS URL
- `max_pages`: 1-5000
- `max_depth`: 0-50
- `max_redirects`: 0-50
- `request_timeout`: 5-120 seconds
- `max_concurrent`: 1-50
- `delay_between_requests`: 0-10 seconds
- `viewport_width`: 320-3840
- `viewport_height`: 240-2160
- `max_content_length`: 100000-100000000 bytes
- `max_ai_tokens`: 500-8000

### 9.2 Project Validation
- `name`: Required, 1-100 chars
- `domain`: Required, valid domain format
- `description`: Optional, max 500 chars
- `max_pages`: 1-5000
- `max_depth`: 0-50

---

## 10. Frontend Service API

### vex-app/src/services/seoProjectService.ts

```typescript
class SeoProjectService {
  // Project CRUD
  static async createProject(data: CreateProjectRequest): Promise<SeoProject>
  static async listProjects(): Promise<SeoProject[]>
  static async getProject(id: string): Promise<SeoProject | null>
  static async updateProject(id: string, updates: Partial<SeoProject>): Promise<SeoProject | null>
  static async deleteProject(id: string): Promise<boolean>

  // Audit history
  static async createAudit(projectId: string, request: CrawlJobRequest): Promise<{audit_id: string}>

  // Capabilities
  static async getCapabilities(): Promise<BackendCapabilities>
  static async getProviderStatus(): Promise<ProviderStatus>
}
```

### vex-app/src/services/seo.ts (Legacy)

```typescript
export async function createSeoAudit(request: SeoAuditRequest): Promise<SeoAuditResult>
export async function downloadSeoAuditExport(auditId: string, format: "markdown" | "json"): Promise<void>
```

---

## 11. Migration Notes (Legacy → Core)

### Breaking Changes
- `SeoAuditRequest` URL field was `HttpUrl` type, now `string`
- `SeoIssue.severity` was `Literal["P0","P1","P2","P3"]`, now `IssueSeverity` enum
- `SeoIssue.page_type` was limited union, now full `PageType` enum
- Added `scope` field to issues (page/site/crawl/pattern)

### Compatibility Layer
Frontend `normalizeBackendAudit()` fonksiyonu backend response'u frontend types'a dönüştürür:
- `severity` → `priority`
- `message` → `name` + `title`
- `recommendation` → `recommended` + `how_to_fix`
- `current_value` → `current` + `current_value`
- `scope` → `category` mapping

### Deprecated Fields
- `SeoPageAnalysis.score_reasons` → use detailed scoring breakdown
- `SeoSiteSignals.score_reasons` → use issue-based scoring
- Legacy `SeoAudit.status` values → unified with new status enum

---

## 12. Testing Contract

### 12.1 Backend Tests Required
- [ ] Project CRUD operations
- [ ] Capabilities endpoint returns correct structure
- [ ] Provider status endpoint returns correct structure
- [ ] Project audit creation links to project history
- [ ] CrawlConfig validation boundaries
- [ ] Enum serialization/deserialization

### 12.2 Frontend Tests Required
- [ ] Project selector loads and displays projects
- [ ] Provider status shows correct states
- [ ] Issue badge colors match severity
- [ ] Score display colors match thresholds
- [ ] Type-safe API responses

### 12.3 Integration Tests
- [ ] Create project → Start audit → Verify history
- [ ] Update project config → Verify crawl uses new settings
- [ ] Delete project → Verify cascade cleanup

---

## 13. Versioning Strategy

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-07-14 | Initial core contract |

**Semantic Versioning:**
- MAJOR: Breaking API changes
- MINOR: New endpoints, new enum values, new optional fields
- PATCH: Bug fixes, documentation updates

---

## 14. Security Considerations

1. **SSRF Protection**: All URLs validated through `SeoCrawler.validate_public_url()`
2. **Rate Limiting**: Configured via `SystemSettings.rate_limit_requests_per_minute`
3. **Input Validation**: Pydantic v2 validation on all request models
4. **No Secrets in Logs**: Structured logging excludes sensitive data
5. **File Permissions**: Data directory restricted to application user

---

## 15. Performance Baselines

| Operation | Target |
|-----------|--------|
| List projects | < 50ms |
| Get project | < 30ms |
| Create project | < 100ms |
| Get capabilities | < 20ms |
| Get provider status | < 20ms |
| Start audit (crawl) | < 5s for 10 pages |

---

*Generated as part of VEX-SEO-CORE-001 sprint*