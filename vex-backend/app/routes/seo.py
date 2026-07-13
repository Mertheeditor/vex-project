from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response

from app.schemas.seo import SeoAuditRequest, SeoAuditSummary, SeoReportResponse
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
        )
    except SeoAuditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SeoAuditSummary(audit=audit)


@router.get("/audits/{audit_id}", response_model=SeoAuditSummary)
def get_seo_audit(audit_id: str) -> SeoAuditSummary:
    service = get_seo_service()
    try:
        return SeoAuditSummary(audit=service.get_audit(audit_id))
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
