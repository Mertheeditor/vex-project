from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services import scheduler_service

from app.routes import (
    ai_provider,
    approvals,
    brain,
    chat,
    computer,
    evolution,
    health,
    memory,
    outputs,
    projects,
    reminders,
    screen,
    seo,
    seo_domain,
    seo_projects,
    shopify,
    site,
    speech,
    task_executions,
    tasks,
    workspace,
)
from app.services.task_execution_runtime import TaskExecutionRuntime

app = FastAPI(title="Vex Backend", version="0.3.0")
app.state.task_execution_runtime = TaskExecutionRuntime()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _start_background_services():
    scheduler_service.start()

@app.get("/")
def root():
    return {"success": True, "message": "Vex backend çalışıyor.", "service": "vex-backend"}

app.include_router(health.router)
app.include_router(brain.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(task_executions.router)
app.include_router(outputs.router)
app.include_router(reminders.router)
app.include_router(workspace.router)
app.include_router(speech.router)
app.include_router(screen.router)
app.include_router(computer.router)
app.include_router(site.router)
app.include_router(seo.router)
app.include_router(seo_domain.router)
app.include_router(seo_projects.router)
app.include_router(shopify.router)
app.include_router(ai_provider.router)
app.include_router(evolution.router)
