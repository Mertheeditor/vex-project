# Vex Project Roadmap

## Vision
Build a robust, persistent multi-agent development system for the Vex project (React/Tauri frontend + FastAPI backend) with strict boundary enforcement, worktree isolation, and quality gates.

## Milestones

### M1: Agent System Foundation ✅ COMPLETE
- [x] Agent definitions (7 agents)
- [x] Agent registry & working agreements
- [x] Core skills (vex-sprint, vex-resume, vex-audit, minimal-fix)
- [x] Rules (lean-code, visible-edits, frontend, backend, safety, verification)
- [x] Checkpoint branch: `checkpoint/vex-pre-agent-20260712`

### M2: Hook System & Enforcement 🔄 IN PROGRESS
- [ ] PreToolUse hook: pre_tool_guard.py (boundary enforcement)
- [ ] TaskCompleted hook: task_completed.py (quality gate)
- [ ] .claude/settings.json with hook registrations
- [ ] Rename pre-commit → pre-commit.disabled
- [ ] 10 validation test scenarios

### M3: Sprint Memory System 🔄 IN PROGRESS
- [x] ROADMAP.md (this file)
- [ ] QUEUE.md with VEX-001, VEX-002 done, VEX-003 ready
- [ ] CURRENT_STATE.md
- [ ] RUN_LOG.md
- [ ] DECISIONS.md
- [ ] BLOCKERS.md

### M4: Skill Corrections 🔄 IN PROGRESS
- [ ] vex-sprint: enforce 5 specialists, Lead no product code, worktree hashes, test gate, queue-driven, irreversible guard
- [ ] vex-resume: read CURRENT_STATE.md, QUEUE.md, RUN_LOG.md, BLOCKERS.md, recent commits, git status
- [ ] vex-audit: read-only, separate security/QA reports

### M5: Agent Frontmatter Validation 🔄 PENDING
- [ ] builder/QA: isolation:worktree
- [ ] architect/security: permissionMode:plan
- [ ] Lead allowlist: only 5 agents
- [ ] No general-purpose agent

### M6: Integration Testing 🔄 PENDING
- [ ] End-to-end sprint workflow
- [ ] Hook blocking on boundary violations
- [ ] Quality gate on task completion

## Success Criteria
- All hooks pass 10 validation scenarios with correct exit codes
- Sprint memory files update automatically on work
- Agent boundaries enforced without manual intervention
- Zero scope creep between agent domains