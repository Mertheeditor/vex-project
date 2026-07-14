from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator


class IssueSeverity(str, Enum):
    """SEO issue severity levels."""

    P0 = "P0"  # Critical - blocks indexing/ranking
    P1 = "P1"  # High - significantly impacts SEO
    P2 = "P2"  # Medium - moderate SEO impact
    P3 = "P3"  # Low - minor SEO improvement


class IssueCategory(str, Enum):
    """Categories of SEO issues."""

    TECHNICAL = "technical"  # Crawling, indexing, rendering
    CONTENT = "content"  # Content quality, relevance, structure
    ON_PAGE = "on_page"  # Title, meta, headings, structure
    TECHNICAL_SEO = "technical_seo"  # Robots, sitemap, canonical, hreflang
    PERFORMANCE = "performance"  # Speed, Core Web Vitals
    MOBILE = "mobile"  # Mobile usability, viewport
    STRUCTURED_DATA = "structured_data"  # Schema.org, JSON-LD
    INTERNATIONAL = "international"  # Hreflang, geo-targeting
    ECOMMERCE = "ecommerce"  # Product schema, inventory, reviews
    SECURITY = "security"  # HTTPS, mixed content, security headers
    ACCESSIBILITY = "accessibility"  # A11y issues affecting SEO
    LINKS = "links"  # Internal/external links, anchors, redirects
    IMAGES = "images"  # Alt text, sizing, formats, lazy-loading


class PageType(str, Enum):
    """Page type classification."""

    HOMEPAGE = "homepage"
    COLLECTION = "collection"
    PRODUCT = "product"
    BLOG_ARTICLE = "blog_article"
    CONTENT_PAGE = "content_page"
    CART = "cart"
    ACCOUNT = "account"
    POLICY = "policy"
    SEARCH = "search"
    UNKNOWN = "unknown"
    CATEGORY = "category"
    TAG = "tag"
    AUTHOR = "author"
    ARCHIVE = "archive"
    LANDING = "landing"
    THANK_YOU = "thank_you"
    PAGE_404 = "404"
    PAGE_500 = "500"


class CrawlStatus(str, Enum):
    """Crawl status for a URL."""

    PENDING = "pending"
    QUEUED = "queued"
    CRAWLING = "crawling"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    REDIRECTED = "redirected"
    TIMEOUT = "timeout"
    ERROR = "error"


class IndexabilityStatus(str, Enum):
    """Indexability status of a page."""

    INDEXABLE = "indexable"
    NOINDEX = "noindex"
    CANONICALIZED = "canonicalized"
    REDIRECTED = "redirected"
    BLOCKED_ROBOTS = "blocked_robots"
    BLOCKED_ROBOTS_TXT = "blocked_robots_txt"
    NOINDEX_NOFOLLOW = "noindex_nofollow"
    CANONICAL_MISMATCH = "canonical_mismatch"
    UNKNOWN = "unknown"


class RedirectType(str, Enum):
    """HTTP redirect types."""

    REDIRECT_301 = "301"
    REDIRECT_302 = "302"
    REDIRECT_303 = "303"
    REDIRECT_307 = "307"
    REDIRECT_308 = "308"
    META_REFRESH = "meta_refresh"
    JS_REDIRECT = "js_redirect"
    UNKNOWN = "unknown"


class StructuredDataType(str, Enum):
    """Schema.org structured data types."""

    WEBSITE = "WebSite"
    ORGANIZATION = "Organization"
    LOCAL_BUSINESS = "LocalBusiness"
    PRODUCT = "Product"
    PRODUCT_GROUP = "ProductGroup"
    BLOG_POSTING = "BlogPosting"
    ARTICLE = "Article"
    NEWS_ARTICLE = "NewsArticle"
    BREADCRUMB_LIST = "BreadcrumbList"
    ITEM_LIST = "ItemList"
    FAQ_PAGE = "FAQPage"
    HOW_TO = "HowTo"
    VIDEO_OBJECT = "VideoObject"
    IMAGE_OBJECT = "ImageObject"
    PERSON = "Person"
    BRAND = "Brand"
    OFFER = "Offer"
    AGGREGATE_RATING = "AggregateRating"
    REVIEW = "Review"
    WEB_PAGE = "WebPage"
    COLLECTION_PAGE = "CollectionPage"
    PRODUCT_PAGE = "ProductPage"
    BLOG = "Blog"
    SITE_NAVIGATION_ELEMENT = "SiteNavigationElement"
    TABLE = "Table"
    DATASET = "DataSet"
    SOFTWARE_APPLICATION = "SoftwareApplication"
    MOBILE_APPLICATION = "MobileApplication"
    WEB_APPLICATION = "WebApplication"
    SERVICE = "Service"
    EVENT = "Event"
    COURSE = "Course"
    JOB_POSTING = "JobPosting"
    FAQ = "FAQ"
    HOW_TO_SECTION = "HowToSection"
    HOW_TO_STEP = "HowToStep"
    UNKNOWN = "unknown"


class CoreWebVitalsMetric(str, Enum):
    """Core Web Vitals metrics."""

    LCP = "LCP"  # Largest Contentful Paint
    FID = "FID"  # First Input Delay
    CLS = "CLS"  # Cumulative Layout Shift
    INP = "INP"  # Interaction to Next Paint
    FCP = "FCP"  # First Contentful Paint
    TTFB = "TTFB"  # Time to First Byte


class CWVRating(str, Enum):
    """Core Web Vitals rating thresholds."""

    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class HttpStatusCategory(str, Enum):
    """HTTP status code categories."""

    INFORMATIONAL = "1xx"
    SUCCESS = "2xx"
    REDIRECTION = "3xx"
    CLIENT_ERROR = "4xx"
    SERVER_ERROR = "5xx"


class CrawlConfig(BaseModel):
    """Configuration for a crawl job."""

    start_url: HttpUrl
    max_pages: int = Field(default=100, ge=1, le=5000)
    max_depth: int = Field(default=10, ge=0, le=50)
    follow_redirects: bool = True
    max_redirects: int = Field(default=10, ge=0, le=50)
    respect_robots_txt: bool = True
    respect_nofollow: bool = True
    respect_noindex: bool = True
    crawl_subdomains: bool = False
    crawl_external_links: bool = False
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    blocked_paths: list[str] = Field(default_factory=list)
    user_agent: str = "VexBot/1.0 (+https://vex.dev/bot)"
    request_timeout: int = Field(default=30, ge=5, le=120)
    max_concurrent: int = Field(default=5, ge=1, le=50)
    delay_between_requests: float = Field(default=0.5, ge=0, le=10)
    render_javascript: bool = False
    wait_for_network_idle: bool = True
    wait_for_selector: str | None = None
    screenshot_on_error: bool = False
    custom_headers: dict[str, str] = Field(default_factory=dict)
    cookies: dict[str, str] = Field(default_factory=dict)
    auth: dict[str, str] | None = None
    country: str = ""
    language: str = ""
    viewport_width: int = Field(default=1920, ge=320, le=3840)
    viewport_height: int = Field(default=1080, ge=240, le=2160)
    business_description: str = ""
    include_ai_recommendations: bool = False
    ai_model: str = "gpt-4o-mini"
    max_ai_tokens: int = Field(default=2000, ge=500, le=8000)
    prioritize_urls: list[str] = Field(default_factory=list)
    max_content_length: int = Field(default=10_000_000, ge=100_000, le=100_000_000)
    extract_structured_data: bool = True
    extract_performance_metrics: bool = True
    extract_accessibility: bool = True
    extract_security_headers: bool = True
    follow_canonical: bool = True
    follow_pagination: bool = True
    max_pagination_pages: int = Field(default=100, ge=0, le=1000)

    @field_validator("start_url")
    @classmethod
    def validate_start_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("Only http and https URLs are supported")
        return value

    @field_validator("allowed_domains", "blocked_domains", mode="before")
    @classmethod
    def normalize_domains(cls, value: list[str]) -> list[str]:
        return [d.lower().strip() for d in value if d.strip()]

    @property
    def start_domain(self) -> str:
        return urlparse(str(self.start_url)).netloc.lower()


class CrawlUrlResult(BaseModel):
    """Result of crawling a single URL."""

    url: str
    normalized_url: str
    final_url: str
    status: CrawlStatus
    status_code: int | None = None
    status_category: HttpStatusCategory | None = None
    redirect_chain: list[str] = Field(default_factory=list)
    redirect_type: RedirectType | None = None
    content_type: str = ""
    content_length: int = 0
    load_time_ms: int = 0
    ttfb_ms: int = 0
    dom_content_loaded_ms: int = 0
    depth: int = 0
    page_type: PageType = PageType.UNKNOWN
    indexability: IndexabilityStatus = IndexabilityStatus.UNKNOWN
    canonical_url: str = ""
    canonical_status: Literal["valid", "self", "missing", "mismatch", "redirect", "blocked", "multiple"] = "missing"
    robots_meta: str = ""
    x_robots_tag: str = ""
    hreflang_tags: list[dict[str, str]] = Field(default_factory=list)
    title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    h1_tags: list[str] = Field(default_factory=list)
    h2_tags: list[str] = Field(default_factory=list)
    h3_tags: list[str] = Field(default_factory=list)
    h4_tags: list[str] = Field(default_factory=list)
    h5_tags: list[str] = Field(default_factory=list)
    h6_tags: list[str] = Field(default_factory=list)
    word_count: int = 0
    text_html_ratio: float = 0.0
    internal_links: list[LinkInfo] = Field(default_factory=list)
    external_links: list[LinkInfo] = Field(default_factory=list)
    images: list[ImageInfo] = Field(default_factory=list)
    structured_data: list[StructuredDataItem] = Field(default_factory=list)
    open_graph: dict[str, str] = Field(default_factory=dict)
    twitter_card: dict[str, str] = Field(default_factory=dict)
    json_ld: list[dict[str, Any]] = Field(default_factory=list)
    microdata: list[dict[str, Any]] = Field(default_factory=list)
    rdfa: list[dict[str, Any]] = Field(default_factory=list)
    viewport: str = ""
    charset: str = ""
    language: str = ""
    hreflang: str = ""
    response_headers: dict[str, str] = Field(default_factory=dict)
    security_headers: SecurityHeaders = Field(default_factory=lambda: SecurityHeaders())
    performance_metrics: PerformanceMetrics | None = None
    accessibility_issues: list[AccessibilityIssue] = Field(default_factory=list)
    seo_issues: list[SeoIssueCore] = Field(default_factory=list)
    content_hash: str = ""
    simhash: str = ""
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None
    error_type: str | None = None
    skipped_reason: str | None = None


class LinkInfo(BaseModel):
    """Link information extracted from a page."""

    url: str
    normalized_url: str
    anchor_text: str = ""
    title_attribute: str = ""
    rel_attributes: list[str] = Field(default_factory=list)
    is_internal: bool = True
    is_nofollow: bool = False
    is_sponsored: bool = False
    is_ugc: bool = False
    is_external: bool = False
    link_type: Literal["nav", "footer", "sidebar", "content", "breadcrumb", "pagination", "other"] = "other"
    status_code: int | None = None
    redirect_chain: list[str] = Field(default_factory=list)
    is_broken: bool = False
    is_redirect: bool = False


class ImageInfo(BaseModel):
    """Image information extracted from a page."""

    src: str
    alt: str = ""
    title: str = ""
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    format: str = ""
    is_lazy_loaded: bool = False
    has_srcset: bool = False
    has_sizes: bool = False
    is_webp: bool = False
    is_avif: bool = False
    missing_alt: bool = False
    empty_alt: bool = False
    alt_too_long: bool = False
    alt_keyword_stuffing: bool = False


class StructuredDataItem(BaseModel):
    """Structured data item extracted from a page."""

    type: StructuredDataType = StructuredDataType.UNKNOWN
    raw_type: str = ""
    format: Literal["json-ld", "microdata", "rdfa"] = "json-ld"
    data: dict[str, Any] = Field(default_factory=dict)
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)
    namespace: str = "schema.org"


class SecurityHeaders(BaseModel):
    """Security headers analysis."""

    strict_transport_security: str = ""
    content_security_policy: str = ""
    x_frame_options: str = ""
    x_content_type_options: str = ""
    referrer_policy: str = ""
    permissions_policy: str = ""
    cross_origin_opener_policy: str = ""
    cross_origin_embedder_policy: str = ""
    cross_origin_resource_policy: str = ""
    has_hsts: bool = False
    has_csp: bool = False
    hsts_max_age: int = 0
    hsts_includes_subdomains: bool = False
    hsts_preload: bool = False
    csp_report_only: bool = False
    issues: list[str] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    """Core Web Vitals and performance metrics."""

    lcp_ms: int | None = None
    fid_ms: int | None = None
    inp_ms: int | None = None
    cls_score: float | None = None
    fcp_ms: int | None = None
    ttfb_ms: int | None = None
    dom_content_loaded_ms: int | None = None
    load_event_ms: int | None = None
    total_blocking_time_ms: int | None = None
    speed_index: float | None = None
    lcp_rating: CWVRating | None = None
    fid_rating: CWVRating | None = None
    inp_rating: CWVRating | None = None
    cls_rating: CWVRating | None = None
    overall_rating: CWVRating | None = None
    lab_data: bool = True
    field_data: bool = False
    measured_at: datetime = Field(default_factory=datetime.utcnow)


class AccessibilityIssue(BaseModel):
    """Accessibility issue that impacts SEO."""

    type: str
    severity: IssueSeverity
    message: str
    element: str = ""
    selector: str = ""
    wcag_criterion: str = ""
    impact: Literal["critical", "serious", "moderate", "minor"] = "moderate"


class SeoIssueCore(BaseModel):
    """Core SEO issue model with full context."""

    id: str = Field(default_factory=lambda: f"seo_{int(datetime.utcnow().timestamp() * 1000)}")
    severity: IssueSeverity = IssueSeverity.P2
    category: IssueCategory = IssueCategory.TECHNICAL
    code: str
    message: str
    description: str = ""
    recommendation: str = ""
    url: str = ""
    page_type: PageType = PageType.UNKNOWN
    scope: Literal["page", "site", "crawl", "pattern"] = "page"
    affected_urls: list[str] = Field(default_factory=list)
    current_value: str = ""
    expected_value: str = ""
    platform_hint: str = "generic"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    impact_score: int = Field(default=5, ge=1, le=10)
    effort_score: int = Field(default=5, ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    is_auto_fixable: bool = False
    auto_fix_suggestion: str = ""


class SeoRecommendationCore(BaseModel):
    """Comprehensive SEO recommendation."""

    id: str = Field(default_factory=lambda: f"rec_{int(datetime.utcnow().timestamp() * 1000)}")
    priority: IssueSeverity = IssueSeverity.P2
    category: IssueCategory = IssueCategory.TECHNICAL
    title: str
    description: str
    detailed_explanation: str = ""
    impact: Literal["critical", "high", "medium", "low"] = "medium"
    effort: Literal["low", "medium", "high", "very_high"] = "medium"
    urls_affected: list[str] = Field(default_factory=list)
    page_types_affected: list[PageType] = Field(default_factory=list)
    platform_hint: str = "generic"
    implementation_steps: list[str] = Field(default_factory=list)
    code_examples: dict[str, str] = Field(default_factory=dict)
    tools_to_verify: list[str] = Field(default_factory=list)
    related_issues: list[str] = Field(default_factory=list)
    estimated_impact_score: int = Field(default=5, ge=1, le=10)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    ai_generated: bool = False
    ai_model: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PageScoreBreakdown(BaseModel):
    """Detailed page SEO score breakdown."""

    overall: int = Field(ge=0, le=100)
    technical: int = Field(ge=0, le=100)
    content: int = Field(ge=0, le=100)
    on_page: int = Field(ge=0, le=100)
    performance: int = Field(ge=0, le=100)
    mobile: int = Field(ge=0, le=100)
    structured_data: int = Field(ge=0, le=100)
    links: int = Field(ge=0, le=100)
    images: int = Field(ge=0, le=100)
    security: int = Field(ge=0, le=100)
    accessibility: int = Field(ge=0, le=100)
    factors: list[str] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)
    bonuses: list[str] = Field(default_factory=list)


class SiteScoreBreakdown(BaseModel):
    """Site-wide SEO score breakdown."""

    overall: int = Field(ge=0, le=100)
    technical_health: int = Field(ge=0, le=100)
    content_quality: int = Field(ge=0, le=100)
    on_page_optimization: int = Field(ge=0, le=100)
    site_architecture: int = Field(ge=0, le=100)
    crawlability: int = Field(ge=0, le=100)
    indexability: int = Field(ge=0, le=100)
    performance: int = Field(ge=0, le=100)
    mobile_usability: int = Field(ge=0, le=100)
    structured_data_coverage: int = Field(ge=0, le=100)
    internal_linking: int = Field(ge=0, le=100)
    international_seo: int = Field(ge=0, le=100)
    security: int = Field(ge=0, le=100)
    factors: list[str] = Field(default_factory=list)
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0


class CrawlSummary(BaseModel):
    """Summary of a completed crawl."""

    crawl_id: str
    config: CrawlConfig
    status: Literal["running", "completed", "failed", "cancelled", "paused"]
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float = 0
    urls_discovered: int = 0
    urls_queued: int = 0
    urls_crawled: int = 0
    urls_failed: int = 0
    urls_skipped: int = 0
    urls_blocked: int = 0
    urls_redirected: int = 0
    total_bytes_downloaded: int = 0
    avg_response_time_ms: float = 0
    pages_per_second: float = 0
    errors_by_type: dict[str, int] = Field(default_factory=dict)
    status_codes: dict[int, int] = Field(default_factory=dict)
    content_types: dict[str, int] = Field(default_factory=dict)
    page_types: dict[PageType, int] = Field(default_factory=dict)
    depth_distribution: dict[int, int] = Field(default_factory=dict)
    crawl_errors: list[CrawlError] = Field(default_factory=list)
    robots_txt: RobotsTxtInfo | None = None
    sitemaps: list[SitemapInfo] = Field(default_factory=list)
    issues_summary: dict[IssueSeverity, int] = Field(default_factory=dict)
    issues_by_category: dict[IssueCategory, int] = Field(default_factory=dict)
    top_issues: list[SeoIssueCore] = Field(default_factory=list)
    top_recommendations: list[SeoRecommendationCore] = Field(default_factory=list)


class CrawlError(BaseModel):
    """Crawl error detail."""

    url: str
    error_type: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = 0
    status_code: int | None = None


class RobotsTxtInfo(BaseModel):
    """Robots.txt analysis."""

    url: str
    exists: bool = False
    content: str = ""
    size_bytes: int = 0
    parse_errors: list[str] = Field(default_factory=list)
    user_agents: dict[str, RobotsUserAgent] = Field(default_factory=dict)
    sitemaps: list[str] = Field(default_factory=list)
    crawl_delay: float | None = None
    host: str | None = None
    disallowed_paths: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)


class RobotsUserAgent(BaseModel):
    """Robots.txt user agent rules."""

    user_agent: str
    disallow: list[str] = Field(default_factory=list)
    allow: list[str] = Field(default_factory=list)
    crawl_delay: float | None = None


class SitemapInfo(BaseModel):
    """Sitemap information."""

    url: str
    type: Literal["xml", "index", "text", "rss", "atom", "unknown"] = "unknown"
    status_code: int | None = None
    last_modified: datetime | None = None
    size_bytes: int = 0
    url_count: int = 0
    parsed_urls: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    is_valid: bool = True
    has_lastmod: bool = False
    has_changefreq: bool = False
    has_priority: bool = False
    compression: str = ""


class SeoAuditConfig(BaseModel):
    """Configuration for SEO audit behavior."""

    scoring_weights: ScoringWeights = Field(default_factory=lambda: ScoringWeights())
    issue_thresholds: IssueThresholds = Field(default_factory=lambda: IssueThresholds())
    enable_ai_recommendations: bool = False
    ai_model: str = "gpt-4o-mini"
    max_ai_recommendations: int = 10
    include_performance_audit: bool = True
    include_accessibility_audit: bool = True
    include_security_audit: bool = True
    include_international_audit: bool = True
    include_ecommerce_audit: bool = False
    custom_rules: list[CustomRule] = Field(default_factory=list)
    platform_hints: list[str] = Field(default_factory=list)
    ignore_patterns: list[str] = Field(default_factory=list)


class ScoringWeights(BaseModel):
    """SEO scoring weights for different categories."""

    technical: float = 0.20
    content: float = 0.20
    on_page: float = 0.15
    performance: float = 0.15
    mobile: float = 0.10
    structured_data: float = 0.05
    links: float = 0.05
    images: float = 0.03
    security: float = 0.04
    accessibility: float = 0.03

    @field_validator("*", mode="before")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Weight must be between 0 and 1")
        return v


class IssueThresholds(BaseModel):
    """Thresholds for issue detection."""

    min_title_length: int = 30
    max_title_length: int = 60
    min_meta_desc_length: int = 70
    max_meta_desc_length: int = 160
    min_h1_count: int = 1
    max_h1_count: int = 1
    min_word_count: int = 300
    max_load_time_ms: int = 3000
    max_ttfb_ms: int = 600
    max_cls: float = 0.1
    min_lcp_ms: int = 2500
    max_fid_ms: int = 100
    max_inp_ms: int = 200
    max_redirect_chain: int = 3
    max_page_depth: int = 5
    min_internal_links: int = 3
    max_external_links_ratio: float = 0.3
    min_image_alt_coverage: float = 0.9
    duplicate_content_threshold: float = 0.85


class CustomRule(BaseModel):
    """Custom SEO rule definition."""

    id: str
    name: str
    description: str
    severity: IssueSeverity = IssueSeverity.P2
    category: IssueCategory = IssueCategory.TECHNICAL
    enabled: bool = True
    applies_to: list[PageType] = Field(default_factory=list)
    selector: str = ""
    attribute: str = ""
    expected_value: str | None = None
    pattern: str | None = None
    custom_check: str = ""
    message_template: str = ""
    recommendation_template: str = ""


class PlatformProfile(BaseModel):
    """Platform-specific SEO profile and hints."""

    platform: str
    confidence: float = 0.0
    version: str = ""
    indicators: dict[str, Any] = Field(default_factory=dict)
    known_issues: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    platform_specific_selectors: dict[str, str] = Field(default_factory=dict)
    schema_requirements: list[StructuredDataType] = Field(default_factory=list)
    performance_benchmarks: dict[str, float] = Field(default_factory=dict)


class AuditComparison(BaseModel):
    """Comparison between two audits."""

    baseline_audit_id: str
    comparison_audit_id: str
    baseline_date: datetime
    comparison_date: datetime
    score_change: int
    score_change_pct: float
    issues_resolved: int
    issues_new: int
    issues_worsened: int
    issues_improved: int
    pages_improved: int
    pages_declined: int
    top_improvements: list[str] = Field(default_factory=list)
    top_regressions: list[str] = Field(default_factory=list)
    category_changes: dict[IssueCategory, int] = Field(default_factory=dict)


class KeywordOpportunity(BaseModel):
    """Keyword opportunity identified during audit."""

    keyword: str
    volume: int = 0
    difficulty: float = 0.0
    cpc: float = 0.0
    intent: Literal["informational", "navigational", "commercial", "transactional"] = "informational"
    current_position: int | None = None
    target_url: str = ""
    competitor_urls: list[str] = Field(default_factory=list)
    difficulty_score: int = Field(ge=0, le=100)
    opportunity_score: int = Field(ge=0, le=100)
    suggested_content_type: PageType = PageType.CONTENT_PAGE
    related_keywords: list[str] = Field(default_factory=list)
    sero_features: list[str] = Field(default_factory=list)


class CompetitorGap(BaseModel):
    """Competitor content gap analysis."""

    competitor_domain: str
    competitor_url: str
    keywords_missing: list[KeywordOpportunity] = Field(default_factory=list)
    content_gaps: list[str] = Field(default_factory=list)
    structural_advantages: list[str] = Field(default_factory=list)
    technical_advantages: list[str] = Field(default_factory=list)
    backlink_gap: int = 0
    authority_gap: float = 0.0


class InternationalSeoSignal(BaseModel):
    """International SEO signals for a page."""

    url: str
    hreflang: str = ""
    hreflang_tags: list[dict[str, str]] = Field(default_factory=list)
    x_default: bool = False
    canonical_matches_hreflang: bool = True
    language: str = ""
    region: str = ""
    currency: str = ""
    content_language: str = ""
    html_lang: str = ""
    issues: list[SeoIssueCore] = Field(default_factory=list)


class EcommerceSeoSignal(BaseModel):
    """E-commerce specific SEO signals."""

    url: str
    product_schema: StructuredDataItem | None = None
    price: float | None = None
    currency: str = ""
    availability: str = ""
    sku: str = ""
    gtin: str = ""
    mpn: str = ""
    brand: str = ""
    category: str = ""
    review_count: int = 0
    aggregate_rating: float = 0.0
    has_offers: bool = False
    has_reviews: bool = False
    has_breadcrumbs: bool = False
    has_faq: bool = False
    inventory_status: str = ""
    shipping_info: dict[str, Any] = Field(default_factory=dict)
    return_policy: str = ""
    issues: list[SeoIssueCore] = Field(default_factory=list)


class ContentQualitySignal(BaseModel):
    """Content quality signals."""

    url: str
    word_count: int = 0
    readability_score: float | None = None
    reading_time_minutes: int = 0
    heading_structure_score: int = 0
    keyword_density: dict[str, float] = Field(default_factory=dict)
    topic_coverage_score: float = 0.0
    content_depth_score: float = 0.0
    uniqueness_score: float = 0.0
    freshness_score: float = 0.0
    e_e_a_t_signals: EEATSignals = Field(default_factory=lambda: EEATSignals())
    thin_content: bool = False
    duplicate_content: bool = False
    duplicate_of: str = ""


class EEATSignals(BaseModel):
    """E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) signals."""

    has_author_bio: bool = False
    author_credentials: str = ""
    author_profile_url: str = ""
    has_author_schema: bool = False
    publication_date: datetime | None = None
    last_modified_date: datetime | None = None
    has_editorial_policy: bool = False
    has_contact_info: bool = False
    has_about_page: bool = False
    has_privacy_policy: bool = False
    has_terms_of_service: bool = False
    citations_count: int = 0
    external_references: list[str] = Field(default_factory=list)
    expertise_signals: list[str] = Field(default_factory=list)
    experience_signals: list[str] = Field(default_factory=list)
    authority_signals: list[str] = Field(default_factory=list)
    trustworthiness_signals: list[str] = Field(default_factory=list)


class TechnicalSeoSnapshot(BaseModel):
    """Complete technical SEO snapshot for a URL."""

    url: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    http_status: int = 200
    redirect_chain: list[str] = Field(default_factory=list)
    final_url: str = ""
    indexability: IndexabilityStatus = IndexabilityStatus.UNKNOWN
    canonical_url: str = ""
    canonical_status: str = "missing"
    robots_meta: str = ""
    x_robots_tag: str = ""
    robots_txt_allows: bool = True
    sitemap_included: bool = False
    hreflang_valid: bool = True
    load_time_ms: int = 0
    page_size_bytes: int = 0
    text_html_ratio: float = 0.0
    compression: str = ""
    cache_headers: dict[str, str] = Field(default_factory=dict)
    security_headers: SecurityHeaders = Field(default_factory=lambda: SecurityHeaders())
    core_web_vitals: PerformanceMetrics | None = None
    mobile_friendly: bool = True
    viewport_configured: bool = True
    ssl_valid: bool = True
    mixed_content: bool = False
    issues: list[SeoIssueCore] = Field(default_factory=list)


class CrawlJobRequest(BaseModel):
    """Request to start a crawl job."""

    config: CrawlConfig
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    callback_url: HttpUrl | None = None
    webhook_events: list[Literal["started", "progress", "completed", "failed", "paused"]] = Field(default_factory=list)


class CrawlJobResponse(BaseModel):
    """Response for crawl job creation."""

    job_id: str
    status: Literal["queued", "started", "running", "completed", "failed", "cancelled", "paused"]
    message: str = ""
    estimated_duration_seconds: int | None = None
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    config: CrawlConfig


class CrawlProgressUpdate(BaseModel):
    """Real-time crawl progress update."""

    job_id: str
    status: Literal["running", "paused", "completed", "failed"]
    progress_pct: float = Field(ge=0, le=100)
    urls_queued: int = 0
    urls_crawled: int = 0
    urls_failed: int = 0
    urls_skipped: int = 0
    current_url: str = ""
    current_depth: int = 0
    elapsed_seconds: float = 0
    estimated_remaining_seconds: float | None = None
    pages_per_second: float = 0
    errors_per_second: float = 0
    recent_errors: list[CrawlError] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SeoReportRequest(BaseModel):
    """Request for generating an SEO report."""

    audit_id: str
    format: Literal["html", "pdf", "markdown", "json", "csv"] = "html"
    template: Literal["executive", "technical", "content", "full", "custom"] = "full"
    include_sections: list[str] = Field(default_factory=list)
    exclude_sections: list[str] = Field(default_factory=list)
    language: str = "en"
    branding: dict[str, Any] = Field(default_factory=dict)
    custom_css: str = ""
    include_recommendations: bool = True
    include_technical_details: bool = True
    include_screenshots: bool = False
    max_issues_per_category: int = 50
    group_by: Literal["severity", "category", "page", "url"] = "category"


class SeoReportResponse(BaseModel):
    """SEO report generation response."""

    report_id: str
    audit_id: str
    format: str
    status: Literal["generating", "completed", "failed"]
    download_url: str | None = None
    expires_at: datetime | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    file_size_bytes: int | None = None
    error: str | None = None


class AuditListParams(BaseModel):
    """Parameters for listing audits."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: list[Literal["completed", "failed", "running", "pending"]] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    max_score: int | None = Field(default=None, ge=0, le=100)
    search: str | None = None
    tags: list[str] | None = None
    sort_by: Literal["created_at", "score", "crawled_pages", "status"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class AuditListResponse(BaseModel):
    """Paginated audit list response."""

    audits: list[SeoAuditSummary] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class BulkAuditRequest(BaseModel):
    """Request for bulk audit operations."""

    urls: list[HttpUrl] = Field(min_length=1, max_length=100)
    config: CrawlConfig | None = None
    tags: list[str] = Field(default_factory=list)
    priority: Literal["low", "normal", "high"] = "normal"


class BulkAuditResponse(BaseModel):
    """Response for bulk audit operations."""

    batch_id: str
    jobs: list[CrawlJobResponse] = Field(default_factory=list)
    total_urls: int = 0
    estimated_completion: datetime | None = None


class ExportRequest(BaseModel):
    """Data export request."""

    audit_ids: list[str] = Field(min_length=1)
    format: Literal["json", "csv", "xlsx", "pdf"] = "json"
    include_raw_data: bool = False
    include_issues: bool = True
    include_recommendations: bool = True
    include_pages: bool = True
    include_site_signals: bool = True
    filters: dict[str, Any] = Field(default_factory=dict)


class ExportResponse(BaseModel):
    """Data export response."""

    export_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    download_url: str | None = None
    expires_at: datetime | None = None
    file_size_bytes: int | None = None
    error: str | None = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = ""
    uptime_seconds: float = 0
    checks: dict[str, HealthCheck] = Field(default_factory=dict)
    active_jobs: int = 0
    queued_jobs: int = 0
    completed_today: int = 0
    failed_today: int = 0


class HealthCheck(BaseModel):
    """Individual health check."""

    name: str
    status: Literal["pass", "warn", "fail"]
    message: str = ""
    latency_ms: float = 0
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MetricsSnapshot(BaseModel):
    """System metrics snapshot."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_percent: float = 0
    memory_percent: float = 0
    disk_percent: float = 0
    network_io: dict[str, int] = Field(default_factory=dict)
    active_connections: int = 0
    queue_depths: dict[str, int] = Field(default_factory=dict)
    error_rates: dict[str, float] = Field(default_factory=dict)
    response_times: dict[str, float] = Field(default_factory=dict)


class WebhookPayload(BaseModel):
    """Webhook payload for job events."""

    event: Literal["job.started", "job.progress", "job.completed", "job.failed", "job.cancelled", "job.paused"]
    job_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict)
    signature: str = ""


class ApiKeyCreateRequest(BaseModel):
    """Request to create an API key."""

    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    rate_limit: int = Field(default=1000, ge=1, le=100000)
    ip_whitelist: list[str] = Field(default_factory=list)


class ApiKeyResponse(BaseModel):
    """API key creation response."""

    key_id: str
    name: str
    key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)
    rate_limit: int = 1000


class UserPreferences(BaseModel):
    """User SEO preferences."""

    default_max_pages: int = Field(default=100, ge=1, le=500)
    default_max_depth: int = Field(default=10, ge=0, le=50)
    default_user_agent: str = "VexBot/1.0"
    default_delay: float = Field(default=0.5, ge=0, le=10)
    default_concurrent: int = Field(default=5, ge=1, le=50)
    preferred_report_format: Literal["html", "pdf", "markdown", "json"] = "html"
    preferred_report_template: Literal["executive", "technical", "content", "full"] = "full"
    email_notifications: bool = True
    webhook_notifications: bool = False
    default_ai_model: str = "gpt-4o-mini"
    default_ai_recommendations: bool = False
    theme: Literal["light", "dark", "system"] = "system"
    language: str = "en"
    timezone: str = "UTC"
    custom_scoring_weights: ScoringWeights | None = None
    custom_issue_thresholds: IssueThresholds | None = None
    ignored_issue_codes: list[str] = Field(default_factory=list)
    favorite_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)


class IntegrationConfig(BaseModel):
    """Third-party integration configuration."""

    integration_type: Literal["google_search_console", "google_analytics", "ahrefs", "semrush", "screaming_frog", "sitebulb", "custom"]
    name: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)
    sync_schedule: str = ""
    last_sync: datetime | None = None
    last_sync_status: Literal["success", "failed", "partial"] | None = None
    last_sync_error: str | None = None


class NotificationRule(BaseModel):
    """Notification rule for audit events."""

    id: str = Field(default_factory=lambda: f"notif_{int(datetime.utcnow().timestamp() * 1000)}")
    name: str
    event: Literal["audit.completed", "audit.failed", "audit.score_drop", "audit.new_critical_issue", "job.started", "job.completed", "job.failed"]
    condition: dict[str, Any] = Field(default_factory=dict)
    channels: list[Literal["email", "webhook", "slack", "discord", "teams"]] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)
    webhook_url: HttpUrl | None = None
    enabled: bool = True
    cooldown_minutes: int = Field(default=60, ge=0)
    last_triggered: datetime | None = None
    trigger_count: int = 0


class NotificationEvent(BaseModel):
    """Notification event payload."""

    rule_id: str
    event_type: str
    audit_id: str | None = None
    job_id: str | None = None
    title: str
    message: str
    severity: IssueSeverity = IssueSeverity.P2
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SystemSettings(BaseModel):
    """System-wide settings."""

    max_concurrent_jobs: int = Field(default=10, ge=1, le=100)
    max_pages_per_job: int = Field(default=5000, ge=1, le=50000)
    default_job_timeout: int = Field(default=3600, ge=60, le=86400)
    job_retention_days: int = Field(default=30, ge=1, le=365)
    report_retention_days: int = Field(default=90, ge=1, le=365)
    export_retention_days: int = Field(default=7, ge=1, le=30)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    enable_ai_features: bool = True
    default_ai_model: str = "gpt-4o-mini"
    max_ai_tokens_per_audit: int = Field(default=50000, ge=1000, le=200000)
    rate_limit_requests_per_minute: int = Field(default=60, ge=1, le=1000)
    rate_limit_burst: int = Field(default=10, ge=1, le=100)
    enable_metrics: bool = True
    metrics_retention_days: int = Field(default=30, ge=1, le=365)
    enable_tracing: bool = False
    trace_sample_rate: float = Field(default=0.1, ge=0, le=1)
    maintenance_mode: bool = False
    maintenance_message: str = ""
    allowed_origins: list[str] = Field(default_factory=list)
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)
    enable_webhooks: bool = True
    webhook_timeout_seconds: int = Field(default=30, ge=5, le=300)
    webhook_retry_attempts: int = Field(default=3, ge=0, le=10)
    webhook_retry_backoff: float = Field(default=2.0, ge=0.1, le=60)


__all__ = [
    "IssueSeverity",
    "IssueCategory",
    "PageType",
    "CrawlStatus",
    "IndexabilityStatus",
    "RedirectType",
    "StructuredDataType",
    "CoreWebVitalsMetric",
    "CWVRating",
    "HttpStatusCategory",
    "CrawlConfig",
    "CrawlUrlResult",
    "LinkInfo",
    "ImageInfo",
    "StructuredDataItem",
    "SecurityHeaders",
    "PerformanceMetrics",
    "AccessibilityIssue",
    "SeoIssueCore",
    "SeoRecommendationCore",
    "PageScoreBreakdown",
    "SiteScoreBreakdown",
    "CrawlSummary",
    "CrawlError",
    "RobotsTxtInfo",
    "RobotsUserAgent",
    "SitemapInfo",
    "SeoAuditConfig",
    "ScoringWeights",
    "IssueThresholds",
    "CustomRule",
    "PlatformProfile",
    "AuditComparison",
    "KeywordOpportunity",
    "CompetitorGap",
    "InternationalSeoSignal",
    "EcommerceSeoSignal",
    "ContentQualitySignal",
    "EEATSignals",
    "TechnicalSeoSnapshot",
    "CrawlJobRequest",
    "CrawlJobResponse",
    "CrawlProgressUpdate",
    "SeoReportRequest",
    "SeoReportResponse",
    "AuditListParams",
    "AuditListResponse",
    "BulkAuditRequest",
    "BulkAuditResponse",
    "ExportRequest",
    "ExportResponse",
    "HealthCheckResponse",
    "HealthCheck",
    "MetricsSnapshot",
    "WebhookPayload",
    "ApiKeyCreateRequest",
    "ApiKeyResponse",
    "UserPreferences",
    "IntegrationConfig",
    "NotificationRule",
    "NotificationEvent",
    "SystemSettings",
]