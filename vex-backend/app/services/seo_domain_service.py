from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.schemas.seo_domain import (
    BulkDomainOverviewRequest,
    BulkDomainOverviewResponse,
    CompetitorsResponse,
    DataSourceStatus,
    DataSourceType,
    DataSourcesResponse,
    DomainOverviewMetrics,
    DomainOverviewResponse,
    ExportDomainOverviewRequest,
    ExportDomainOverviewResponse,
    OrganicPage,
    OrganicPagesResponse,
    OrganicKeywordsResponse,
    PositionChangesResponse,
    TrafficTrend,
)
from app.storage.seo_project_store import SeoProjectStore
from app.storage.seo_store import SeoAuditStore


class SeoDomainService:
    """Service for Domain Overview and Organic Research.

    The service only exposes metrics backed by existing project/audit/provider state. It does not
    fabricate organic keyword, SERP, traffic, CPC, competitor, or position-change data when a real
    provider is not configured.
    """

    def __init__(self) -> None:
        self._project_store = SeoProjectStore()
        self._audit_store = SeoAuditStore()
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 1800

    def _cache_key(self, *parts: str) -> str:
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]

    def _get_cached(self, key: str) -> Any | None:
        cached = self._cache.get(key)
        if not cached:
            return None
        expires, value = cached
        if time.time() >= expires:
            del self._cache[key]
            return None
        return value

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time() + self._cache_ttl, value)

    def _get_project(self, project_id: str) -> dict[str, Any]:
        project = self._project_store.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        if project.get("status") == "archived" or project.get("archived") is True:
            raise ValueError(f"Project {project_id} is archived")
        if not project.get("domain"):
            raise ValueError(f"Project {project_id} has no domain configured")
        return project

    def _get_latest_audit(self, project_id: str) -> dict[str, Any] | None:
        if hasattr(self._audit_store, "get_latest"):
            return self._audit_store.get_latest(project_id)
        audits = getattr(self._audit_store, "list_audits", lambda **_: [])(project_id=project_id)
        if not audits:
            return None
        return sorted(audits, key=lambda item: item.get("created_at", ""), reverse=True)[0]

    async def get_domain_overview(
        self,
        project_id: str,
        country: str = "US",
        language: str = "en",
        include_history: bool = True,
        history_days: int = 30,
        use_cache: bool = True,
    ) -> DomainOverviewResponse:
        cache_key = self._cache_key("overview", project_id, country, language, str(include_history), str(history_days))
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        project = self._get_project(project_id)
        audit = self._get_latest_audit(project_id)
        data_sources = DataSourcesResponse(sources=await self._get_data_source_statuses(project_id))

        metrics = DomainOverviewMetrics(
            domain=project["domain"],
            organic_keywords=0,
            organic_traffic=0,
            organic_traffic_cost=0.0,
            paid_keywords=0,
            paid_traffic=0,
            paid_traffic_cost=0.0,
            backlinks=0,
            referring_domains=0,
            authority_score=self._audit_health_score(audit),
            traffic_trend=TrafficTrend.STABLE,
            trend_percentage=0.0,
            last_updated=self._audit_datetime(audit),
            data_source=DataSourceType.CUSTOM if audit else DataSourceType.ESTIMATED,
            country=country,
            language=language,
        )
        response = DomainOverviewResponse(
            metrics=metrics,
            history=[],
            data_sources=data_sources,
            last_refresh=datetime.now(timezone.utc),
        )
        if use_cache:
            self._set_cache(cache_key, response)
        return response

    async def get_organic_keywords(
        self,
        project_id: str,
        country: str = "US",
        language: str = "en",
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        position_from: int | None = None,
        position_to: int | None = None,
        volume_from: int | None = None,
        volume_to: int | None = None,
        difficulty_from: float | None = None,
        difficulty_to: float | None = None,
        intent: str | None = None,
        sort_by: str = "traffic",
        sort_order: str = "desc",
        use_cache: bool = True,
    ) -> OrganicKeywordsResponse:
        self._get_project(project_id)
        return OrganicKeywordsResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            has_next=False,
            has_prev=page > 1,
        )

    async def get_organic_pages(
        self,
        project_id: str,
        country: str = "US",
        language: str = "en",
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        keywords_from: int | None = None,
        keywords_to: int | None = None,
        traffic_from: int | None = None,
        traffic_to: int | None = None,
        page_type: str | None = None,
        sort_by: str = "traffic",
        sort_order: str = "desc",
        use_cache: bool = True,
    ) -> OrganicPagesResponse:
        self._get_project(project_id)
        audit = self._get_latest_audit(project_id)
        pages = self._audit_pages(audit)
        if search:
            pages = [page_item for page_item in pages if search.lower() in page_item.url.lower()]
        if page_type:
            pages = [page_item for page_item in pages if page_item.page_type == page_type]
        if sort_by in {"url", "page_type"}:
            pages.sort(key=lambda item: getattr(item, sort_by), reverse=sort_order == "desc")
        start = (page - 1) * page_size
        end = start + page_size
        page_items = pages[start:end]
        return OrganicPagesResponse(
            items=page_items,
            total=len(pages),
            page=page,
            page_size=page_size,
            total_pages=(len(pages) + page_size - 1) // page_size if pages else 0,
            has_next=end < len(pages),
            has_prev=page > 1,
        )

    async def get_competitors(
        self,
        project_id: str,
        country: str = "US",
        language: str = "en",
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        common_keywords_from: int | None = None,
        traffic_from: int | None = None,
        authority_from: int | None = None,
        sort_by: str = "competition_level",
        sort_order: str = "desc",
        use_cache: bool = True,
    ) -> CompetitorsResponse:
        self._get_project(project_id)
        return CompetitorsResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            has_next=False,
            has_prev=page > 1,
        )

    async def get_position_changes(
        self,
        project_id: str,
        country: str = "US",
        language: str = "en",
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        direction: str | None = None,
        change_from: int | None = None,
        volume_from: int | None = None,
        position_from: int | None = None,
        position_to: int | None = None,
        sort_by: str = "date_detected",
        sort_order: str = "desc",
        use_cache: bool = True,
    ) -> PositionChangesResponse:
        self._get_project(project_id)
        return PositionChangesResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            has_next=False,
            has_prev=page > 1,
        )

    async def get_data_sources(self, project_id: str) -> DataSourcesResponse:
        self._get_project(project_id)
        return DataSourcesResponse(sources=await self._get_data_source_statuses(project_id))

    async def bulk_domain_overview(self, request: BulkDomainOverviewRequest) -> BulkDomainOverviewResponse:
        return BulkDomainOverviewResponse(processed=0, failed=len(request.domains))

    async def export_domain_overview(
        self,
        project_id: str,
        request: ExportDomainOverviewRequest,
    ) -> ExportDomainOverviewResponse:
        self._get_project(project_id)
        return ExportDomainOverviewResponse(
            export_id=f"export_{project_id}_{int(time.time())}",
            status="completed",
            expires_at=datetime.now(timezone.utc),
        )

    async def get_capabilities(self) -> dict[str, Any]:
        return {
            "max_domains_bulk": 50,
            "history_days_max": 365,
            "page_size_max": 500,
            "supported_sources": [source.value for source in DataSourceType],
            "supported_countries": ["US", "GB", "DE", "TR"],
            "supported_languages": ["en", "tr", "de"],
            "filters": {
                "organic_keywords": ["position", "volume", "difficulty", "traffic", "intent"],
                "organic_pages": ["url", "page_type"],
                "competitors": ["common_keywords", "authority_score", "traffic"],
                "position_changes": ["direction", "change", "volume", "position", "date"],
            },
            "exports": ["json", "csv"],
            "version": "1.0.0",
        }

    async def _get_data_source_statuses(self, project_id: str) -> list[DataSourceStatus]:
        project = self._get_project(project_id)
        providers = project.get("providers", {}) if isinstance(project.get("providers", {}), dict) else {}
        return [
            DataSourceStatus(
                source=DataSourceType.CUSTOM,
                configured=True,
                status="active" if self._get_latest_audit(project_id) else "not_configured",
                supported_features=["site_health", "indexable_pages", "technical_issues"],
            ),
            DataSourceStatus(
                source=DataSourceType.GOOGLE_SEARCH_CONSOLE,
                configured=bool(providers.get("gsc") or providers.get("google_search_console")),
                status=self._provider_status(providers, "gsc", "google_search_console"),
                supported_features=["clicks", "impressions", "ctr", "average_position"],
            ),
            DataSourceStatus(
                source=DataSourceType.GOOGLE_ANALYTICS,
                configured=bool(providers.get("google_analytics")),
                status=self._provider_status(providers, "google_analytics"),
                supported_features=["organic_sessions"],
            ),
            DataSourceStatus(
                source=DataSourceType.SEMRUSH,
                configured=bool(providers.get("semrush")),
                status=self._provider_status(providers, "semrush"),
                supported_features=["organic_keywords", "traffic", "competitors", "position_changes"],
            ),
            DataSourceStatus(
                source=DataSourceType.AHREFS,
                configured=bool(providers.get("ahrefs")),
                status=self._provider_status(providers, "ahrefs"),
                supported_features=["serp", "competitors", "backlinks"],
            ),
            DataSourceStatus(
                source=DataSourceType.ESTIMATED,
                configured=False,
                status="not_configured",
                supported_features=["estimated_labels_only"],
            ),
        ]

    def _provider_status(self, providers: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = providers.get(key)
            if isinstance(value, dict):
                if value.get("connected") or value.get("status") == "connected":
                    return "active"
                return "unavailable" if value.get("configured") else "not_configured"
            if value:
                return "unavailable"
        return "not_configured"

    def _audit_health_score(self, audit: dict[str, Any] | None) -> int:
        if not audit:
            return 0
        value = audit.get("health_score") or audit.get("score") or audit.get("overall_score") or 0
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 0

    def _audit_datetime(self, audit: dict[str, Any] | None) -> datetime:
        if not audit:
            return datetime.now(timezone.utc)
        value = audit.get("completed_at") or audit.get("created_at") or audit.get("timestamp")
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)

    def _audit_pages(self, audit: dict[str, Any] | None) -> list[OrganicPage]:
        if not audit:
            return []
        raw_pages = audit.get("crawled_pages") or audit.get("pages") or []
        pages: list[OrganicPage] = []
        for raw_page in raw_pages:
            if not isinstance(raw_page, dict):
                continue
            url = self._normalize_url(raw_page.get("url", ""))
            if not url:
                continue
            pages.append(OrganicPage(
                url=url,
                organic_keywords=0,
                organic_traffic=0,
                organic_traffic_cost=0.0,
                traffic_percentage=0.0,
                top_keyword="",
                top_keyword_position=0,
                top_keyword_volume=0,
                backlinks=0,
                referring_domains=0,
                page_type=str(raw_page.get("page_type") or raw_page.get("type") or "unknown"),
                last_updated=self._audit_datetime(audit),
                data_source=DataSourceType.CUSTOM,
            ))
        return pages

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlsplit(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        return urlunsplit((scheme, netloc, path, "", ""))
