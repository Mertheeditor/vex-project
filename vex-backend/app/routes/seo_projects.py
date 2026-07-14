from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.seo_core import CrawlConfig, CrawlJobRequest
from app.services.seo_project_service import SeoProjectService
from app.services.seo_service import SeoAuditService


router = APIRouter(prefix="/seo/projects", tags=["seo-projects"])


def get_project_service() -> SeoProjectService:
    return SeoProjectService()


def get_audit_service() -> SeoAuditService:
    return SeoAuditService()


@router.post("", response_model=dict[str, Any])
async def create_seo_project(request: dict[str, Any]) -> dict[str, Any]:
    """Create a new SEO project."""
    service = get_project_service()
    try:
        project = service.create_project(
            name=request["name"],
            domain=request["domain"],
            description=request.get("description", ""),
            max_pages=request.get("max_pages", 100),
            max_depth=request.get("max_depth", 10),
            crawl_config=request.get("crawl_config"),
        )
        return project
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[dict[str, Any]])
async def list_seo_projects() -> list[dict[str, Any]]:
    """List all SEO projects."""
    service = get_project_service()
    return service.list_projects()


@router.get("/capabilities", response_model=dict[str, Any])
async def get_seo_capabilities() -> dict[str, Any]:
    """Get SEO backend capabilities and supported features."""
    service = get_project_service()
    return service.get_capabilities()


@router.get("/providers/status", response_model=dict[str, Any])
async def get_provider_status() -> dict[str, Any]:
    """Get status of external SEO data providers."""
    service = get_project_service()
    return service.get_provider_status()


@router.get("/{project_id}", response_model=dict[str, Any])
async def get_seo_project(project_id: str) -> dict[str, Any]:
    """Get an SEO project by ID."""
    service = get_project_service()
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="SEO project not found")
    return project


@router.patch("/{project_id}", response_model=dict[str, Any])
async def update_seo_project(project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update an SEO project."""
    service = get_project_service()
    project = service.update_project(project_id, updates)
    if not project:
        raise HTTPException(status_code=404, detail="SEO project not found")
    return project


@router.delete("/{project_id}", response_model=dict[str, Any])
async def delete_seo_project(project_id: str) -> dict[str, Any]:
    """Delete an SEO project."""
    service = get_project_service()
    deleted = service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="SEO project not found")
    return {"success": True, "deleted": True, "id": project_id}


@router.get("/{project_id}/config", response_model=CrawlConfig)
async def get_project_crawl_config(project_id: str) -> CrawlConfig:
    """Get default crawl configuration for a project."""
    service = get_project_service()
    return service.get_default_crawl_config(project_id)


@router.post("/{project_id}/audits", response_model=dict[str, Any])
async def create_project_audit(project_id: str, request: CrawlJobRequest) -> dict[str, Any]:
    """Start an audit for an SEO project."""
    project_service = get_project_service()
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="SEO project not found")

    audit_service = get_audit_service()
    try:
        audit = await audit_service.create_audit(
            url=str(request.config.start_url),
            max_pages=request.config.max_pages,
            max_depth=request.config.max_depth,
            country=request.config.country or "",
            language=request.config.language or "",
            business_description=project.get("description", ""),
            include_ai_recommendations=request.config.include_ai_recommendations,
        )
        project_service.add_audit_to_history(project_id, audit.id, audit.score, audit.crawled_pages)
        return {"success": True, "audit_id": audit.id}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}/audits", response_model=list[dict[str, Any]])
async def list_project_audits(project_id: str) -> list[dict[str, Any]]:
    """List audit history for an SEO project."""
    project_service = get_project_service()
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="SEO project not found")
    return project.get("audit_history", [])