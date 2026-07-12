#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
READ_ONLY_AGENTS = {"architect", "security-auditor", "diff-auditor"}

DANGEROUS_BASH_PATTERNS = (
    (re.compile(r"(^|[\s;&|])sudo(?:\s|$)", re.IGNORECASE), "sudo komutları yasak"),
    (re.compile(r"\brm\s+-[^\n]*r[^\n]*f\b|\brm\s+-[^\n]*f[^\n]*r\b", re.IGNORECASE), "rm -rf yasak"),
    (re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE), "git reset --hard yasak"),
    (re.compile(r"\bgit\s+clean\s+-[^\s]*f[^\s]*d|\bgit\s+clean\s+-[^\s]*d[^\s]*f", re.IGNORECASE), "git clean -fd yasak"),
    (re.compile(r"\bgit\s+push\b[^\n]*(?:--force|-f)(?:\s|$)", re.IGNORECASE), "force push yasak"),
    (re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba)?sh\b", re.IGNORECASE), "uzaktan script pipe ile çalıştırma yasak"),
)

READ_ONLY_MUTATION_PATTERNS = (
    (re.compile(r"(^|[\s;&|])(?:>|>>)(?!&)", re.IGNORECASE), "çıktı yönlendirmesi dosya değiştirebilir"),
    (re.compile(r"(^|[\s;&|])tee(?:\s|$)", re.IGNORECASE), "tee dosya değiştirebilir"),
    (re.compile(r"(^|[\s;&|])(?:mv|cp|rm|touch|mkdir|chmod)(?:\s|$)", re.IGNORECASE), "salt okunur ajan dosya değiştiremez"),
    (re.compile(r"\bgit\s+(?:add|commit|checkout|switch|merge|rebase)\b", re.IGNORECASE), "salt okunur ajan Git durumunu değiştiremez"),
)

SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
SENSITIVE_NAMES = {
    "id_rsa", "id_ed25519", "credentials", "credentials.json",
    "service-account.json", "service_account.json",
}
SENSITIVE_PART_RE = re.compile(
    r"(?:^|[._-])(secret|secrets|credential|credentials|private[_-]?key|access[_-]?token|refresh[_-]?token)(?:$|[._-])",
    re.IGNORECASE,
)


def deny(reason: str) -> None:
    print(f"VEX GUARD BLOCK: {reason}", file=sys.stderr)
    raise SystemExit(2)


def allow() -> None:
    raise SystemExit(0)


def load_input() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        deny(f"Geçersiz hook JSON girdisi: {exc}")
    return {}


def get_project_root(data: Mapping[str, Any]) -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root).expanduser().resolve(strict=False)

    cwd = data.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        candidate = Path(cwd).expanduser().resolve(strict=False)
        for current in (candidate, *candidate.parents):
            if (current / ".claude").exists() or (current / "CLAUDE.md").exists():
                return current
        return candidate

    return Path(__file__).resolve().parents[2]


def get_agent_type(data: Mapping[str, Any]) -> str:
    value = data.get("agent_type") or data.get("agent_name")
    if isinstance(value, str) and value.strip():
        return value.strip()

    env_value = os.environ.get("CLAUDE_AGENT_NAME")
    if env_value:
        return env_value.strip()

    cwd = data.get("cwd")
    if isinstance(cwd, str):
        match = re.search(r"/\.vex-worktrees/(backend-builder|frontend-builder|qa-engineer)(?:/|$)", cwd)
        if match:
            return match.group(1)

    return "vex-lead"


def get_tool_input(data: Mapping[str, Any]) -> Mapping[str, Any]:
    value = data.get("tool_input")
    return value if isinstance(value, Mapping) else {}


def extract_path(tool_input: Mapping[str, Any]) -> Optional[str]:
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_path(raw_path: str, cwd: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return path.resolve(strict=False)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def is_sensitive_path(path: Path) -> bool:
    name = path.name.lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if name in SENSITIVE_NAMES or path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    return any(SENSITIVE_PART_RE.search(part) for part in path.parts)


def check_global_bash(command: str) -> None:
    for pattern, reason in DANGEROUS_BASH_PATTERNS:
        if pattern.search(command):
            deny(reason)


def check_read_only_bash(command: str) -> None:
    for pattern, reason in READ_ONLY_MUTATION_PATTERNS:
        if pattern.search(command):
            deny(reason)


def resolve_worktree_root(
    project_root: Path,
    agent_type: str,
    data: Mapping[str, Any],
    tool_input: Mapping[str, Any],
) -> Path:
    explicit = data.get("worktree_root") or tool_input.get("worktree_root")
    if isinstance(explicit, str) and explicit.strip():
        candidate = Path(explicit).expanduser().resolve(strict=False)
        allowed_parent = (project_root / ".vex-worktrees").resolve(strict=False)
        if not is_relative_to(candidate, allowed_parent):
            deny("worktree_root .vex-worktrees dışında")
        return candidate

    return (project_root / ".vex-worktrees" / agent_type).resolve(strict=False)


def allowed_builder_path(agent_type: str, relative: Path) -> bool:
    rel = relative.as_posix().lstrip("./")
    if rel == "docs/agent-system" or rel.startswith("docs/agent-system/"):
        return True
    if agent_type == "backend-builder":
        return rel == "vex-backend" or rel.startswith("vex-backend/")
    if agent_type == "frontend-builder":
        return rel == "vex-app" or rel.startswith("vex-app/")
    return False


def allowed_qa_path(relative: Path) -> bool:
    rel = relative.as_posix().lstrip("./")
    lower = rel.lower()

    if rel == "docs/agent-system" or rel.startswith("docs/agent-system/"):
        return True
    if rel == "vex-backend/tests" or rel.startswith("vex-backend/tests/"):
        return True
    if rel.startswith(("vex-app/src/test/", "vex-app/src/tests/", "vex-app/src/__tests__/")):
        return True
    if rel.startswith("vex-app/src/") and lower.endswith(
        (".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".test.jsx", ".spec.js", ".spec.jsx")
    ):
        return True
    return False


def enforce_write_path(
    agent_type: str,
    path: Path,
    project_root: Path,
    data: Mapping[str, Any],
    tool_input: Mapping[str, Any],
) -> None:
    if is_sensitive_path(path):
        deny(f"hassas dosyaya erişim yasak: {path}")

    if not is_relative_to(path, project_root):
        deny(f"repo dışına yazma yasak: {path}")

    if agent_type in READ_ONLY_AGENTS:
        deny(f"{agent_type} salt okunur; {path} değiştirilemez")

    if agent_type in {"backend-builder", "frontend-builder", "qa-engineer"}:
        worktree_root = resolve_worktree_root(project_root, agent_type, data, tool_input)
        if not is_relative_to(path, worktree_root):
            deny(f"{agent_type} yalnızca atanmış worktree içinde yazabilir: {worktree_root}")

        relative = path.relative_to(worktree_root)
        if agent_type == "qa-engineer":
            if not allowed_qa_path(relative):
                deny(f"QA yalnızca test alanlarına yazabilir: {relative}")
        elif not allowed_builder_path(agent_type, relative):
            deny(f"{agent_type} yanlış alana yazmaya çalıştı: {relative}")
        return

    if agent_type == "vex-lead":
        relative = path.relative_to(project_root).as_posix()
        if relative == ".claude" or relative.startswith(".claude/"):
            return
        if relative == "docs/agent-system" or relative.startswith("docs/agent-system/"):
            return
        deny(f"Vex Lead ana checkout ürün koduna yazamaz: {relative}")

    deny(f"tanımsız ajan yazma yetkisine sahip değil: {agent_type}")


def main() -> None:
    data = load_input()
    tool_name = str(data.get("tool_name") or "")
    tool_input = get_tool_input(data)
    agent_type = get_agent_type(data)
    project_root = get_project_root(data)

    cwd_value = data.get("cwd")
    cwd = (
        Path(cwd_value).expanduser().resolve(strict=False)
        if isinstance(cwd_value, str) and cwd_value.strip()
        else project_root
    )

    raw_path = extract_path(tool_input)
    if raw_path:
        path = normalize_path(raw_path, cwd)
        if is_sensitive_path(path):
            deny(f"hassas dosyaya erişim yasak: {path}")

    if tool_name == "Bash":
        command = tool_input.get("command")
        command_text = command if isinstance(command, str) else ""
        check_global_bash(command_text)
        if agent_type in READ_ONLY_AGENTS:
            check_read_only_bash(command_text)
        allow()

    if tool_name in WRITE_TOOLS:
        if not raw_path:
            deny(f"{tool_name} için file_path/path bulunamadı")
        enforce_write_path(
            agent_type=agent_type,
            path=normalize_path(raw_path, cwd),
            project_root=project_root,
            data=data,
            tool_input=tool_input,
        )
        allow()

    allow()


if __name__ == "__main__":
    main()
