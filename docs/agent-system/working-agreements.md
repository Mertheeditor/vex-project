# Agent Interaction Working Agreements

## Communication Protocol

### Task Handoff Format
When passing work between agents, use this structured format:

```markdown
## HANDOFF: [Task Title]
**From**: [agent-name]
**To**: [agent-name]
**Status**: ready_for_review | blocked | in_progress
**Context**: [link to resume artifacts or key files]
**Summary**: [2-3 sentences what was done]
**Next Steps**: [specific actions for recipient]
**Acceptance Criteria**: [verifiable conditions]
```

### Status Updates
- **Daily** (during long tasks): Brief progress note in handoff format
- **On blocker**: Immediate handoff with `blocked` status
- **On completion**: Handoff with `ready_for_review` + verification evidence

## Agent Boundaries

| Agent | Can Read | Can Write | Worktree |
|-------|----------|-----------|----------|
| vex-lead | All | All (orchestration only) | Main |
| architect | All | Never | Main |
| backend-builder | vex-backend/ | vex-backend/ | Isolated |
| frontend-builder | vex-app/ | vex-app/ | Isolated |
| qa-engineer | All | Test fixtures only* | Main |
| security-auditor | All | Never | Main |
| diff-auditor | All | Never | Main |

*Requires Lead approval

## Conflict Resolution

1. **Scope overlap**: Lead partitions work immediately
2. **Technical disagreement**: Architect decides (design), Lead decides (process)
3. **Security vs Feature**: Security wins; feature redesign required
3. **Quality gate failure**: QA blocks; builder fixes before re-review

## Decision Log
All architectural decisions recorded in `docs/architecture/decisions/` with:
- Title, Date, Author
- Context & Alternatives
- Decision & Rationale
- Consequences

## Escalation Path
```
Builder → Lead → Architect → Security (if applicable)
```
Time limit: 2 hours at each level before auto-escalation.

## Review Cadence
- **Pre-merge**: diff-auditor + security-auditor (fast)
- **Sprint end**: Full audit suite (architect + security + quality + compliance)
- **Release**: All audits + architecture review