#!/usr/bin/env python3
"""Vex PreToolUse security guard.

Writer agents may write only inside a linked Git worktree belonging to this
repository. The worktree location may be Claude-managed (.claude/worktrees),
manually managed (.vex-worktrees), or any other linked Git worktree.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
READ_ONLY_AGENTS = {"architect", "security-auditor", "diff-auditor"}
WRITER_AGENTS = {"backend-builder", "frontend-builder", "qa-engineer"}

DANGEROUS_BASH_PATTERNS = (
    (re.compile(r"(^|[\s;&|])sudo(?:\s|$)", re.IGNORECASE), "sudo komutları yasak"),
    (
        re.compile(
            r"\brm\s+-[^\n]*r[^\n]*f\b|\brm\s+-[^\n]*f[^\n]*r\b",
            re.IGNORECASE,
        ),
        "rm -rf yasak",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
        "git reset --hard yasak",
    ),
    (
        re.compile(
            r"\bgit\s+clean\s+-[^\s]*f[^\s]*d|\bgit\s+clean\s+-[^\s]*d[^\s]*f",
            re.IGNORECASE,
        ),
        "git clean -fd yasak",
    ),
    (
        re.compile(r"\bgit\s+push\b", re.IGNORECASE),
        "git push kullanıcı onayı olmadan yasak",
    ),
    (
        re.compile(
            r"\bgit\s+(?:merge|rebase|cherry-pick|stash|switch|checkout)\b",
            re.IGNORECASE,
        ),
        "entegrasyon veya branch değiştirme komutu kullanıcı onayı olmadan yasak",
    ),
    (
        re.compile(r"\bgit\s+branch\s+-D\b", re.IGNORECASE),
        "zorla branch silme yasak",
    ),
    (
        re.compile(r"\bgit\s+worktree\s+remove\b", re.IGNORECASE),
        "worktree kaldırma kullanıcı onayı olmadan yasak",
    ),
    (
        re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba)?sh\b", re.IGNORECASE),
        "uzaktan script pipe ile çalıştırma yasak",
    ),
)

READ_ONLY_MUTATION_PATTERNS = (
    (
        re.compile(r"(^|[\s;&|])(?:>|>>)(?!&)", re.IGNORECASE),
        "çıktı yönlendirmesi dosya değiştirebilir",
    ),
    (
        re.compile(r"(^|[\s;&|])tee(?:\s|$)", re.IGNORECASE),
        "tee dosya değiştirebilir",
    ),
    (
        re.compile(
            r"(^|[\s;&|])(?:mv|cp|rm|touch|mkdir|chmod)(?:\s|$)",
            re.IGNORECASE,
        ),
        "salt okunur ajan dosya değiştiremez",
    ),
    (
        re.compile(
            r"\bgit\s+(?:add|commit|checkout|switch|merge|rebase|cherry-pick)\b",
            re.IGNORECASE,
        ),
        "salt okunur ajan Git durumunu değiştiremez",
    ),
)

SENSITIVE_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
}
SENSITIVE_NAMES = {
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
    "service-account.json",
    "service_account.json",
}
SENSITIVE_PART_RE = re.compile(
    r"(?:^|[._-])"
    r"(secret|secrets|credential|credentials|private[_-]?key|"
    r"access[_-]?token|refresh[_-]?token)"
    r"(?:$|[._-])",
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


def run_git(cwd: Path, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    return value or None


def git_top_level(cwd: Path) -> Optional[Path]:
    value = run_git(cwd, "rev-parse", "--show-toplevel")
    return Path(value).resolve(strict=False) if value else None


def git_common_dir(cwd: Path) -> Optional[Path]:
    value = run_git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if value:
        return Path(value).resolve(strict=False)

    value = run_git(cwd, "rev-parse", "--git-common-dir")
    if not value:
        return None

    path = Path(value)
    if not path.is_absolute():
        path = cwd / path
    return path.resolve(strict=False)


def canonical_main_root(cwd: Path) -> Optional[Path]:
    common = git_common_dir(cwd)
    if common is None:
        return None

    if common.name == ".git":
        return common.parent.resolve(strict=False)

    return None


def get_agent_type(data: Mapping[str, Any]) -> str:
    value = data.get("agent_type") or data.get("agent_name")
    if isinstance(value, str) and value.strip():
        return value.strip()

    env_value = os.environ.get("CLAUDE_AGENT_NAME")
    if env_value:
        return env_value.strip()

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

    if rel.startswith(
        (
            "vex-app/src/test/",
            "vex-app/src/tests/",
            "vex-app/src/__tests__/",
        )
    ):
        return True

    return rel.startswith("vex-app/src/") and lower.endswith(
        (
            ".test.ts",
            ".test.tsx",
            ".spec.ts",
            ".spec.tsx",
            ".test.js",
            ".test.jsx",
            ".spec.js",
            ".spec.jsx",
        )
    )


def resolve_context(data: Mapping[str, Any]) -> tuple[Path, Path]:
    cwd_value = data.get("cwd")
    cwd = (
        Path(cwd_value).expanduser().resolve(strict=False)
        if isinstance(cwd_value, str) and cwd_value.strip()
        else Path.cwd().resolve(strict=False)
    )

    active_root = git_top_level(cwd)
    if active_root is None:
        env_root = os.environ.get("CLAUDE_PROJECT_DIR")
        if env_root:
            active_root = git_top_level(
                Path(env_root).expanduser().resolve(strict=False)
            )

    if active_root is None:
        deny(f"Git çalışma kökü belirlenemedi: {cwd}")

    main_root = canonical_main_root(active_root)
    if main_root is None:
        deny(f"Git ortak repository kökü belirlenemedi: {active_root}")

    return active_root, main_root


def enforce_writer_worktree(
    agent_type: str,
    active_root: Path,
    main_root: Path,
) -> None:
    if active_root == main_root:
        deny(
            f"{agent_type} ana checkout üzerinde çalışamaz; "
            "isolation: worktree gereklidir"
        )


def enforce_write_path(
    agent_type: str,
    path: Path,
    active_root: Path,
    main_root: Path,
) -> None:
    if is_sensitive_path(path):
        deny(f"hassas dosyaya erişim yasak: {path}")

    if agent_type in READ_ONLY_AGENTS:
        deny(f"{agent_type} salt okunur; {path} değiştirilemez")

    if agent_type in WRITER_AGENTS:
        enforce_writer_worktree(agent_type, active_root, main_root)

        if not is_relative_to(path, active_root):
            deny(
                f"{agent_type} yalnızca aktif worktree içinde yazabilir: "
                f"{active_root}"
            )

        relative = path.relative_to(active_root)

        if agent_type == "qa-engineer":
            if not allowed_qa_path(relative):
                deny(f"QA yalnızca test alanlarına yazabilir: {relative}")
        elif not allowed_builder_path(agent_type, relative):
            deny(f"{agent_type} yanlış alana yazmaya çalıştı: {relative}")

        return

    if agent_type == "vex-lead":
        if not is_relative_to(path, main_root):
            deny(f"Vex Lead repository dışına yazamaz: {path}")

        relative = path.relative_to(main_root).as_posix()

        if relative == ".claude" or relative.startswith(".claude/"):
            return

        if (
            relative == "docs/agent-system"
            or relative.startswith("docs/agent-system/")
        ):
            return

        deny(f"Vex Lead ana checkout ürün koduna yazamaz: {relative}")

    deny(f"tanımsız ajan yazma yetkisine sahip değil: {agent_type}")


def main() -> None:
    data = load_input()
    tool_name = str(data.get("tool_name") or "")
    tool_input = get_tool_input(data)
    agent_type = get_agent_type(data)
    active_root, main_root = resolve_context(data)

    cwd_value = data.get("cwd")
    cwd = (
        Path(cwd_value).expanduser().resolve(strict=False)
        if isinstance(cwd_value, str) and cwd_value.strip()
        else active_root
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

        if agent_type in WRITER_AGENTS:
            enforce_writer_worktree(agent_type, active_root, main_root)

        allow()

    if tool_name in WRITE_TOOLS:
        if not raw_path:
            deny(f"{tool_name} için file_path/path bulunamadı")

        enforce_write_path(
            agent_type=agent_type,
            path=normalize_path(raw_path, cwd),
            active_root=active_root,
            main_root=main_root,
        )
        allow()

    allow()


if __name__ == "__main__":
    main()
