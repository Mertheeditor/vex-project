from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

IssueSeverity = Literal["P0", "P1", "P2", "P3"]


class SeoAuditRequest(BaseModel):
    """Request body for starting an SEO audit."""

    url: HttpUrl
    max_pages: int = Field(default=25, ge=1, le=50)
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
