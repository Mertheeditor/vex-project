from __future__ import annotations

"""
Öz-farkındalık — Vex'in kendi kod tabanını GÜVENLE okuyabilmesi.

Bu, dokümandaki self-evolution'ın ilk (salt-okunur) tohumudur. Vex "nasıl
çalışıyorsun / neler yapabilirsin / şu dosyada ne var" sorularını gerçek
kodu okuyarak cevaplayabilir. KIRMIZI ÇİZGİLER burada zorunlu tutulur:
- .env / .env.* / sır dosyaları OKUNMAZ.
- .ssh, *.pem, *.key, *.p12, *.pfx OKUNMAZ.
- Proje kökü DIŞINA çıkılamaz (path traversal engellenir).
- Yalnızca okuma; yazma/silme YOK.
"""

from pathlib import Path

from app.core.config import BASE_DIR

# Proje kökü: vex-backend'in bir üstü (vex-app + vex-backend'i kapsar).
PROJECT_ROOT = BASE_DIR.parent.resolve()

# İsimce yasak (sır) dosyalar / uzantılar.
FORBIDDEN_NAMES = {".env"}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".crt", ".cer"}
FORBIDDEN_MARKERS = (".env", ".ssh", "id_rsa", "id_ed25519", "secret", "credential", "token")

# Gürültü / gereksiz dizinler (listeleme ve okuma dışı).
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    "target", "_archive", ".mypy_cache", ".pytest_cache", "data", "screenshots",
}

MAX_READ_BYTES = 60_000  # tek dosyada okunacak azami boyut


def _is_forbidden(path: Path) -> bool:
    name = path.name.lower()
    if name in FORBIDDEN_NAMES:
        return True
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return True
    if any(marker in name for marker in FORBIDDEN_MARKERS):
        return True
    # .env.production gibi türevler
    if name.startswith(".env"):
        return True
    return False


def _safe_resolve(rel_path: str) -> tuple[Path | None, str | None]:
    # Proje kökü dışına çıkışı (../ vb.) engelle.
    try:
        candidate = (PROJECT_ROOT / rel_path).resolve()
    except Exception as exc:
        return None, f"Yol çözümlenemedi: {exc}"
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError:
        return None, "Proje kökü dışına erişim engellendi."
    return candidate, None


def list_files(subdir: str = "", max_items: int = 300) -> dict:
    base, err = _safe_resolve(subdir or ".")
    if err:
        return {"success": False, "message": err}
    if not base.exists():
        return {"success": False, "message": f"Bulunamadı: {subdir}"}
    items: list[str] = []
    for path in sorted(base.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_dir():
            continue
        if _is_forbidden(path):
            continue
        try:
            items.append(str(path.relative_to(PROJECT_ROOT)))
        except ValueError:
            continue
        if len(items) >= max_items:
            break
    return {"success": True, "root": str(PROJECT_ROOT), "count": len(items), "files": items}


def read_file(rel_path: str) -> dict:
    if not rel_path:
        return {"success": False, "message": "Dosya yolu gerekli."}
    path, err = _safe_resolve(rel_path)
    if err:
        return {"success": False, "message": err}
    if _is_forbidden(path):
        return {"success": False, "message": "Bu dosya güvenlik gereği okunamaz (sır/anahtar dosyası)."}
    if not path.exists() or not path.is_file():
        return {"success": False, "message": f"Dosya bulunamadı: {rel_path}"}
    if any(part in SKIP_DIRS for part in path.parts):
        return {"success": False, "message": "Bu dizin okunmuyor (derleme/bağımlılık/veri klasörü)."}
    try:
        raw = path.read_bytes()
    except Exception as exc:
        return {"success": False, "message": f"Okunamadı: {exc}"}
    truncated = len(raw) > MAX_READ_BYTES
    text = raw[:MAX_READ_BYTES].decode("utf-8", errors="replace")
    return {
        "success": True,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "bytes": len(raw),
        "truncated": truncated,
        "content": text,
    }


def project_overview() -> dict:
    # Vex'in kendini tanıtması için üst düzey özet (dosya sayıları + ana modüller).
    listing = list_files("", max_items=1000)
    files = listing.get("files", []) if listing.get("success") else []
    backend = [f for f in files if f.startswith("vex-backend/")]
    frontend = [f for f in files if f.startswith("vex-app/")]
    routes = [f for f in backend if "/routes/" in f and f.endswith(".py")]
    services = [f for f in backend if "/services/" in f and f.endswith(".py")]
    return {
        "success": True,
        "summary": {
            "toplam_dosya": len(files),
            "backend_dosya": len(backend),
            "frontend_dosya": len(frontend),
            "route_sayisi": len(routes),
            "servis_sayisi": len(services),
        },
        "routes": [Path(r).stem for r in routes],
        "services": [Path(s).stem for s in services],
    }
