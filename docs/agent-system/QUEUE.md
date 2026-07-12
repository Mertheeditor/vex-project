# Vex Task Queue

## Format
```
VEX-XXX | STATUS | PRIORITY | AGENT | DESCRIPTION
```
- **STATUS**: BACKLOG | READY | IN_PROGRESS | DONE | BLOCKED
- **PRIORITY**: P0 (critical) | P1 (high) | P2 (medium) | P3 (low)
- **AGENT**: lead | architect | backend-builder | frontend-builder | qa-engineer | security-auditor | diff-auditor

---

## Completed Tasks

### VEX-001 | DONE | P0 | lead/architect/builders
**Agent System Foundation**
- Created 7 agent definitions with proper frontmatter
- Established agent registry & working agreements
- Defined skills: vex-sprint, vex-resume, vex-audit, minimal-fix
- Created all 6 rule files
- **Verification**: All agents documented in agent-registry.md

### VEX-002 | DONE | P0 | lead
**Repository Checkpoint**
- Cleaned repo (removed temp scripts, test files)
- Fixed .gitignore (.env.example rule)
- Created checkpoint branch `checkpoint/vex-pre-agent-20260712` at commit b90dabe
- Verified: 22 backend tests pass, npm build succeeds, cargo check clean
- **Verification**: git diff clean, no secrets, all builds pass

---

## Ready Tasks (Prioritized)

### VEX-003 | READY | P0 | lead/architect
**Hook System Implementation**
- Create pre_tool_guard.py (boundary enforcement for all agents)
- Create task_completed.py (quality gate on task completion)
- Create .claude/settings.json with PreToolUse + TaskCompleted hooks
- Rename pre-commit → pre-commit.disabled with explanation
- Run 10 validation scenarios, document exit codes
- **Dependencies**: None
- **Assigned**: TBD

### VEX-004 | READY | P0 | lead
**Sprint Memory System**
- Create/verify CURRENT_STATE.md from git status + active work
- Create/verify RUN_LOG.md with session history
- Create/verify DECISIONS.md with architectural decisions
- Create/verify BLOCKERS.md (currently empty)
- Ensure auto-update mechanism on session resume
- **Dependencies**: VEX-003 (hooks trigger updates)
- **Assigned**: TBD

### VEX-005 | READY | P0 | lead
**Skill Corrections**
- Fix vex-sprint: enforce 5 specialists, Lead no product code, worktree hashes, test gate, queue-driven, irreversible guard
- Fix vex-resume: read CURRENT_STATE.md, QUEUE.md, RUN_LOG.md, BLOCKERS.md, recent commits, git status
- Fix vex-audit: read-only, separate security vs QA reports
- **Dependencies**: VEX-003, VEX-004
- **Assigned**: TBD

### VEX-006 | READY | P0 | lead/architect
**Agent Frontmatter Validation**
- Verify backend-builder & frontend-builder: isolation:worktree
- Verify architect & security-auditor: permissionMode:plan
- Verify vex-lead allowlist: only 5 specialist agents
- Verify NO general-purpose agent in allowlist
- **Dependencies**: VEX-005
- **Assigned**: TBD

### VEX-007 | READY | P1 | qa-engineer
**Integration Test Suite**
- Design 10 hook validation scenarios
- Run scenarios, capture exit codes
- Document pass/fail matrix
- Verify boundary enforcement works for all agent types
- **Dependencies**: VEX-003
- **Assigned**: TBD

---

## Backlog

### VEX-008 | BACKLOG | P2 | architect
**Agent Communication Protocol Enhancement**
- Structured handoff templates with required fields
- Automated handoff artifact generation
- Cross-agent context sharing

### VEX-009 | BACKLOG | P2 | backend-builder
**Backend Agent Kernel Hardening**
- Review agent_kernel.py for boundary compliance
- Add input validation to all public methods
- Stress test concurrent agent execution

### VEX-010 | BACKLOG | P3 | frontend-builder
**Frontend DevTools Integration**
- Tauri devtools integration
- Hot reload optimization
- Performance profiling setup

---

## Current Sprint Status
**Sprint**: Foundation Complete → Hook System In Progress
**Started**: 2026-07-12
**Goal**: Complete hook system + sprint memory + skill corrections
**Blocked By**: None