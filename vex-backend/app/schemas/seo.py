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
    status: Literal["completed", "failed"] = "completed"
    created_at: str
    max_pages: int
    crawled_pages: int
    score: int
    issues: list[SeoIssue] = Field(default_factory=list)
    recommendations: list[SeoRecommendation] = Field(default_factory=list)
    pages: list[SeoPageAnalysis] = Field(default_factory=list)
    site_signals: SeoSiteSignals = Field(default_factory=SeoSiteSignals)
    crawl_errors: list[str] = Field(default_factory=list)
    ai_recommendations: list[SeoRecommendation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeoAuditSummary(BaseModel):
    """Response returned after audit creation."""

    success: bool = True
    audit: SeoAudit


class SeoReportResponse(BaseModel):
    """Human-readable report response."""

    success: bool = True
    audit_id: str
    report: str
