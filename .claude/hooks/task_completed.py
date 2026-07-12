#!/usr/bin/env python3
"""TaskCompleted quality gate for Vex Agent Teams and isolated worktrees."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def read_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        eprint(f"TaskCompleted: geçersiz JSON: {exc}")
        raise SystemExit(2)


def git_root(candidate: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    return Path(value).resolve() if value else None


def resolve_root(data: dict) -> Path:
    # TaskCompleted provides the actual task cwd. Resolve its Git root first so
    # teammate worktrees are validated independently from the main checkout.
    cwd_value = data.get("cwd")
    if isinstance(cwd_value, str) and cwd_value.strip():
        root = git_root(Path(cwd_value).expanduser().resolve())
        if root is not None:
            return root

    env_value = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_value:
        env_path = Path(env_value).expanduser().resolve()
        root = git_root(env_path)
        if root is not None:
            return root
        return env_path

    script_project = Path(__file__).resolve().parents[2]
    root = git_root(script_project)
    return root if root is not None else script_project


def run(
    args: Sequence[str],
    cwd: Path,
    *,
    label: str,
    timeout: int = 900,
    env: dict[str, str] | None = None,
) -> bool:
    try:
        result = subprocess.run(
            list(args),
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except FileNotFoundError:
        eprint(f"[FAIL] {label}: komut bulunamadı: {args[0]}")
        return False
    except subprocess.TimeoutExpired:
        eprint(f"[FAIL] {label}: {timeout} saniyede tamamlanmadı.")
        return False
    except OSError as exc:
        eprint(f"[FAIL] {label}: {exc}")
        return False

    if result.returncode == 0:
        print(f"[PASS] {label}")
        return True

    eprint(f"[FAIL] {label} (exit {result.returncode})")
    if result.stdout.strip():
        eprint("--- stdout ---")
        eprint(result.stdout.rstrip())
    if result.stderr.strip():
        eprint("--- stderr ---")
        eprint(result.stderr.rstrip())
    return False


def git_output(root: Path, args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git komutu başarısız")
    return result.stdout


def changed_files(root: Path) -> list[str]:
    paths: set[str] = set()
    commands: tuple[Sequence[str], ...] = (
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    )

    for command in commands:
        output = git_output(root, command)
        for line in output.splitlines():
            path = line.strip()
            if path:
                paths.add(path)

    return sorted(paths)


def load_scripts(package_json: Path) -> dict[str, str]:
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"package.json okunamadı: {exc}") from exc

    scripts = payload.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def backend_python(backend: Path) -> Path | None:
    for candidate in (
        backend / ".venv" / "bin" / "python",
        backend / "venv" / "bin" / "python",
    ):
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    data = read_input()
    root = resolve_root(data)

    if git_root(root) is None:
        eprint(f"TaskCompleted: Git repository bulunamadı: {root}")
        return 2

    task_id = str(data.get("task_id") or "unknown")
    subject = str(data.get("task_subject") or "Untitled task")
    print(f"Vex quality gate: {task_id} — {subject}")
    print(f"Repository: {root}")

    try:
        files = changed_files(root)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        eprint(f"TaskCompleted: değişen dosyalar alınamadı: {exc}")
        return 2

    all_ok = True

    all_ok &= run(
        ["git", "-C", str(root), "diff", "--check"],
        root,
        label="git diff --check",
    )
    all_ok &= run(
        ["git", "-C", str(root), "diff", "--cached", "--check"],
        root,
        label="git diff --cached --check",
    )

    backend_changed = any(path.startswith("vex-backend/") for path in files)
    frontend_changed = any(path.startswith("vex-app/") for path in files)
    rust_changed = any(path.startswith("vex-app/src-tauri/") for path in files)

    if backend_changed:
        backend = root / "vex-backend"
        python_bin = backend_python(backend)

        if python_bin is None:
            eprint("[FAIL] Backend değişikliği var fakat .venv/bin/python bulunamadı.")
            all_ok = False
        else:
            python_files = [
                root / path
                for path in files
                if path.startswith("vex-backend/")
                and path.endswith(".py")
                and (root / path).is_file()
            ]

            if python_files:
                all_ok &= run(
                    [str(python_bin), "-m", "py_compile", *map(str, python_files)],
                    backend,
                    label="Backend Python syntax",
                )

            if (backend / "tests").is_dir():
                all_ok &= run(
                    [
                        str(python_bin),
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                        "-v",
                    ],
                    backend,
                    label="Backend unittest",
                    timeout=1200,
                )
            else:
                eprint("[FAIL] vex-backend/tests klasörü bulunamadı.")
                all_ok = False

    if frontend_changed:
        frontend = root / "vex-app"
        package_json = frontend / "package.json"

        if not package_json.is_file():
            eprint("[FAIL] vex-app/package.json bulunamadı.")
            all_ok = False
        else:
            try:
                scripts = load_scripts(package_json)
            except RuntimeError as exc:
                eprint(f"[FAIL] {exc}")
                all_ok = False
                scripts = {}

            if "build" not in scripts:
                eprint("[FAIL] package.json içinde build scripti yok.")
                all_ok = False
            else:
                ordered = ("build", "typecheck", "type-check", "lint", "test")
                npm_env = os.environ.copy()
                npm_env["CI"] = "true"

                for script_name in ordered:
                    if script_name not in scripts:
                        continue
                    all_ok &= run(
                        ["npm", "run", script_name],
                        frontend,
                        label=f"Frontend npm run {script_name}",
                        timeout=1200,
                        env=npm_env,
                    )

    if rust_changed:
        tauri = root / "vex-app" / "src-tauri"
        if (tauri / "Cargo.toml").is_file():
            all_ok &= run(
                ["cargo", "check"],
                tauri,
                label="Tauri cargo check",
                timeout=1200,
            )
        else:
            eprint("[FAIL] src-tauri/Cargo.toml bulunamadı.")
            all_ok = False

    if all_ok:
        print("TaskCompleted quality gate: PASS")
        return 0

    eprint("TaskCompleted quality gate: FAIL")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
