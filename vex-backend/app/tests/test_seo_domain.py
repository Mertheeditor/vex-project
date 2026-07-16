"""Tests for SEO Domain Overview and Organic Research endpoints."""

from __future__ import annotations

from datetime import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.schemas.seo_domain import (
    DataSourceStatus,
    DataSourceType,
    DataSourcesResponse,
    DomainOverviewMetrics,
    DomainOverviewResponse,
    OrganicKeywordsResponse,
)
from main import app


class TestSeoDomainRoutes(unittest.TestCase):
    """Test project-scoped SEO Domain API routes."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("app.routes.seo_domain.get_domain_service")
    def test_unknown_project_returns_404(self, mock_get_service: MagicMock) -> None:
        """Unknown project errors are mapped to HTTP 404."""
        mock_service = MagicMock()
        mock_service.get_domain_overview = AsyncMock(side_effect=ValueError("Project not found"))
        mock_get_service.return_value = mock_service

        response = self.client.get("/seo/projects/missing/domain-overview")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Project not found", response.json()["detail"])

    @patch("app.routes.seo_domain.get_domain_service")
    def test_domain_overview_null_provider_contract(self, mock_get_service: MagicMock) -> None:
        """Domain overview returns provider status without inventing organic rows."""
        mock_service = MagicMock()
        mock_service.get_domain_overview = AsyncMock(return_value=DomainOverviewResponse(
            metrics=DomainOverviewMetrics(
                domain="example.com",
                country="US",
                language="en",
                organic_keywords=0,
                organic_traffic=0,
                data_source=DataSourceType.ESTIMATED,
                last_updated=datetime(2026, 7, 16, 12, 0, 0),
            ),
            history=[],
            data_sources=DataSourcesResponse(sources=[
                DataSourceStatus(
                    source=DataSourceType.CUSTOM,
                    configured=True,
                    status="active",
                    supported_features=["site_audit"],
                ),
                DataSourceStatus(
                    source=DataSourceType.SEMRUSH,
                    configured=False,
                    status="not_configured",
                    supported_features=["organic_keywords"],
                ),
            ]),
            last_refresh=datetime(2026, 7, 16, 12, 0, 0),
        ))
        mock_get_service.return_value = mock_service

        response = self.client.get("/seo/projects/proj-123/domain-overview")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["metrics"]["domain"], "example.com")
        self.assertEqual(data["metrics"]["organic_keywords"], 0)
        self.assertEqual(data["data_sources"]["sources"][1]["status"], "not_configured")

    @patch("app.routes.seo_domain.get_domain_service")
    def test_organic_keyword_pagination_and_filters(self, mock_get_service: MagicMock) -> None:
        """Keyword endpoint forwards pagination and filters to the service."""
        mock_service = MagicMock()
        mock_service.get_organic_keywords = AsyncMock(return_value=OrganicKeywordsResponse(
            items=[],
            total=0,
            page=2,
            page_size=20,
            total_pages=0,
            has_next=False,
            has_prev=True,
        ))
        mock_get_service.return_value = mock_service

        response = self.client.get(
            "/seo/projects/proj-123/organic-keywords",
            params={
                "page": 2,
                "page_size": 20,
                "search": "shoe",
                "position_from": 1,
                "position_to": 10,
                "intent": "commercial",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["page"], 2)
        call_kwargs = mock_service.get_organic_keywords.call_args.kwargs
        self.assertEqual(call_kwargs["page"], 2)
        self.assertEqual(call_kwargs["page_size"], 20)
        self.assertEqual(call_kwargs["search"], "shoe")
        self.assertEqual(call_kwargs["position_to"], 10)
        self.assertEqual(call_kwargs["intent"], "commercial")

    @patch("app.routes.seo_domain.get_domain_service")
    def test_data_sources_response_has_no_secret_fields(self, mock_get_service: MagicMock) -> None:
        """Data sources endpoint returns status/capability but no API key or secret."""
        mock_service = MagicMock()
        mock_service.get_data_sources = AsyncMock(return_value=DataSourcesResponse(sources=[
            DataSourceStatus(
                source=DataSourceType.GOOGLE_SEARCH_CONSOLE,
                configured=False,
                status="not_configured",
                error_message=None,
                supported_features=["clicks", "impressions"],
            )
        ]))
        mock_get_service.return_value = mock_service

        response = self.client.get("/seo/projects/proj-123/data-sources")

        self.assertEqual(response.status_code, 200)
        response_text = response.text.lower()
        self.assertNotIn("api_key", response_text)
        self.assertNotIn("secret", response_text)
        self.assertEqual(response.json()["sources"][0]["status"], "not_configured")

    def test_pagination_validation(self) -> None:
        """FastAPI validates pagination bounds on domain endpoints."""
        response = self.client.get("/seo/projects/proj-123/organic-keywords", params={"page": 0})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
