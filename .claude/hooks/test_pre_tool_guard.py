#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", "/Users/mert/Vex")).resolve()
HOOK = PROJECT_ROOT / ".claude/hooks/pre_tool_guard.py"


def run_case(name: str, payload: dict, expected: int) -> bool:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
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
    print(f"{status:4} | beklenen={expected} gerçek={result.returncode} | {name}")
    if detail:
        print(f"       {detail}")
    return ok


def payload(agent: str, tool: str, tool_input: dict, cwd: str | None = None) -> dict:
    return {
        "agent_type": agent,
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": cwd or str(PROJECT_ROOT),
    }


def main() -> int:
    wt = PROJECT_ROOT / ".vex-worktrees"
    cases = [
        ("architect Write engellenir", payload("architect", "Write", {"file_path": str(PROJECT_ROOT / "docs/x.md"), "content": "x"}), 2),
        ("security-auditor Edit engellenir", payload("security-auditor", "Edit", {"file_path": str(PROJECT_ROOT / "docs/x.md"), "old_string": "a", "new_string": "b"}), 2),
        ("backend-builder ana checkout engellenir", payload("backend-builder", "Write", {"file_path": str(PROJECT_ROOT / "vex-backend/app/x.py"), "content": "x"}), 2),
        ("backend-builder worktree backend izinli", payload("backend-builder", "Write", {"file_path": str(wt / "backend-builder/vex-backend/app/x.py"), "content": "x"}), 0),
        ("backend-builder worktree frontend engellenir", payload("backend-builder", "Write", {"file_path": str(wt / "backend-builder/vex-app/src/x.ts"), "content": "x"}), 2),
        ("frontend-builder worktree frontend izinli", payload("frontend-builder", "Edit", {"file_path": str(wt / "frontend-builder/vex-app/src/x.tsx"), "old_string": "a", "new_string": "b"}), 0),
        ("frontend-builder worktree backend engellenir", payload("frontend-builder", "Edit", {"file_path": str(wt / "frontend-builder/vex-backend/app/x.py"), "old_string": "a", "new_string": "b"}), 2),
        ("qa-engineer backend test izinli", payload("qa-engineer", "Write", {"file_path": str(wt / "qa-engineer/vex-backend/tests/test_example.py"), "content": "x"}), 0),
        ("qa-engineer production Python engellenir", payload("qa-engineer", "Write", {"file_path": str(wt / "qa-engineer/vex-backend/app/main.py"), "content": "x"}), 2),
        (".env Read engellenir", payload("vex-lead", "Read", {"file_path": str(PROJECT_ROOT / ".env")}), 2),
        ("git reset --hard engellenir", payload("vex-lead", "Bash", {"command": "git reset --hard HEAD"}), 2),
        ("architect git diff --check izinli", payload("architect", "Bash", {"command": "git diff --check"}), 0),
    ]

    passed = sum(run_case(*case) for case in cases)
    print(f"\nSonuç: {passed}/{len(cases)} test geçti.")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
