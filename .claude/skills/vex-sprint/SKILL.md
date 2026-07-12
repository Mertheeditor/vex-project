---
name: vex-sprint
description: Sprint planning and execution workflow for Vex agent team
disable-model-invocation: false
disallowed-tools: []
---

# Vex Sprint Skill

## Purpose
Structured sprint workflow for the Vex multi-agent team. Ensures consistent planning, execution, and review cycles.

## Sprint Phases

### 1. Sprint Planning (Lead + Architect)
- **Input**: Backlog items, capacity, priorities
- **Output**: Sprint goal, committed stories, task breakdown
- **Architect** creates implementation plans for complex items
- **Lead** assigns to builders with acceptance criteria

### 2. Sprint Execution (Builders + QA)
- **Backend-builder** works in worktree on backend tasks
- **Frontend-builder** works in worktree on frontend tasks
- **QA-engineer** run continuous verification
- **Security-auditor** reviews security-sensitive changes

### 3. Sprint Review (Lead + All)
- Demo working features
- Verify against acceptance criteria
- Collect metrics (velocity, defect rate, cycle time)

### 4. Sprint Retrospective (Lead + All)
- What worked?
- What didn't?
- Process improvements for next sprint

## Agent Handoff Protocol

```
Architect → Plan → Backend-builder/Frontend-builder
    ↓                                    ↓
    → QA-engineer (continuous)           → QA-engineer (final)
    ↓                                    ↓
    → Security-auditor (if needed)       → Lead (merge decision)
```

## Task Format
Each task assigned to builders includes:
```markdown
## Task: [Title]
**Type**: backend | frontend | full-stack
**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
**Architect Plan**: [Link or summary]
**Files to Modify**: [List]
**Worktree**: [backend|frontend]
**Verification**: [QA commands to run]
```

## Sprint Metrics Tracked
- Stories committed vs completed
- Defects found in sprint
- Cycle time per story type
- Worktree merge conflicts (should be 0 with worktrees)
- Security findings

## Escalation
- Blocker > 4 hours → Lead intervenes
- Security critical finding → Immediate, blocks merge
- Architect disagreement → Lead decides