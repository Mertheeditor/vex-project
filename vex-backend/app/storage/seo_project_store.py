from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import DATA_DIR
from app.storage.entity_store import find_item, list_items, upsert_item, load_json, save_json

SEO_PROJECTS_PATH = DATA_DIR / "seo_projects.json"


class SeoProjectStore:
    """JSON-backed SEO project store."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SEO_PROJECTS_PATH

    def save_project(self, project: dict[str, Any]) -> dict[str, Any]:
        return upsert_item(self.path, project, fallback="seo-project")

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return find_item(self.path, project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        return list_items(self.path)

    def delete_project(self, project_id: str) -> bool:
        data = load_json(self.path, [])
        if not isinstance(data, list):
            return False
        original_len = len(data)
        data = [item for item in data if item.get("id") != project_id]
        if len(data) == original_len:
            return False
        save_json(self.path, data)
        return True