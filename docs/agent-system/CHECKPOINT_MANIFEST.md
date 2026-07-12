# Agent Infrastructure Checkpoint Manifest

## Include

- `.claude/agents/architect.md`
- `.claude/agents/backend-builder.md`
- `.claude/agents/diff-auditor.md`
- `.claude/agents/frontend-builder.md`
- `.claude/agents/qa-engineer.md`
- `.claude/agents/security-auditor.md`
- `.claude/agents/vex-lead.md`
- `.claude/hooks/pre_tool_guard.py`
- `.claude/hooks/task_completed.py`
- `.claude/hooks/notification_hook.py`
- `.claude/hooks/test_pre_tool_guard.py`
- `.claude/hooks/pre-tool-use.sh`
- `.claude/hooks/pre-commit`
- `.claude/rules/`
- `.claude/skills/`
- `.claude/settings.json`
- `.claude/settings.local.json`
- `docs/agent-system/`

## Exclude

- `.env`
- `.env.*`
- Secret or credential files
- `.venv/`
- `node_modules/`
- `dist/`
- `target/`
- Build and cache directories
- Root-level `*-new.md` preparation files
- Root-level temporary test files
- `patch04_terminal_blogu.sh`
- `patch05_5adim.sh`
- Unrelated frontend/backend product-code changes
- `.claude/backups/`

## Commit Message

`chore(agent-infra): establish safe Vex agent team`
