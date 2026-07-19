from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.schemas.agent_kernel import AgentContext, AgentResult, AgentTask
from app.schemas.task_engine import AgentTaskStatus
from app.services.agent_kernel import AgentRegistry, BaseAgent
from app.services.task_execution_runtime import TaskExecutionRuntime, get_task_execution_runtime
from app.storage.entity_store import save_items, upsert_item
from main import app


class CountingAgent(BaseAgent):
    name = "route-agent"

    def __init__(self) -> None:
        self.execution_count = 0

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        self.execution_count += 1
        return AgentResult(
            task_id=task.task_id,
            agent=self.name,
            status="success",
            summary=task.objective,
        )


class TaskExecutionRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.tasks_path = temp_path / "tasks.json"
        self.approvals_path = temp_path / "approvals.json"
        save_items(self.tasks_path, [])
        save_items(self.approvals_path, [])

        self.agent = CountingAgent()
        registry = AgentRegistry()
        registry.register(self.agent)
        self.runtime = TaskExecutionRuntime(agent_registry=registry)
        app.dependency_overrides[get_task_execution_runtime] = lambda: self.runtime

        self.patchers = [
            patch("app.routes.task_executions.TASKS_PATH", self.tasks_path),
            patch("app.routes.task_executions.APPROVALS_PATH", self.approvals_path),
            patch("app.services.task_engine.APPROVALS_PATH", self.approvals_path),
            patch("app.routes.approvals.APPROVALS_PATH", self.approvals_path),
            patch("app.routes.tasks.TASKS_PATH", self.tasks_path),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp_dir.cleanup()

    def add_task(self, task_id: str = "task-1", title: str = "Ship safely") -> dict:
        return upsert_item(
            self.tasks_path,
            {
                "id": task_id,
                "title": title,
                "project_id": "project-1",
                "status": "açık",
                "priority": "yüksek",
                "description": "Use the guarded execution path",
                "notes": ["route-test"],
            },
        )

    def execute(self, task_id: str = "task-1", risk: str = "green", agent_name: str = "route-agent"):
        return self.client.post(
            f"/task-executions/{task_id}/execute",
            json={"agent_name": agent_name, "risk_level": risk, "context": {"source": "test"}},
        )

    def create_approval(self, task_id: str = "task-1", risk: str = "yellow"):
        return self.client.post(
            f"/task-executions/{task_id}/approvals",
            json={"risk_level": risk, "action": f"Approve {risk} execution"},
        )

    def approve(self, approval_id: str):
        return self.client.patch(f"/approvals/{approval_id}/approve")

    def reject(self, approval_id: str):
        return self.client.patch(f"/approvals/{approval_id}/reject")

    def prepare_approval_task(self, risk: str = "yellow") -> str:
        self.add_task()
        execute_response = self.execute(risk=risk)
        self.assertEqual(execute_response.status_code, 202)
        self.assertEqual(execute_response.json()["outcome"], "approval_required")
        approval_response = self.create_approval(risk=risk)
        self.assertEqual(approval_response.status_code, 200)
        return approval_response.json()["id"]

    def test_unknown_crud_task_execute_returns_404(self) -> None:
        response = self.execute(task_id="missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.runtime.engine.list_tasks(), [])

    def test_crud_task_bridges_to_same_engine_id_and_fields(self) -> None:
        self.add_task(task_id="crud-id", title="Canonical title")
        response = self.execute(task_id="crud-id")
        self.assertEqual(response.status_code, 202)
        record = self.runtime.engine.get_task("crud-id")
        self.assertEqual(record.task_id, "crud-id")
        self.assertEqual(record.objective, "Canonical title")
        self.assertEqual(record.metadata["project_id"], "project-1")
        self.assertEqual(record.metadata["description"], "Use the guarded execution path")

    def test_duplicate_execute_keeps_one_engine_id_and_one_agent_execution(self) -> None:
        self.add_task()
        first = self.execute()
        second = self.execute()
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 409)
        self.assertEqual([record.task_id for record in self.runtime.engine.list_tasks()], ["task-1"])
        self.assertEqual(self.agent.execution_count, 1)

    def test_task_approval_payload_uses_exact_task_id(self) -> None:
        self.add_task(task_id="identity-task")
        response = self.create_approval(task_id="identity-task")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["task_id"], "identity-task")
        self.assertEqual(data["payload"]["task_id"], "identity-task")

    def test_green_execution_starts_with_registered_agent(self) -> None:
        self.add_task()
        response = self.execute()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["outcome"], "started")
        self.assertEqual(response.json()["task"]["status"], "running")
        self.assertEqual(self.agent.execution_count, 1)

    def test_unknown_risk_is_validation_error_and_never_registers_task(self) -> None:
        self.add_task()
        response = self.execute(risk="purple")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.runtime.engine.list_tasks(), [])
        self.assertEqual(self.agent.execution_count, 0)

    def test_missing_risk_is_validation_error_and_never_registers_task(self) -> None:
        self.add_task()
        response = self.client.post(
            "/task-executions/task-1/execute",
            json={"agent_name": "route-agent"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.runtime.engine.list_tasks(), [])

    def test_black_risk_is_forbidden_and_never_reaches_agent(self) -> None:
        self.add_task()
        response = self.execute(risk="black")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.agent.execution_count, 0)
        self.assertEqual(self.runtime.engine.get_task("task-1").status, AgentTaskStatus.WAITING_APPROVAL)

    def test_missing_agent_returns_typed_unavailable_without_fake_start(self) -> None:
        self.add_task()
        response = self.execute(agent_name="missing-agent")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["outcome"], "agent_unavailable")
        self.assertEqual(response.json()["task"]["status"], "waiting_approval")
        self.assertEqual(self.agent.execution_count, 0)

    def test_status_reads_typed_execution_record(self) -> None:
        self.add_task()
        self.execute()
        response = self.client.get("/task-executions/task-1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["task_id"], "task-1")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["metadata"]["risk_level"], "green")
        self.assertNotIn("request_context", data["metadata"])

    def test_unknown_execution_status_returns_404(self) -> None:
        response = self.client.get("/task-executions/missing")
        self.assertEqual(response.status_code, 404)

    def test_running_task_can_be_cancelled_without_deleting_crud_task(self) -> None:
        self.add_task()
        self.execute()
        response = self.client.post("/task-executions/task-1/cancel")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancelled")
        tasks = self.client.get("/tasks").json()
        self.assertEqual([task["id"] for task in tasks], ["task-1"])

    def test_terminal_task_cancel_returns_conflict(self) -> None:
        self.add_task()
        self.execute()
        self.runtime.engine.transition("task-1", AgentTaskStatus.VERIFYING)
        self.runtime.engine.transition("task-1", AgentTaskStatus.COMPLETED)
        response = self.client.post("/task-executions/task-1/cancel")
        self.assertEqual(response.status_code, 409)

    def test_unknown_task_cancel_returns_404(self) -> None:
        response = self.client.post("/task-executions/missing/cancel")
        self.assertEqual(response.status_code, 404)

    def test_yellow_and_red_create_pending_task_bound_approvals(self) -> None:
        for task_id, risk in (("yellow-task", "yellow"), ("red-task", "red")):
            self.add_task(task_id=task_id)
            response = self.create_approval(task_id=task_id, risk=risk)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "bekliyor")
            self.assertEqual(response.json()["risk_level"], risk)
            self.assertEqual(response.json()["payload"]["task_id"], task_id)

    def test_task_approval_list_filters_out_other_tasks(self) -> None:
        self.add_task(task_id="first")
        self.add_task(task_id="second")
        first = self.create_approval(task_id="first").json()
        self.create_approval(task_id="second", risk="red")
        response = self.client.get("/task-executions/first/approvals")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([approval["id"] for approval in response.json()], [first["id"]])

    def test_task_approval_list_accepts_explicit_task_id_link(self) -> None:
        self.add_task()
        upsert_item(
            self.approvals_path,
            {
                "id": "explicit-link",
                "task_id": "task-1",
                "title": "Explicit link",
                "project_id": "project-1",
                "action_type": "task_execution",
                "risk_level": "yellow",
                "status": "bekliyor",
                "description": "Explicit link",
                "payload": {},
                "notes": [],
            },
        )
        response = self.client.get("/task-executions/task-1/approvals")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["payload"]["task_id"], "task-1")

    def test_black_approval_creation_and_existing_black_approval_are_blocked(self) -> None:
        self.add_task()
        create_response = self.create_approval(risk="black")
        self.assertEqual(create_response.status_code, 403)
        black = upsert_item(
            self.approvals_path,
            {
                "id": "black-approval",
                "status": "bekliyor",
                "risk_level": "black",
                "payload": {"task_id": "task-1"},
            },
        )
        approve_response = self.approve(black["id"])
        self.assertEqual(approve_response.status_code, 409)

    def test_rejected_approval_blocks_execute(self) -> None:
        self.add_task()
        approval = self.create_approval().json()
        self.assertEqual(self.reject(approval["id"]).status_code, 200)
        response = self.execute(risk="yellow")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.agent.execution_count, 0)

    def test_wrong_task_approval_cannot_resume(self) -> None:
        self.prepare_approval_task()
        self.add_task(task_id="other-task")
        other = self.create_approval(task_id="other-task").json()
        self.approve(other["id"])
        response = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": other["id"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.agent.execution_count, 0)

    def test_risk_mismatch_approval_cannot_resume(self) -> None:
        self.add_task()
        self.execute(risk="yellow")
        mismatch = upsert_item(
            self.approvals_path,
            {
                "id": "mismatch",
                "task_id": "task-1",
                "title": "Wrong risk",
                "project_id": "project-1",
                "action_type": "task_execution",
                "risk_level": "red",
                "status": "onaylandı",
                "description": "Wrong risk",
                "payload": {"task_id": "task-1"},
                "notes": [],
            },
        )
        response = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": mismatch["id"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.agent.execution_count, 0)

    def test_approved_matching_approval_resumes_execution(self) -> None:
        approval_id = self.prepare_approval_task(risk="red")
        approved = self.approve(approval_id)
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["approval"]["payload"]["task_id"], "task-1")
        response = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": approval_id},
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["outcome"], "started")
        self.assertEqual(self.agent.execution_count, 1)

    def test_pending_approval_cannot_resume(self) -> None:
        approval_id = self.prepare_approval_task()
        response = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": approval_id},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.agent.execution_count, 0)

    def test_rejected_approval_cannot_resume(self) -> None:
        approval_id = self.prepare_approval_task()
        self.reject(approval_id)
        response = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": approval_id},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.agent.execution_count, 0)

    def test_unknown_approval_id_cannot_resume(self) -> None:
        self.add_task()
        self.execute(risk="yellow")
        response = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": "missing"},
        )
        self.assertEqual(response.status_code, 404)

    def test_duplicate_resume_does_not_execute_agent_twice(self) -> None:
        approval_id = self.prepare_approval_task()
        self.approve(approval_id)
        first = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": approval_id},
        )
        second = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": approval_id},
        )
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.agent.execution_count, 1)

    def test_black_risk_cannot_be_bypassed_by_resume(self) -> None:
        self.add_task()
        self.assertEqual(self.execute(risk="black").status_code, 403)
        black = upsert_item(
            self.approvals_path,
            {
                "id": "black-resume",
                "task_id": "task-1",
                "title": "Unsafe",
                "project_id": "project-1",
                "action_type": "task_execution",
                "risk_level": "black",
                "status": "onaylandı",
                "description": "Unsafe",
                "payload": {"task_id": "task-1"},
                "notes": [],
            },
        )
        response = self.client.post(
            "/task-executions/task-1/resume",
            json={"approval_id": black["id"]},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.agent.execution_count, 0)

    def test_existing_tasks_and_approvals_endpoints_keep_no_filter_behavior(self) -> None:
        self.add_task()
        approval = self.create_approval().json()
        tasks_response = self.client.get("/tasks")
        approvals_response = self.client.get("/approvals")
        self.assertEqual(tasks_response.status_code, 200)
        self.assertEqual(approvals_response.status_code, 200)
        self.assertEqual(tasks_response.json()[0]["id"], "task-1")
        self.assertEqual(approvals_response.json()[0]["id"], approval["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
