# Vex Architecture Decisions

## ADR-001 — Main Session Is Vex Lead

- **Status:** accepted
- **Date:** 2026-07-12
- **Decision:** The main Claude Code session is the Lead. A separate Lead
  teammate is not created.
- **Reason:** Prevent duplicate orchestration and uncontrolled agent spawning.

## ADR-002 — Five Specialist Agents

- **Status:** accepted
- **Date:** 2026-07-12
- **Decision:** The active team consists of architect, backend-builder,
  frontend-builder, qa-engineer, and security-auditor.
- **Reason:** Clear ownership and minimum necessary parallelism.

## ADR-003 — Worktree Isolation for Writers

- **Status:** accepted
- **Date:** 2026-07-12
- **Decision:** Backend, frontend, and QA writers operate only in assigned
  `.vex-worktrees/` paths.
- **Reason:** Avoid file collisions and protect the main checkout.

## ADR-004 — Hook-Enforced Boundaries

- **Status:** accepted
- **Date:** 2026-07-12
- **Decision:** PreToolUse enforces write and destructive-command boundaries;
  TaskCompleted enforces verification.
- **Reason:** Instructions alone are not a hard security boundary.

## ADR-005 — Controlled Evolution

- **Status:** accepted
- **Date:** 2026-07-12
- **Decision:** Self-evolution follows proposal → approval → worktree →
  implementation → tests → audit → preview → approval → integration →
  rollback.
- **Reason:** Preserve user control and recoverability.
