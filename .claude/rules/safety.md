# Vex Safety Rules

## Security Boundaries

### Secrets Management
- **Never read `.env` files** in agent operations
- **Never log API keys, tokens, passwords** — redact in all outputs
- **Never commit secrets** — `.env` and `.env.*` are gitignored
- `.env.example` contains **only placeholder keys** (empty values)

### File System Access
- **Project root only**: `/Users/mert/Vex` — no traversal outside
- **Forbidden paths**:
  - `~/.ssh/`, `~/.aws/`, `~/.config/gcloud/`
  - Any `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `*.cer`
  - Files containing: `secret`, `credential`, `token`, `password`, `private`
- **Read-only by default**: Agents should read, not write, unless explicitly authorized

### Network Access
- **Localhost only**: `127.0.0.1`, `localhost`, `::1`
- **No external HTTP requests** without explicit user approval
- **Tauri capabilities**: Only declared permissions in `tauri.conf.json`

### Command Execution
- **No `sudo`**, no system package installs
- **No shell redirection to sensitive paths** (`/etc/`, `/usr/`, `/bin/`)
- **Allowed**: `uvicorn`, `npm`, `cargo`, `python`, `git` (read-only operations)

## Input Validation
- **Sanitize all user input** before filesystem/network use
- **Path traversal prevention**: Resolve and verify within project root
- **Size limits**: Max 60KB file reads, max 5MB uploads

## Agent-Specific Restrictions

### Read-Only Agents (architect, security-auditor, diff-auditor)
- **Tools**: `Read`, `Glob`, `Grep`, `Bash` (read-only commands)
- **Forbidden**: `Write`, `Edit`, `NotebookEdit`, `Task` (spawning writers)
- **Can**: Analyze, review, plan, report
- **Cannot**: Modify code, create files, run builds/tests that write output

### Builder Agents (backend-builder, frontend-builder)
- **Worktree isolation mandatory** — never write to main checkout
- **Tools**: `Read`, `Write`, `Edit`, `Bash` (scoped to their domain)
- **Backend-builder**: Only `vex-backend/**`
- **Frontend-builder**: Only `vex-app/**`
- **Cannot**: Modify each other's domains, modify `.claude/`, modify `docs/`

### QA Engineer
- **Default**: Read-only (run tests, lint, type-check)
- **Write access**: Only with explicit approval for test fixtures

## Data Privacy
- **User data in `vex-backend/data/`** — personal, never logged, never committed
- **Screenshots/recordings** — ephemeral, user-controlled deletion
- **No telemetry**, no analytics, no crash reporting to external services

## Incident Response
If secret exposure suspected:
1. **Stop** — do not continue operation
2. **Report** — notify user immediately
3. **Rotate** — user must rotate affected credentials
4. **Audit** — check git history for accidental commits