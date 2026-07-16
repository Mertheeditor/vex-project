from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

IssueSeverity = Literal["P0", "P1", "P2", "P3"]
PageType = Literal[
    "homepage",
    "collection",
    "product",
    "blog/article",
    "content page",
    "cart",
    "account",
    "policy",
    "search",
    "unknown",
]


class SeoAuditRequest(BaseModel):
    """Request body for starting an SEO audit."""

    url: HttpUrl
    project_id: str | None = None
    country: str = ""
    language: str = ""
    business_description: str = ""
    max_pages: int = Field(default=100, ge=1, le=500)
    include_ai_recommendations: bool = False

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("Only http and https URLs are supported")
        return value


class AuditComparison(BaseModel):
    """Comparison between two audits."""

    baseline_audit_id: str
    comparison_audit_id: str
    baseline_date: str
    comparison_date: str
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
    category_changes: dict[str, int] = Field(default_factory=dict)


class AuditProgress(BaseModel):
    """Audit progress for polling."""

    audit_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress_pct: float = 0.0
    current_url: str = ""
    current_depth: int = 0
    urls_queued: int = 0
    urls_crawled: int = 0
    urls_failed: int = 0
    urls_skipped: int = 0
    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float | None = None
    pages_per_second: float = 0.0
    recent_errors: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = ""


class AuditListParams(BaseModel):
    """Parameters for listing audits."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    max_score: int | None = Field(default=None, ge=0, le=100)
    search: str | None = None
    project_id: str | None = None
    sort_by: Literal["created_at", "score", "crawled_pages", "status"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class AuditListResponse(BaseModel):
    """Paginated audit list response."""

    audits: list[SeoAudit] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class ExportFormat(BaseModel):
    """Export format options."""

    format: Literal["csv", "json", "markdown"] = "csv"
    type: Literal["issues", "pages", "both"] = "issues"
    include_details: bool = True


class SeoIssue(BaseModel):
    """A deterministic SEO issue discovered during an audit."""

    severity: IssueSeverity
    code: str
    message: str
    url: str = ""
    recommendation: str
    platform_hint: str = "generic"
    current_value: str = ""
    page_type: PageType | str = "unknown"
    scope: Literal["page", "site", "crawl"] = "page"


class SeoRecommendation(BaseModel):
    """Structured SEO recommendation."""

    priority: IssueSeverity
    title: str
    detail: str
    platform_hint: str = "generic"


class SeoPageAnalysis(BaseModel):
    """Per-page SEO extraction result."""

    url: str
    source_url: str = ""
    status_code: int
    depth: int
    page_type: PageType | str = "unknown"
    page_score: int | None = None
    platform: str = "unknown"
    score_reasons: list[str] = Field(default_factory=list)
    title: str = ""
    meta_description: str = ""
    h1: list[str] = Field(default_factory=list)
    h2: list[str] = Field(default_factory=list)
    h3: list[str] = Field(default_factory=list)
    canonical: str = ""
    robots: str = ""
    lang: str = ""
    word_count: int = 0
    internal_links: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    images_total: int = 0
    images_missing_alt: int = 0
    json_ld_count: int = 0
    open_graph: dict[str, str] = Field(default_factory=dict)
    twitter: dict[str, str] = Field(default_factory=dict)
    viewport: str = ""
    indexable: bool = True
    issues: list[SeoIssue] = Field(default_factory=list)


class SeoSiteSignals(BaseModel):
    """Site-level signals derived from all crawled pages."""

    duplicate_titles: dict[str, list[str]] = Field(default_factory=dict)
    duplicate_meta_descriptions: dict[str, list[str]] = Field(default_factory=dict)
    missing_titles: list[str] = Field(default_factory=list)
    missing_meta_descriptions: list[str] = Field(default_factory=list)
    canonical_mismatches: list[str] = Field(default_factory=list)
    broken_links: list[str] = Field(default_factory=list)
    robots_url: str = ""
    sitemap_urls: list[str] = Field(default_factory=list)
    discovered_urls: int = 0
    crawled_urls: int = 0
    skipped_urls: int = 0
    blocked_urls: int = 0
    errored_urls: int = 0
    platform: str = "unknown"
    platform_confidence: str = "unknown"
    page_type_counts: dict[str, int] = Field(default_factory=dict)
    score_reasons: list[str] = Field(default_factory=list)


class SeoAudit(BaseModel):
    """Stored SEO audit."""

    id: str
    requested_url: str
    normalized_url: str
    status: Literal["completed", "failed", "running", "pending"] = "completed"
    created_at: str
    max_pages: int
    crawled_pages: int
    score: int
    project_id: str | None = None
    issues: list[SeoIssue] = Field(default_factory=list)
    recommendations: list[SeoRecommendation] = Field(default_factory=list)
    pages: list[SeoPageAnalysis] = Field(default_factory=list)
    site_signals: SeoSiteSignals = Field(default_factory=SeoSiteSignals)
    crawl_errors: list[str] = Field(default_factory=list)
    ai_recommendations: list[SeoRecommendation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    progress: dict[str, Any] | None = None


class SeoAuditSummary(BaseModel):
    """Response returned after audit creation."""

    success: bool = True
    audit: SeoAudit


class SeoReportResponse(BaseModel):
    """Human-readable report response."""

    success: bool = True
    audit_id: str
    report: str
