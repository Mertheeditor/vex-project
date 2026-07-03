from __future__ import annotations

def ok(**kwargs):
    return {"success": True, **kwargs}

def fail(message: str, **kwargs):
    return {"success": False, "message": message, **kwargs}
