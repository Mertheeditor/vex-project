from __future__ import annotations

from fastapi import APIRouter
from app.schemas.common import SiteProductFinderRequest, UrlAnalyzeRequest
from app.services.site_service import analyze_site, find_products

router = APIRouter()

@router.post("/site/analyze")
def site_analyze(request: UrlAnalyzeRequest):
    return analyze_site(request.url, request.prompt)

@router.post("/site/find-products")
def site_find_products(request: SiteProductFinderRequest):
    return find_products(request.url, request.query, request.language, request.max_pages)
