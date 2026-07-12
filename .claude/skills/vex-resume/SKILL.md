---
name: vex-resume
description: Context resumption protocol for interrupted work sessions
disable-model-invocation: false
disallowed-tools: []
---

# Vex Resume Protocol

## Purpose
Enable seamless context recovery when a work session is interrupted (timeout, crash, manual pause).

## Triggers
- Session timeout / token limit reached
- Manual pause request
- Agent handoff
- System restart

## Resumption Artifacts
On pause, the active agent MUST produce:

### 1. Task State (`resume_task.json`)
```json
{
  "task_id": "unique-id",
  "objective": "What we're achieving",
  "status": "in_progress | blocked | awaiting_review",
  "progress_pct": 60,
  "completed_steps": ["step1", "step2"],
  "current_step": "step3",
  "blockers": ["reason if any"],
  "context_refs": ["file1.py", "file2.ts"]
}
```

### 2. Git State (`resume_git.json`)
```json
{
  "branch": "current-branch",
  "commit_sha": "abc123",
  "staged_files": ["file1.py"],
  "unstaged_files": ["file2.ts"],
  "untracked_files": ["new_file.py"]
}
```

### 3. Mental Model (`resume_notes.md`)
```markdown
# Resumption Notes

## Key Decisions Made
- Decision 1: rationale
- Decision 2: rationale

## Open Questions
- Question 1
- Question 2

## Next Actions (ordered)
1. Action 1
2. Action 2

## Files Modified (summary)
- file1.py: Changed X to Y because Z
- file2.ts: Added handler for W
```

## Recovery Procedure
On resume, the Lead agent:
1. Reads all three artifacts
2. Validates git state matches `resume_git.json`
3. Briefs the resuming agent with `resume_notes.md`
4. Resuming agent continues from `current_step`

## Automation
- `vex-resume` skill can be invoked with `resume` argument
- Produces standardized artifacts in `.claude/resume/`
- Lead agent uses these for context injection

## Best Practices
- Write resumption artifacts **before** any long operation
- Update progressively (don't wait for end)
- Keep `resume_notes.md` under 200 lines
- Reference files by relative path from repo root