#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().with_name("pre_tool_guard.py")


def git(cwd: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def run_case(
    name: str,
    payload: dict,
    expected: int,
    main_root: Path,
) -> bool:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(main_root)

    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    ok = result.returncode == expected
    status = "PASS" if ok else "FAIL"
    detail = result.stderr.strip().splitlines()[0] if result.stderr.strip() else ""

    print(
        f"{status:4} | beklenen={expected} "
        f"gerçek={result.returncode} | {name}"
    )
    if detail:
        print(f"       {detail}")

    return ok


def payload(
    agent: str,
    tool: str,
    tool_input: dict,
    cwd: Path,
) -> dict:
    return {
        "agent_type": agent,
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": str(cwd),
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vex-guard-test-") as temp:
        main_root = Path(temp) / "repo"
        worktree = main_root / ".claude" / "worktrees" / "writer"

        main_root.mkdir(parents=True)

        git(main_root, "init", "-q")
        git(main_root, "config", "user.name", "Vex Guard Test")
        git(main_root, "config", "user.email", "vex-guard@example.invalid")

        for directory in (
            main_root / ".claude",
            main_root / "vex-backend" / "app",
            main_root / "vex-backend" / "tests",
            main_root / "vex-app" / "src",
            main_root / "docs" / "agent-system",
        ):
            directory.mkdir(parents=True, exist_ok=True)

        (main_root / "README.md").write_text("test\n", encoding="utf-8")
        git(main_root, "add", ".")
        git(main_root, "commit", "-qm", "baseline")
        git(
            main_root,
            "worktree",
            "add",
            "-q",
            "-b",
            "guard-test-worktree",
            str(worktree),
            "HEAD",
        )

        cases = [
            (
                "architect Write engellenir",
                payload(
                    "architect",
                    "Write",
                    {
                        "file_path": str(main_root / "docs" / "x.md"),
                        "content": "x",
                    },
                    main_root,
                ),
                2,
            ),
            (
                "security-auditor Edit engellenir",
                payload(
                    "security-auditor",
                    "Edit",
                    {
                        "file_path": str(main_root / "docs" / "x.md"),
                        "old_string": "a",
                        "new_string": "b",
                    },
                    main_root,
                ),
                2,
            ),
            (
                "backend-builder ana checkout engellenir",
                payload(
                    "backend-builder",
                    "Write",
                    {
                        "file_path": str(
                            main_root / "vex-backend" / "app" / "x.py"
                        ),
                        "content": "x",
                    },
                    main_root,
                ),
                2,
            ),
            (
                "backend-builder Claude worktree backend izinli",
                payload(
                    "backend-builder",
                    "Write",
                    {
                        "file_path": str(
                            worktree / "vex-backend" / "app" / "x.py"
                        ),
                        "content": "x",
                    },
                    worktree,
                ),
                0,
            ),
            (
                "backend-builder worktree frontend engellenir",
                payload(
                    "backend-builder",
                    "Write",
                    {
                        "file_path": str(
                            worktree / "vex-app" / "src" / "x.ts"
                        ),
                        "content": "x",
                    },
                    worktree,
                ),
                2,
            ),
            (
                "frontend-builder Claude worktree frontend izinli",
                payload(
                    "frontend-builder",
                    "Edit",
                    {
                        "file_path": str(
                            worktree / "vex-app" / "src" / "x.tsx"
                        ),
                        "old_string": "a",
                        "new_string": "b",
                    },
                    worktree,
                ),
                0,
            ),
            (
                "frontend-builder worktree backend engellenir",
                payload(
                    "frontend-builder",
                    "Edit",
                    {
                        "file_path": str(
                            worktree / "vex-backend" / "app" / "x.py"
                        ),
                        "old_string": "a",
                        "new_string": "b",
                    },
                    worktree,
                ),
                2,
            ),
            (
                "qa-engineer backend test izinli",
                payload(
                    "qa-engineer",
                    "Write",
                    {
                        "file_path": str(
                            worktree
                            / "vex-backend"
                            / "tests"
                            / "test_example.py"
                        ),
                        "content": "x",
                    },
                    worktree,
                ),
                0,
            ),
            (
                "qa-engineer production Python engellenir",
                payload(
                    "qa-engineer",
                    "Write",
                    {
                        "file_path": str(
                            worktree / "vex-backend" / "app" / "main.py"
                        ),
                        "content": "x",
                    },
                    worktree,
                ),
                2,
            ),
            (
                ".env Read engellenir",
                payload(
                    "vex-lead",
                    "Read",
                    {"file_path": str(main_root / ".env")},
                    main_root,
                ),
                2,
            ),
            (
                "git reset --hard engellenir",
                payload(
                    "vex-lead",
                    "Bash",
                    {"command": "git reset --hard HEAD"},
                    main_root,
                ),
                2,
            ),
            (
                "git push engellenir",
                payload(
                    "backend-builder",
                    "Bash",
                    {"command": "git push origin test"},
                    worktree,
                ),
                2,
            ),
            (
                "writer ana checkout Bash engellenir",
                payload(
                    "backend-builder",
                    "Bash",
                    {"command": "git status --short"},
                    main_root,
                ),
                2,
            ),
            (
                "writer worktree test komutu izinli",
                payload(
                    "backend-builder",
                    "Bash",
                    {"command": "python3 -m unittest discover -s tests -v"},
                    worktree,
                ),
                0,
            ),
            (
                "architect git diff --check izinli",
                payload(
                    "architect",
                    "Bash",
                    {"command": "git diff --check"},
                    main_root,
                ),
                0,
            ),
        ]

        passed = sum(
            run_case(name, case_payload, expected, main_root)
            for name, case_payload, expected in cases
        )

        print(f"\nSonuç: {passed}/{len(cases)} test geçti.")
        return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
