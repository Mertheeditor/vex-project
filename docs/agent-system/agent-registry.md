# Vex Agent Registry

## Active Agents

| Agent | Role | Model | Tools | Isolation | Status |
|-------|------|-------|-------|-----------|--------|
| vex-lead | Main orchestrator | opus | All | Main checkout | Active |
| architect | Read-only designer | sonnet | Read, Glob, Grep, Bash | Main checkout | Active |
| backend-builder | Backend implementer | sonnet | Read, Write, Edit, Bash, Glob, Grep | **Worktree** | Active |
| frontend-builder | Frontend implementer | sonnet | Read, Write, Edit, Bash, Glob, Grep | **Worktree** | Active |
| qa-engineer | Verification | haiku | Read, Bash, Glob, Grep | Main checkout | Active |
| security-auditor | Security review | haiku | Read, Glob, Grep, Bash | Main checkout | Active |
| diff-auditor | Diff review | haiku | Read, Glob, Grep, Bash | Main checkout | Active |

## Agent Capabilities Matrix

### vex-lead
- Task decomposition & planning
- Agent coordination & delegation
- Progress tracking & synthesis
- Decision making & escalation
- Project state management

### architect
- Codebase exploration & mapping
- Dependency analysis
- Architecture documentation
- Implementation planning
- Trade-off analysis
- Risk assessment

### backend-builder (worktree)
- FastAPI route implementation
- Service layer logic
- Storage layer operations
- Schema definition (Pydantic)
- Unit test creation
- API endpoint development

### frontend-builder (worktree)
- React component development
- TypeScript type definitions
- Tauri integration
- State management (Context/Reducer)
- CSS/module styling
- Build configuration

### qa-engineer
- Unit test execution
- Lint & type-check runs
- Build verification
- Smoke testing
- Regression detection
- Coverage analysis

### security-auditor
- Secret detection
- Input validation review
- Injection vulnerability scan
- Auth/authorization review
- Dependency audit
- Compliance check

### diff-auditor
- Scope creep detection
- Regression risk assessment
- Code quality review
- Unnecessary abstraction flagging
- Test coverage verification

## Invocation Patterns

### Read-Only Agents (no worktree)
```
Task(agent=architect, prompt="...")
Task(agent=security-auditor, prompt="...")
Task(agent=qa-engineer, prompt="...")
Task(agent=diff-auditor, prompt="...")
```

### Builder Agents (require worktree)
```
Task(agent=backend-builder, prompt="...", isolation=worktree)
Task(agent=frontend-builder, prompt="...", isolation=worktree)
```

### Lead Agent (orchestrator)
```
Task(agent=vex-lead, prompt="...")
```

## Model Selection Rationale
- **opus**: Vex Lead - complex reasoning, synthesis, coordination
- **sonnet**: Builders & Architect - balanced capability for implementation/design
- **haiku**: Auditors & QA - fast, cost-effective for verification tasks

## Tool Restrictions Enforcement
- Built into agent definitions (tools list)
- Worktree isolation via `Task` tool `isolation` parameter
- Pre-commit hooks validate boundaries

## Adding New Agents
1. Create `.claude/agents/<name>.md` with frontmatter
2. Add entry to this registry
3. Define capabilities, tools, model, isolation
4. Update working-agreements.md if protocols change
5. Verify via diff-auditor