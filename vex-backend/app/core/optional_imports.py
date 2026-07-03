from __future__ import annotations

from importlib import import_module
from typing import Any

def optional_import(module_name: str, attr_name: str | None = None) -> tuple[Any | None, str | None]:
    try:
        module = import_module(module_name)
        if attr_name:
            return getattr(module, attr_name), None
        return module, None
    except Exception as exc:
        return None, str(exc)

def module_status(module_name: str, attr_name: str | None = None) -> str:
    _, error = optional_import(module_name, attr_name)
    return "available" if error is None else f"missing: {error}"
