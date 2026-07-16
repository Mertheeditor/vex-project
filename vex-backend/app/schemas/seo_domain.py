from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    """Data source types for domain overview."""

    SEMRUSH = "semrush"
    AHREFS = "ahrefs"
    GOOGLE_SEARCH_CONSOLE = "google_search_console"
    GOOGLE_ANALYTICS = "google_analytics"
    CUSTOM = "custom"
    ESTIMATED = "estimated"


class KeywordIntent(str, Enum):
    """Keyword search intent."""

    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"


class PositionChangeDirection(str, Enum):
    """Position change direction."""

    UP = "up"
    DOWN = "down"
    NEW = "new"
    LOST = "lost"
    UNCHANGED = "unchanged"


class TrafficTrend(str, Enum):
    """Traffic trend direction."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class DomainOverviewMetrics(BaseModel):
    """Core domain overview metrics."""

    domain: str
    organic_keywords: int = Field(default=0, ge=0, description="Number of organic keywords")
    organic_traffic: int = Field(default=0, ge=0, description="Estimated organic traffic")
    organic_traffic_cost: float = Field(default=0.0, ge=0.0, description="Estimated traffic cost")
    paid_keywords: int = Field(default=0, ge=0, description="Number of paid keywords")
    paid_traffic: int = Field(default=0, ge=0, description="Estimated paid traffic")
    paid_traffic_cost: float = Field(default=0.0, ge=0.0, description="Estimated paid traffic cost")
    backlinks: int = Field(default=0, ge=0, description="Total backlinks")
    referring_domains: int = Field(default=0, ge=0, description="Referring domains")
    authority_score: int = Field(default=0, ge=0, le=100, description="Authority score (0-100)")
    traffic_trend: TrafficTrend = TrafficTrend.STABLE
    trend_percentage: float = Field(default=0.0, description="Trend percentage change")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_source: DataSourceType = DataSourceType.ESTIMATED
    country: str = ""
    language: str = ""


class DomainOverviewHistoryPoint(BaseModel):
    """Historical data point for domain overview charts."""

    date: datetime
    organic_keywords: int = 0
    organic_traffic: int = 0
    organic_traffic_cost: float = 0.0
    paid_keywords: int = 0
    paid_traffic: int = 0
    paid_traffic_cost: float = 0.0
    backlinks: int = 0
    referring_domains: int = 0
    authority_score: int = 0


class OrganicKeyword(BaseModel):
    """Organic keyword data."""

    keyword: str
    position: int = Field(ge=1, le=100, description="Current position in SERP")
    previous_position: int | None = Field(default=None, ge=1, le=100, description="Previous position")
    position_change: int = Field(default=0, description="Position change (positive = improved)")
    url: str = Field(description="Landing page URL")
    search_volume: int = Field(default=0, ge=0, description="Monthly search volume")
    keyword_difficulty: float = Field(default=0.0, ge=0.0, le=100.0, description="Keyword difficulty 0-100")
    cpc: float = Field(default=0.0, ge=0.0, description="Cost per click")
    traffic: int = Field(default=0, ge=0, description="Estimated traffic from this keyword")
    traffic_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Traffic % of total")
    traffic_cost: float = Field(default=0.0, ge=0.0, description="Estimated traffic cost")
    intent: KeywordIntent = KeywordIntent.INFORMATIONAL
    serps_features: list[str] = Field(default_factory=list, description="SERP features present")
    results_count: int = Field(default=0, ge=0, description="Number of search results")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_source: DataSourceType = DataSourceType.ESTIMATED
    country: str = ""
    language: str = ""


class OrganicKeywordFilters(BaseModel):
    """Filters for organic keywords query."""

    keyword: Optional[str] = None
    position_min: Optional[int] = Field(default=None, ge=1, le=100)
    position_max: Optional[int] = Field(default=None, ge=1, le=100)
    volume_min: Optional[int] = Field(default=None, ge=0)
    volume_max: Optional[int] = Field(default=None, ge=0)
    difficulty_min: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    difficulty_max: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    intent: Optional[KeywordIntent] = None
    serps_feature: Optional[str] = None
    url_contains: Optional[str] = None
    position_change_min: Optional[int] = None
    position_change_max: Optional[int] = None
    traffic_min: Optional[int] = Field(default=None, ge=0)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class OrganicPage(BaseModel):
    """Organic page (top page) data."""

    url: str
    organic_keywords: int = Field(default=0, ge=0, description="Keywords this page ranks for")
    organic_traffic: int = Field(default=0, ge=0, description="Estimated traffic to this page")
    organic_traffic_cost: float = Field(default=0.0, ge=0.0, description="Estimated traffic cost")
    traffic_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Traffic % of total")
    top_keyword: str = Field(default="", description="Top keyword for this page")
    top_keyword_position: int = Field(default=0, ge=0, le=100)
    top_keyword_volume: int = Field(default=0, ge=0)
    backlinks: int = Field(default=0, ge=0)
    referring_domains: int = Field(default=0, ge=0)
    page_type: str = Field(default="", description="Page type classification")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_source: DataSourceType = DataSourceType.ESTIMATED


class OrganicPageFilters(BaseModel):
    """Filters for organic pages query."""

    url_contains: Optional[str] = None
    keywords_min: Optional[int] = Field(default=None, ge=0)
    keywords_max: Optional[int] = Field(default=None, ge=0)
    traffic_min: Optional[int] = Field(default=None, ge=0)
    traffic_max: Optional[int] = Field(default=None, ge=0)
    page_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class Competitor(BaseModel):
    """Competitor domain data."""

    domain: str
    common_keywords: int = Field(default=0, ge=0, description="Keywords in common")
    organic_keywords: int = Field(default=0, ge=0, description="Competitor's total organic keywords")
    organic_traffic: int = Field(default=0, ge=0, description="Competitor's estimated organic traffic")
    organic_traffic_cost: float = Field(default=0.0, ge=0.0)
    paid_keywords: int = Field(default=0, ge=0)
    paid_traffic: int = Field(default=0, ge=0)
    paid_traffic_cost: float = Field(default=0.0, ge=0.0)
    backlinks: int = Field(default=0, ge=0)
    referring_domains: int = Field(default=0, ge=0)
    authority_score: int = Field(default=0, ge=0, le=100)
    competition_level: float = Field(default=0.0, ge=0.0, le=100.0, description="Competition level 0-100")
    top_keywords: list[OrganicKeyword] = Field(default_factory=list, description="Top shared keywords")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_source: DataSourceType = DataSourceType.ESTIMATED


class CompetitorFilters(BaseModel):
    """Filters for competitors query."""

    domain_contains: Optional[str] = None
    common_keywords_min: Optional[int] = Field(default=None, ge=0)
    traffic_min: Optional[int] = Field(default=None, ge=0)
    authority_min: Optional[int] = Field(default=None, ge=0, le=100)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class PositionChange(BaseModel):
    """Position change for a keyword."""

    keyword: str
    url: str
    current_position: int = Field(ge=1, le=100)
    previous_position: int | None = Field(default=None, ge=1, le=100)
    change: int = Field(description="Positive = improved, negative = dropped")
    direction: PositionChangeDirection
    search_volume: int = Field(default=0, ge=0)
    traffic_impact: int = Field(default=0, description="Estimated traffic impact")
    intent: KeywordIntent = KeywordIntent.INFORMATIONAL
    date_detected: datetime = Field(default_factory=datetime.utcnow)
    data_source: DataSourceType = DataSourceType.ESTIMATED


class PositionChangesFilters(BaseModel):
    """Filters for position changes query."""

    direction: Optional[PositionChangeDirection] = None
    keyword_contains: Optional[str] = None
    url_contains: Optional[str] = None
    volume_min: Optional[int] = Field(default=None, ge=0)
    change_min: Optional[int] = None
    change_max: Optional[int] = None
    intent: Optional[KeywordIntent] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class DataSourceStatus(BaseModel):
    """Data source connection status."""

    source: DataSourceType
    configured: bool
    status: str  # connected, not_configured, error, quota_exceeded
    last_sync: Optional[datetime] = None
    quota_remaining: Optional[int] = None
    quota_total: Optional[int] = None
    error_message: Optional[str] = None
    supported_features: list[str] = Field(default_factory=list)


class DomainOverviewRequest(BaseModel):
    """Request parameters for domain overview."""

    domain: str
    country: str = "US"
    language: str = "en"
    data_sources: list[DataSourceType] = Field(default_factory=list)
    include_history: bool = True
    history_days: int = Field(default=30, ge=1, le=365)
    use_cache: bool = True


class OrganicKeywordsRequest(BaseModel):
    """Request parameters for organic keywords."""

    domain: str
    country: str = "US"
    language: str = "en"
    filters: Optional[OrganicKeywordFilters] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    sort_by: str = "traffic"
    sort_order: str = "desc"
    data_sources: list[DataSourceType] = Field(default_factory=list)
    use_cache: bool = True


class OrganicPagesRequest(BaseModel):
    """Request parameters for organic pages."""

    domain: str
    country: str = "US"
    language: str = "en"
    filters: Optional[OrganicPageFilters] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    sort_by: str = "traffic"
    sort_order: str = "desc"
    data_sources: list[DataSourceType] = Field(default_factory=list)
    use_cache: bool = True


class CompetitorsRequest(BaseModel):
    """Request parameters for competitors."""

    domain: str
    country: str = "US"
    language: str = "en"
    filters: Optional[CompetitorFilters] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "competition_level"
    sort_order: str = "desc"
    data_sources: list[DataSourceType] = Field(default_factory=list)
    use_cache: bool = True


class PositionChangesRequest(BaseModel):
    """Request parameters for position changes."""

    domain: str
    country: str = "US"
    language: str = "en"
    filters: Optional[PositionChangesFilters] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    sort_by: str = "date_detected"
    sort_order: str = "desc"
    data_sources: list[DataSourceType] = Field(default_factory=list)
    use_cache: bool = True


class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    items: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class OrganicKeywordsResponse(PaginatedResponse):
    """Response for organic keywords query."""

    items: list[OrganicKeyword] = Field(default_factory=list)
    filters_applied: Optional[OrganicKeywordFilters] = None


class OrganicPagesResponse(PaginatedResponse):
    """Response for organic pages query."""

    items: list[OrganicPage] = Field(default_factory=list)
    filters_applied: Optional[OrganicPageFilters] = None


class CompetitorsResponse(PaginatedResponse):
    """Response for competitors query."""

    items: list[Competitor] = Field(default_factory=list)
    filters_applied: Optional[CompetitorFilters] = None


class PositionChangesResponse(PaginatedResponse):
    """Response for position changes query."""

    items: list[PositionChange] = Field(default_factory=list)
    filters_applied: Optional[PositionChangesFilters] = None


class DataSourcesResponse(BaseModel):
    """Response for data sources status."""

    sources: list[DataSourceStatus] = Field(default_factory=list)
    primary_source: Optional[DataSourceType] = None


class DomainOverviewResponse(BaseModel):
    """Complete domain overview response."""

    metrics: DomainOverviewMetrics
    history: list[DomainOverviewHistoryPoint] = Field(default_factory=list)
    data_sources: DataSourcesResponse
    last_refresh: datetime = Field(default_factory=datetime.utcnow)


# Request/Response for bulk operations
class BulkDomainOverviewRequest(BaseModel):
    """Request for bulk domain overview."""

    domains: list[str] = Field(min_length=1, max_length=50)
    country: str = "US"
    language: str = "en"
    data_sources: list[DataSourceType] = Field(default_factory=list)
    use_cache: bool = True


class BulkDomainOverviewResponse(BaseModel):
    """Response for bulk domain overview."""

    results: dict[str, DomainOverviewResponse] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    processed: int = 0
    failed: int = 0
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class ExportDomainOverviewRequest(BaseModel):
    """Request to export domain overview data."""

    domain: str
    format: str = Field(default="json", pattern="^(json|csv|xlsx)$")
    sections: list[str] = Field(
        default_factory=lambda: [
            "overview",
            "organic_keywords",
            "organic_pages",
            "competitors",
            "position_changes",
        ]
    )
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filters: dict[str, Any] = Field(default_factory=dict)


class ExportDomainOverviewResponse(BaseModel):
    """Response for domain overview export."""

    export_id: str
    status: str  # pending, processing, completed, failed
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    error: Optional[str] = None


__all__ = [
    "DataSourceType",
    "KeywordIntent",
    "PositionChangeDirection",
    "TrafficTrend",
    "DomainOverviewMetrics",
    "DomainOverviewHistoryPoint",
    "OrganicKeyword",
    "OrganicKeywordFilters",
    "OrganicPage",
    "OrganicPageFilters",
    "Competitor",
    "CompetitorFilters",
    "PositionChange",
    "PositionChangesFilters",
    "DataSourceStatus",
    "DomainOverviewRequest",
    "OrganicKeywordsRequest",
    "OrganicPagesRequest",
    "CompetitorsRequest",
    "PositionChangesRequest",
    "PaginatedResponse",
    "OrganicKeywordsResponse",
    "OrganicPagesResponse",
    "CompetitorsResponse",
    "PositionChangesResponse",
    "DataSourcesResponse",
    "DomainOverviewResponse",
    "BulkDomainOverviewRequest",
    "BulkDomainOverviewResponse",
    "ExportDomainOverviewRequest",
    "ExportDomainOverviewResponse",
]