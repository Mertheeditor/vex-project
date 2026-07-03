from __future__ import annotations

from pathlib import Path
from app.core.config import BASE_DIR

MEMORY_PATH = BASE_DIR / "memory.json"
REMINDERS_PATH = BASE_DIR / "reminders.json"
PROJECTS_PATH = BASE_DIR / "projects.json"
TASKS_PATH = BASE_DIR / "tasks.json"
APPROVALS_PATH = BASE_DIR / "approvals.json"
ACTIVE_PROJECT_PATH = BASE_DIR / "active_project.json"
ACTIVE_TASK_PATH = BASE_DIR / "active_task.json"
OUTPUTS_PATH = BASE_DIR / "outputs.json"
PREFERENCES_PATH = BASE_DIR / "preferences.json"
SCREENSHOTS_PATH = BASE_DIR / "screenshots"
COMPUTER_LOGS_PATH = BASE_DIR / "computer_logs.json"
EVOLUTION_LOGS_PATH = BASE_DIR / "evolution_logs.json"
EVOLUTION_PENDING_PATH = BASE_DIR / "evolution_pending_actions.json"
