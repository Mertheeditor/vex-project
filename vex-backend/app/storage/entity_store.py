from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.text_utils import slugify
from app.storage.json_store import load_json, save_json

def list_items(path: Path) -> list[dict]:
    data = load_json(path, [])
    return data if isinstance(data, list) else []

def save_items(path: Path, items: list[dict]) -> None:
    save_json(path, items)

def unique_id(items: list[dict], base: str, fallback: str = "item") -> str:
    base_id = slugify(base, fallback)
    existing = {str(item.get("id", "")) for item in items}
    item_id = base_id
    counter = 2
    while item_id in existing:
        item_id = f"{base_id}-{counter}"
        counter += 1
    return item_id

def upsert_item(path: Path, item: dict, fallback: str = "item") -> dict:
    items = list_items(path)
    item = dict(item)
    if not item.get("id"):
        item["id"] = unique_id(items, item.get("title") or item.get("name") or fallback, fallback)
    item.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    for index, current in enumerate(items):
        if current.get("id") == item["id"]:
            items[index] = {**current, **item}
            save_items(path, items)
            return item
    items.append(item)
    save_items(path, items)
    return item

def delete_item(path: Path, item_id: str) -> bool:
    items = list_items(path)
    new_items = [item for item in items if str(item.get("id")) != item_id]
    save_items(path, new_items)
    return len(new_items) != len(items)

def find_item(path: Path, item_id: str) -> dict | None:
    for item in list_items(path):
        if str(item.get("id")) == item_id:
            return item
    return None

def patch_item(path: Path, item_id: str, updates: dict[str, Any]) -> dict | None:
    items = list_items(path)
    for index, item in enumerate(items):
        if str(item.get("id")) == item_id:
            items[index] = {**item, **updates}
            save_items(path, items)
            return items[index]
    return None
