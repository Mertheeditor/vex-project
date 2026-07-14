from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.schemas.seo_core import CrawlConfig
from app.storage.seo_project_store import SeoProjectStore


class SeoProjectService:
    """Service for managing SEO projects and their configurations."""

    def __init__(self, store: SeoProjectStore | None = None) -> None:
        self.store = store or SeoProjectStore()

    def create_project(
        self,
        name: str,
        domain: str,
        description: str = "",
        max_pages: int = 100,
        max_depth: int = 10,
        crawl_config: dict[str, Any] | None = None,
        country: str = "",
        language: str = "",
    ) -> dict[str, Any]:
        """Create a new SEO project."""
        if not name or not domain:
            raise ValueError("Name and domain are required")

        # Validate domain format
        domain = domain.strip().lower()
        if not self._is_valid_domain(domain):
            raise ValueError("Invalid domain format")

        # Validate country code (ISO 3166-1 alpha-2)
        if country and not self._is_valid_country_code(country):
            raise ValueError("Invalid country code (use ISO 3166-1 alpha-2)")

        # Validate language code (ISO 639-1)
        if language and not self._is_valid_language_code(language):
            raise ValueError("Invalid language code (use ISO 639-1)")

        # Check for duplicate active project with same domain
        existing = self._find_active_project_by_domain(domain)
        if existing:
            raise ValueError(f"An active project for domain '{domain}' already exists")

        project = {
            "name": name.strip(),
            "domain": domain,
            "description": description.strip(),
            "max_pages": max(1, min(max_pages, 5000)),
            "max_depth": max(0, min(max_depth, 50)),
            "crawl_config": crawl_config or {},
            "audit_history": [],
            "created_at": datetime.utcnow().isoformat(timespec="seconds"),
            "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
            "archived": False,
            "country": country.upper() if country else "",
            "language": language.lower() if language else "",
        }
        return self.store.save_project(project)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get an SEO project by ID."""
        return self.store.get_project(project_id)

    def list_projects(self, include_archived: bool = False) -> list[dict[str, Any]]:
        """List all SEO projects. Excludes archived by default."""
        projects = self.store.list_projects()
        if not include_archived:
            projects = [p for p in projects if not p.get("archived", False)]
        return projects

    def update_project(self, project_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update an SEO project."""
        from app.storage.json_store import load_json, save_json

        data = load_json(self.store.path, [])
        if not isinstance(data, list):
            return None

        for item in data:
            if str(item.get("id")) == project_id:
                # Validate domain if being updated
                if "domain" in updates:
                    new_domain = updates["domain"].strip().lower()
                    if not self._is_valid_domain(new_domain):
                        raise ValueError("Invalid domain format")
                    # Check for duplicate (excluding self)
                    existing = self._find_active_project_by_domain(new_domain, exclude_id=project_id)
                    if existing:
                        raise ValueError(f"An active project for domain '{new_domain}' already exists")
                    updates["domain"] = new_domain

                # Validate country if being updated
                if "country" in updates and updates["country"]:
                    if not self._is_valid_country_code(updates["country"]):
                        raise ValueError("Invalid country code (use ISO 3166-1 alpha-2)")
                    updates["country"] = updates["country"].upper()

                # Validate language if being updated
                if "language" in updates and updates["language"]:
                    if not self._is_valid_language_code(updates["language"]):
                        raise ValueError("Invalid language code (use ISO 639-1)")
                    updates["language"] = updates["language"].lower()

                item.update(updates)
                item["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
                save_json(self.store.path, data)
                return item
        return None

    def delete_project(self, project_id: str) -> bool:
        """Delete an SEO project (soft delete - archive)."""
        from app.storage.json_store import load_json, save_json

        data = load_json(self.store.path, [])
        if not isinstance(data, list):
            return False

        for item in data:
            if str(item.get("id")) == project_id:
                item["archived"] = True
                item["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
                save_json(self.store.path, data)
                return True
        return False

    def restore_project(self, project_id: str) -> bool:
        """Restore an archived project."""
        from app.storage.json_store import load_json, save_json

        data = load_json(self.store.path, [])
        if not isinstance(data, list):
            return False

        for item in data:
            if str(item.get("id")) == project_id:
                if not item.get("archived", False):
                    return False
                item["archived"] = False
                item["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
                save_json(self.store.path, data)
                return True
        return False

    def get_default_crawl_config(self, project_id: str) -> CrawlConfig:
        """Get default crawl configuration for a project."""
        project = self.store.get_project(project_id)
        if not project:
            return CrawlConfig(start_url="https://example.com")

        domain = project.get("domain", "")
        return CrawlConfig(
            start_url=f"https://{domain}",
            max_pages=project.get("max_pages", 100),
            max_depth=project.get("max_depth", 10),
            country=project.get("country", ""),
            language=project.get("language", ""),
        )

    def add_audit_to_history(
        self, project_id: str, audit_id: str, score: int, crawled_pages: int
    ) -> bool:
        """Add an audit result to project history."""
        project = self.store.get_project(project_id)
        if not project:
            return False

        history = project.get("audit_history", [])
        history.insert(0, {
            "audit_id": audit_id,
            "score": score,
            "crawled_pages": crawled_pages,
            "completed_at": datetime.utcnow().isoformat(timespec="seconds"),
        })
        project["audit_history"] = history[:50]  # Keep last 50 audits
        project["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
        self.store.save_project(project)
        return True

    def get_capabilities(self) -> dict[str, Any]:
        """Get SEO backend capabilities and supported features."""
        return {
            "crawl": {
                "max_pages_per_job": 5000,
                "max_depth": 50,
                "max_concurrent_jobs": 10,
                "javascript_rendering": True,
                "screenshot_on_error": True,
                "custom_headers": True,
                "authentication": True,
                "robots_txt_respect": True,
                "sitemap_discovery": True,
            },
            "analysis": {
                "technical_seo": True,
                "on_page_seo": True,
                "content_quality": True,
                "core_web_vitals": True,
                "mobile_usability": True,
                "structured_data": True,
                "international_seo": True,
                "ecommerce_seo": True,
                "accessibility_audit": True,
                "security_headers": True,
                "duplicate_content_detection": True,
                "canonical_analysis": True,
                "hreflang_validation": True,
                "redirect_chain_analysis": True,
            },
            "scoring": {
                "page_level_scoring": True,
                "site_level_scoring": True,
                "custom_weights": True,
                "issue_thresholds": True,
            },
            "exports": {
                "formats": ["html", "pdf", "markdown", "json", "csv"],
                "templates": ["executive", "technical", "content", "full"],
            },
            "integrations": {
                "google_search_console": False,
                "google_analytics": False,
                "ahrefs": False,
                "semrush": False,
                "screaming_frog": False,
            },
            "ai_features": {
                "recommendations": True,
                "content_suggestions": True,
                "custom_models": False,
            },
            "version": "1.0.0",
        }

    def get_provider_status(self) -> dict[str, Any]:
        """Get status of external SEO data providers."""
        return {
            "google_search_console": {
                "configured": False,
                "status": "not_configured",
                "last_sync": None,
                "quota_remaining": None,
            },
            "google_analytics": {
                "configured": False,
                "status": "not_configured",
                "last_sync": None,
            },
            "ahrefs": {
                "configured": False,
                "status": "not_configured",
                "last_sync": None,
            },
            "semrush": {
                "configured": False,
                "status": "not_configured",
                "last_sync": None,
            },
            "custom_api": {
                "configured": False,
                "status": "not_configured",
                "last_sync": None,
            },
        }

    def _find_active_project_by_domain(self, domain: str, exclude_id: str | None = None) -> dict[str, Any] | None:
        """Find active project with matching domain."""
        projects = self.store.list_projects()
        for p in projects:
            if p.get("archived", False):
                continue
            if p.get("domain") == domain:
                if exclude_id and str(p.get("id")) == exclude_id:
                    continue
                return p
        return None

    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain format."""
        import re
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))

    def _is_valid_country_code(self, code: str) -> bool:
        """Validate ISO 3166-1 alpha-2 country code."""
        valid_codes = {
            "US", "CA", "GB", "DE", "FR", "IT", "ES", "NL", "BE", "CH", "AT", "PL", "CZ", "SK", "HU",
            "RO", "BG", "HR", "SI", "EE", "LV", "LT", "FI", "SE", "NO", "DK", "IE", "PT", "GR", "CY",
            "MT", "LU", "TR", "RU", "UA", "BY", "MD", "GE", "AM", "AZ", "KZ", "UZ", "KG", "TJ", "TM",
            "CN", "JP", "KR", "TW", "HK", "MO", "SG", "MY", "TH", "VN", "ID", "PH", "AU", "NZ", "IL",
            "SA", "AE", "QA", "KW", "BH", "OM", "JO", "LB", "EG", "MA", "DZ", "TN", "LY", "ZA", "NG",
            "KE", "GH", "ET", "TZ", "UG", "RW", "BR", "AR", "CL", "CO", "PE", "VE", "EC", "BO", "PY",
            "UY", "MX", "CR", "PA", "GT", "SV", "HN", "NI", "DO", "PR", "CU", "JM", "TT", "BB"
        }
        return code.upper() in valid_codes

    def _is_valid_language_code(self, code: str) -> bool:
        """Validate ISO 639-1 language code."""
        valid_codes = {
            "en", "de", "fr", "es", "it", "pt", "nl", "pl", "cs", "sk", "hu", "ro", "bg", "hr",
            "sl", "et", "lv", "lt", "fi", "sv", "no", "da", "is", "ga", "cy", "eu", "ca", "gl",
            "zh", "ja", "ko", "th", "vi", "id", "ms", "tl", "hi", "bn", "ta", "te", "mr", "gu",
            "kn", "ml", "or", "as", "pa", "ur", "fa", "ar", "he", "tr", "el", "ru", "uk", "be"
        }
        return code.lower() in valid_codes