from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import DATA_DIR
from app.storage.entity_store import find_item, list_items, upsert_item, load_json

SEO_AUDITS_PATH = DATA_DIR / "seo_audits.json"


class SeoAuditStore:
    """JSON-backed SEO audit store."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SEO_AUDITS_PATH

    def save_audit(self, audit: dict[str, Any]) -> dict[str, Any]:
        return upsert_item(self.path, audit, fallback="seo-audit")

    def get_audit(self, audit_id: str) -> dict[str, Any] | None:
        return find_item(self.path, audit_id)

    def list_audits(self) -> list[dict[str, Any]]:
        return list_items(self.path)

    def get_latest(self, project_id: str) -> dict[str, Any] | None:
        """Get the latest audit for a project."""
        all_audits = self.list_audits()
        project_audits = [a for a in all_audits if a.get("project_id") == project_id]
        if not project_audits:
            return None
        # Sort by created_at descending
        project_audits.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return project_audits[0]

    def get_audits_by_project(self, project_id: str) -> list[dict[str, Any]]:
        """Get all audits for a project, newest first."""
        all_audits = self.list_audits()
        project_audits = [a for a in all_audits if a.get("project_id") == project_id]
        project_audits.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return project_audits
