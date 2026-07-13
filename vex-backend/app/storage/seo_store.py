from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import DATA_DIR
from app.storage.entity_store import find_item, list_items, upsert_item

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
