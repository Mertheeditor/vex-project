from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.seo_domain import (
    BulkDomainOverviewRequest,
    BulkDomainOverviewResponse,
    CompetitorsResponse,
    DataSourcesResponse,
    DomainOverviewResponse,
    ExportDomainOverviewRequest,
    ExportDomainOverviewResponse,
    OrganicKeywordsResponse,
    OrganicPagesResponse,
    PositionChangesResponse,
)
from app.services.seo_domain_service import SeoDomainService


router = APIRouter(prefix="/seo/projects", tags=["seo-domain"])


def get_domain_service() -> SeoDomainService:
    return SeoDomainService()


@router.get("/{project_id}/domain-overview", response_model=DomainOverviewResponse)
async def get_domain_overview(
    project_id: str,
    country: str = Query("US", description="Country code"),
    language: str = Query("en", description="Language code"),
    include_history: bool = Query(True, description="Include historical data"),
    history_days: int = Query(30, ge=1, le=365, description="Days of history to include"),
    use_cache: bool = Query(True, description="Use cached data"),
) -> DomainOverviewResponse:
    """Get complete domain overview with metrics, history, and data sources from latest Site Audit."""
    service = get_domain_service()
    try:
        return await service.get_domain_overview(
            project_id=project_id,
            country=country,
            language=language,
            include_history=include_history,
            history_days=history_days,
            use_cache=use_cache,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/organic-keywords", response_model=OrganicKeywordsResponse)
async def get_organic_keywords(
    project_id: str,
    country: str = Query("US", description="Country code"),
    language: str = Query("en", description="Language code"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    search: str | None = Query(None, description="Search in keyword"),
    position_from: int | None = Query(None, ge=1, le=100, description="Minimum position"),
    position_to: int | None = Query(None, ge=1, le=100, description="Maximum position"),
    volume_from: int | None = Query(None, ge=0, description="Minimum search volume"),
    volume_to: int | None = Query(None, ge=0, description="Maximum search volume"),
    difficulty_from: float | None = Query(None, ge=0, le=100, description="Minimum keyword difficulty"),
    difficulty_to: float | None = Query(None, ge=0, le=100, description="Maximum keyword difficulty"),
    intent: str | None = Query(None, description="Keyword intent filter"),
    sort_by: str = Query("traffic", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    use_cache: bool = Query(True, description="Use cached data"),
) -> OrganicKeywordsResponse:
    """Get organic keywords for a project's domain. Returns empty pagination with provider status when no keyword provider connected."""
    service = get_domain_service()
    try:
        return await service.get_organic_keywords(
            project_id=project_id,
            country=country,
            language=language,
            page=page,
            page_size=page_size,
            search=search,
            position_from=position_from,
            position_to=position_to,
            volume_from=volume_from,
            volume_to=volume_to,
            difficulty_from=difficulty_from,
            difficulty_to=difficulty_to,
            intent=intent,
            sort_by=sort_by,
            sort_order=sort_order,
            use_cache=use_cache,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/organic-pages", response_model=OrganicPagesResponse)
async def get_organic_pages(
    project_id: str,
    country: str = Query("US", description="Country code"),
    language: str = Query("en", description="Language code"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    search: str | None = Query(None, description="Search in URL or page type"),
    keywords_from: int | None = Query(None, ge=0, description="Minimum keywords"),
    keywords_to: int | None = Query(None, ge=0, description="Maximum keywords"),
    traffic_from: int | None = Query(None, ge=0, description="Minimum traffic"),
    traffic_to: int | None = Query(None, ge=0, description="Maximum traffic"),
    page_type: str | None = Query(None, description="Page type filter"),
    sort_by: str = Query("traffic", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    use_cache: bool = Query(True, description="Use cached data"),
) -> OrganicPagesResponse:
    """Get organic pages (top pages) for a project's domain. Uses Site Audit page data as real source."""
    service = get_domain_service()
    try:
        return await service.get_organic_pages(
            project_id=project_id,
            country=country,
            language=language,
            page=page,
            page_size=page_size,
            search=search,
            keywords_from=keywords_from,
            keywords_to=keywords_to,
            traffic_from=traffic_from,
            traffic_to=traffic_to,
            page_type=page_type,
            sort_by=sort_by,
            sort_order=sort_order,
            use_cache=use_cache,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/organic-competitors", response_model=CompetitorsResponse)
async def get_competitors(
    project_id: str,
    country: str = Query("US", description="Country code"),
    language: str = Query("en", description="Language code"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search in competitor domain"),
    common_keywords_from: int | None = Query(None, ge=0, description="Minimum common keywords"),
    traffic_from: int | None = Query(None, ge=0, description="Minimum competitor traffic"),
    authority_from: int | None = Query(None, ge=0, le=100, description="Minimum authority score"),
    sort_by: str = Query("competition_level", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    use_cache: bool = Query(True, description="Use cached data"),
) -> CompetitorsResponse:
    """Get organic competitors for a project's domain. Returns provider status when no SERP/domain provider connected."""
    service = get_domain_service()
    try:
        return await service.get_competitors(
            project_id=project_id,
            country=country,
            language=language,
            page=page,
            page_size=page_size,
            search=search,
            common_keywords_from=common_keywords_from,
            traffic_from=traffic_from,
            authority_from=authority_from,
            sort_by=sort_by,
            sort_order=sort_order,
            use_cache=use_cache,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/position-changes", response_model=PositionChangesResponse)
async def get_position_changes(
    project_id: str,
    country: str = Query("US", description="Country code"),
    language: str = Query("en", description="Language code"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    search: str | None = Query(None, description="Search in keyword"),
    direction: str | None = Query(None, description="Position change direction (up/down/new/lost)"),
    change_from: int | None = Query(None, description="Minimum absolute change"),
    volume_from: int | None = Query(None, ge=0, description="Minimum search volume"),
    position_from: int | None = Query(None, ge=1, le=100, description="Minimum new position"),
    position_to: int | None = Query(None, ge=1, le=100, description="Maximum new position"),
    sort_by: str = Query("date_detected", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    use_cache: bool = Query(True, description="Use cached data"),
) -> PositionChangesResponse:
    """Get position changes for a project's domain. Requires at least two snapshots for comparison."""
    service = get_domain_service()
    try:
        return await service.get_position_changes(
            project_id=project_id,
            country=country,
            language=language,
            page=page,
            page_size=page_size,
            search=search,
            direction=direction,
            change_from=change_from,
            volume_from=volume_from,
            position_from=position_from,
            position_to=position_to,
            sort_by=sort_by,
            sort_order=sort_order,
            use_cache=use_cache,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/data-sources", response_model=DataSourcesResponse)
async def get_data_sources(project_id: str) -> DataSourcesResponse:
    """Get available data sources and their connection status for a project."""
    service = get_domain_service()
    try:
        return await service.get_data_sources(project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/bulk-overview", response_model=BulkDomainOverviewResponse)
async def bulk_domain_overview(
    project_id: str,
    request: BulkDomainOverviewRequest,
) -> BulkDomainOverviewResponse:
    """Get domain overview for multiple domains at once. (Not project-scoped, uses domains from request)"""
    service = get_domain_service()
    try:
        return await service.bulk_domain_overview(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/export", response_model=ExportDomainOverviewResponse)
async def export_domain_overview(
    project_id: str,
    request: ExportDomainOverviewRequest,
) -> ExportDomainOverviewResponse:
    """Export domain overview data in various formats."""
    service = get_domain_service()
    try:
        return await service.export_domain_overview(project_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/capabilities", response_model=dict[str, Any])
async def get_capabilities() -> dict[str, Any]:
    """Get domain overview capabilities and limits."""
    service = get_domain_service()
    return await service.get_capabilities()