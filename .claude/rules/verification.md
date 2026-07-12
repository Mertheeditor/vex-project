# Vex Verification Rules

## Principle
**Every change must be verifiable before claiming success.** No "trust me" — run the checks.

## Backend Verification

### Required Checks (run in `vex-backend/`)
```bash
# 1. Unit tests
./.venv/bin/python -m unittest discover -s app/tests -v

# 2. Syntax & imports
./.venv/bin/python -m py_compile app/**/*.py

# 3. Type check (if mypy configured)
./.venv/bin/mypy app/

# 4. Lint (if ruff configured)
./.venv/bin/ruff check app/

# 5. Health endpoint (if server running)
curl -sf http://127.0.0.1:8000/health
```

### Test Standards
- **All tests pass** — zero failures, zero errors
- **Coverage**: New code paths must have tests
- **No flaky tests** — deterministic, isolated, fast

## Frontend Verification

### Required Checks (run in `vex-app/`)
```bash
# 1. Type check
npm run build  # includes tsc

# 2. Lint
npm run lint  # if configured

# 3. Build production
npm run build

# 4. Dev server smoke test
npm run dev  # verify no console errors
```

### TypeScript Standards
- **Zero `tsc` errors** — strict mode enforced
- **No `any`** — use `unknown` + type guards
- **Exhaustive checks** — `never` in switch defaults

## Tauri/Rust Verification

### Required Checks (run in `vex-app/src-tauri/`)
```bash
# 1. Cargo check (fast, no build)
cargo check

# 2. Clippy lints
cargo clippy -- -D warnings

# 3. Full build (release)
cargo build --release
```

## Git Verification

### Pre-Commit
```bash
# 1. No whitespace errors
git diff --check

# 2. Diff stat within budget
git diff --stat  # ≤ 3 files, ≤ 150 lines changed (unless approved)

# 3. No secrets in diff
git diff | grep -iE 'api[_-]?key|secret|token|password' || echo "clean"
```

### Commit Quality
- **Conventional commits**: `type(scope): subject`
- **Atomic commits** — one logical change per commit
- **No fixup/squash** in main history

## Agent Work Verification

### Read-Only Agents (architect, security-auditor, diff-auditor)
- **Output**: Markdown report with findings
- **Verification**: User reviews report, no auto-merge

### Builder Agents (backend-builder, frontend-builder)
- **Must run verification** in their worktree before reporting done
- **Report format**:
  ```
  ✅ Backend tests: 22 passed
  ✅ Syntax check: clean
  ✅ Type check: clean (tsc)
  ✅ Build: success
  ```

### QA Engineer
- **Runs full verification suite** on merged changes
- **Blocks merge** if any check fails
- **Reports**: Summary table with pass/fail per check

## Definition of Done
A task is **complete** only when:
1. ✅ All relevant verification commands pass
2. ✅ `git diff --check` clean
3. ✅ No new warnings in linters
4. ✅ Tests added for new behavior
5. ✅ Documentation updated if API changed
6. ✅ User acceptance (explicit or via demo)