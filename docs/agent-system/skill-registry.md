# Vex Skill Registry

## Active Skills

| Skill | Path | Model Invocation | Purpose |
|-------|------|------------------|---------|
| vex-sprint | `.claude/skills/vex-sprint/SKILL.md` | Enabled | Sprint planning & execution workflow |
| vex-resume | `.claude/skills/vex-resume/SKILL.md` | Enabled | Context resumption for interrupted sessions |
| vex-audit | `.claude/skills/vex-audit/SKILL.md` | Enabled | Security & code audit procedures |
| minimal-fix | `.claude/skills/minimal-fix/SKILL.md` | **Disabled** (instructions only) | Minimal change bug fixing |

## Skill Usage

### vex-sprint
**When to use**: Starting a new feature, planning a sprint, coordinating multi-agent work
**Trigger**: `/vex-sprint` or Lead agent invocation
**Flow**:
1. Lead creates sprint plan
2. Architect reviews & approves design
3. Builders execute in parallel worktrees
4. QA continuous verification
5. Security audit on completion
6. Lead merges & closes

### vex-resume
**When to use**: Session timeout, manual pause, agent handoff, system restart
**Trigger**: `/vex-resume` or automatic on session restore
**Artifacts produced**:
- `resume_task.json` — Task state
- `resume_git.json` — Git state
- `resume_notes.md` — Mental model

### vex-audit
**When to use**: Pre-merge, sprint review, release prep, security incident
**Trigger**: `/vex-audit [type]` or auditor agent invocation
**Types**: security, quality, architecture, compliance

### minimal-fix
**When to use**: Single bug fix, small scope, known root cause
**Trigger**: `/minimal-fix [issue]`
**Constraints**: Max 3 files, 150 lines, 1 new file, no new deps

## Skill Development Guidelines

### Creating New Skills
1. Create directory: `.claude/skills/<kebab-name>/`
2. Create `SKILL.md` with frontmatter
3. Register in this file
4. Document usage patterns

### Frontmatter Schema
```yaml
---
name: skill-name
description: One-line purpose
disable-model-invocation: false  # true = no model call, just instructions
disallowed-tools: Tool1, Tool2   # blocked while skill active
---
```

### Best Practices
- Keep instructions concise (<500 lines)
- Use `disable-model-invocation: true` for pure checklists/workflows
- Block only truly dangerous tools in `disallowed-tools`
- Document trigger patterns and expected outputs
- Test skill in isolation before registering

## Deprecated/Archived Skills
*None currently*

## Skill Chaining
Skills can invoke other skills via Lead agent:
```
vex-sprint → vex-audit (security) → vex-audit (quality) → vex-resume (if paused)
```

## Versioning
- Skills versioned via git
- Breaking changes require registry update
- Major version bump = new skill directory