---
name: vex-audit
description: Security and code audit procedures for Vex
disable-model-invocation: false
disallowed-tools: []
---

# Vex Audit Skill

## Purpose
Standardized audit procedures for security reviews, code quality checks, and compliance verification.

## Audit Types

### 1. Security Audit (security-auditor agent)
**Scope**: Authentication, authorization, input validation, secrets, injection risks
**Frequency**: Pre-merge for auth/network/fs changes; periodic full audit
**Tools**: Read, Glob, Grep, Bash (scanners)

### 2. Code Quality Audit (diff-auditor agent)
**Scope**: Scope creep, duplication, unused code, complexity, regressions
**Frequency**: Every PR / checkpoint
**Tools**: Read, Glob, Grep, Bash (git diff)

### 3. Architecture Audit (architect agent)
**Scope**: Pattern consistency, dependency direction, layering violations
**Frequency**: Major refactors, new modules
**Tools**: Read, Glob, Grep

### 4. Compliance Audit (qa-engineer agent)
**Scope**: Rules adherence, test coverage, documentation sync
**Frequency**: Sprint review, release prep

## Audit Checklist Template

```markdown
## Audit: [Type] - [Target]
**Auditor**: [agent]
**Date**: [ISO]
**Scope**: [files/directories]

### Findings
| ID | Severity | Category | Location | Description | Evidence | Fix |
|----|----------|----------|----------|-------------|----------|-----|
| 1  | High     | Injection | routes/brain.py:34 | User input in shell | Line 34 | Use args list |

### Summary
- Total: X
- By Severity: Critical=Y, High=Z, Medium=W, Low=V
- By Category: Injection=X, Secrets=Y, Complexity=Z

### Recommendations
1. Immediate: [Critical/High fixes]
2. Short-term: [Medium fixes]
3. Long-term: [Low/refactor]

### Verdict
PASS / CONDITIONAL (fix before merge) / FAIL (block)
```

## Automated Scanners

### Python (Backend)
```bash
pip-audit                 # Vulnerabilities
ruff check --select=S    # Security lints
bandit -r app/           # Static analysis
```

### Rust (Tauri)
```bash
cargo audit              # Vulnerabilities
cargo clippy -- -D warnings
```

### JavaScript (Frontend)
```bash
npm audit                # Vulnerabilities
npm run lint             # Code quality
```

## Integration with Sprint
- **Pre-merge**: security-auditor + diff-auditor (fast)
- **Sprint end**: Full audit suite
- **Release**: All audits + architecture review

## Reporting
All audits produce machine-readable JSON + human-readable Markdown stored in:
```
docs/audits/
├── security/
├── quality/
├── architecture/
└── compliance/
```

## Escalation
- Critical finding → Immediate Lead notification
- Blocks merge until resolved
- Lead decides on risk acceptance (documented)