---
name: backend
description: Backend development rules for vex-backend (FastAPI, Python 3.12+, Uvicorn)
alwaysApply: false
---

# Vex Backend Development Rules

## Tech Stack
- Python 3.12+
- FastAPI with async/await
- Uvicorn ASGI server
- Pydantic v2 for validation
- Standard library + minimal deps (see `requirements.txt`)

## Project Structure
```
vex-backend/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── core/                # Configuration, paths, optional imports
│   ├── routes/              # HTTP route handlers (thin)
│   ├── services/            # Business logic (thick)
│   ├── storage/             # JSON file storage layer
│   ├── schemas/             # Pydantic models (request/response)
│   └── tests/               # Unit tests
├── data/                    # Runtime data (gitignored)
├── .venv/                   # Virtual env (gitignored)
└── requirements.txt
```

## Architecture Principles
- **Routes → Services → Storage** (no direct storage access in routes)
- **Services are stateless** — inject config via `Depends` or constructor
- **Async by default** — use `async def` for I/O bound operations
- **Sync for CPU-bound** — use `run_in_executor` if needed

## Code Style
- **Type hints everywhere** — parameters, returns, attributes
- **Pydantic models** for all request/response bodies
- **Descriptive names**: `create_reminder`, not `cr_rem`
- **Docstrings** for public functions/classes (Google style)
- **Max line length**: 100 chars (ruff default)

## Error Handling
- Custom exceptions in `app/core/exceptions.py`
- FastAPI exception handlers for consistent JSON errors
- **Never expose stack traces** to clients
- Log errors with context (structured logging)

## Configuration
- `.env` for secrets (never committed)
- `.env.example` as template (committed)
- `app.core.config.Settings` via `pydantic-settings`
- Access via `Depends(get_settings)`

## Storage Layer
- `app/storage/json_store.py` — atomic read/write with file locks
- `app/storage/entity_store.py` — generic CRUD helpers
- Data files in `data/` (gitignored)
- **No SQLite/PostgreSQL** without architecture review

## Testing
```bash
# Unit tests
./.venv/bin/python -m unittest discover -s app/tests -v

# Syntax/import check
./.venv/bin/python -m py_compile app/**/*.py

# Lint (if ruff configured)
ruff check app/
```

## Prohibited Patterns
- ❌ Global mutable state in modules
- ❌ Blocking I/O in async functions (use `aiofiles`, `httpx`)
- ❌ `print()` in production code (use `logging`)
- ❌ Raw SQL / ORM without approval
- ❌ `**kwargs` in public APIs
- ❌ Circular imports (enforce route → service → storage direction)