from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

from app.schemas.seo import (
    AuditComparison,
    AuditListParams,
    AuditListResponse,
    AuditProgress,
    ExportFormat,
    SeoAuditRequest,
    SeoAuditSummary,
    SeoReportResponse,
)
from app.services.seo_service import SeoAuditError, SeoAuditService

router = APIRouter(prefix="/seo", tags=["seo"])


def get_seo_service() -> SeoAuditService:
    """Return SEO audit service instance."""

    return SeoAuditService()


@router.post("/audits", response_model=SeoAuditSummary)
async def create_seo_audit(request: SeoAuditRequest) -> SeoAuditSummary:
    service = get_seo_service()
    try:
        audit = await service.create_audit(
            url=str(request.url),
            max_pages=request.max_pages,
            country=request.country,
            language=request.language,
            business_description=request.business_description,
            include_ai_recommendations=request.include_ai_recommendations,
            project_id=request.project_id,
        )
    except SeoAuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Add audit to project history if project_id provided
    if request.project_id:
        from app.services.seo_project_service import SeoProjectService
        project_service = SeoProjectService()
        project_service.add_audit_to_history(request.project_id, audit.id, audit.score, audit.crawled_pages)
    return SeoAuditSummary(audit=audit)


@router.get("/audits", response_model=AuditListResponse)
def list_seo_audits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: list[str] | None = Query(None),
    project_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    min_score: int | None = Query(None, ge=0, le=100),
    max_score: int | None = Query(None, ge=0, le=100),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> AuditListResponse:
    service = get_seo_service()
    params = {
        "page": page,
        "page_size": page_size,
        "status": status,
        "project_id": project_id,
        "date_from": date_from,
        "date_to": date_to,
        "min_score": min_score,
        "max_score": max_score,
        "search": search,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    result = service.list_audits(params)
    return AuditListResponse(**result)


@router.get("/audits/{audit_id}", response_model=SeoAuditSummary)
def get_seo_audit(audit_id: str) -> SeoAuditSummary:
    service = get_seo_service()
    try:
        return SeoAuditSummary(audit=service.get_audit(audit_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="SEO audit not found") from exc


@router.get("/audits/{audit_id}/progress", response_model=AuditProgress)
def get_audit_progress(audit_id: str) -> AuditProgress:
    service = get_seo_service()
    try:
        return service.get_audit_progress(audit_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="SEO audit not found") from exc


@router.get("/audits/{audit_id}/compare", response_model=AuditComparison)
def compare_audits(audit_id: str, baseline_id: str = Query(..., alias="baseline_id")) -> AuditComparison:
    service = get_seo_service()
    try:
        return service.compare_audits(baseline_id, audit_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="SEO audit not found") from exc


@router.get("/audits/{audit_id}/report", response_model=SeoReportResponse)
def get_seo_report(audit_id: str) -> SeoReportResponse:
    service = get_seo_service()
    try:
        return SeoReportResponse(audit_id=audit_id, report=service.report(audit_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="SEO audit not found") from exc


@router.get("/audits/{audit_id}/export/markdown")
def export_seo_markdown(audit_id: str) -> Response:
    service = get_seo_service()
    try:
        return Response(content=service.export_markdown(audit_id), media_type="text/markdown")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="SEO audit not found") from exc


@router.get("/audits/{audit_id}/export/json")
def export_seo_json(audit_id: str) -> dict[str, Any]:
    service = get_seo_service()
    try:
        return service.export_json(audit_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="SEO audit not found") from exc


@router.get("/audits/{audit_id}/export/csv")
def export_seo_csv(
    audit_id: str,
    type: str = Query("issues", pattern="^(issues|pages|both)$"),
    include_details: bool = Query(True),
) -> Response:
    service = get_seo_service()
    try:
        export_format = ExportFormat(format="csv", type=type, include_details=include_details)
        csv_content = service.export_csv(audit_id, export_format)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=seo-audit-{audit_id}-{type}.csv"},
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="SEO audit not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
