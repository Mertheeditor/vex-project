from __future__ import annotations

import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from app.schemas.agent_kernel import AgentContext, AgentResult, AgentTask
from app.schemas.task_engine import AgentTaskStatus
from app.services.agent_kernel import BaseAgent
from app.services.task_engine import TaskEngine
from app.storage.entity_store import save_items, upsert_item
from app.routes import approvals


class CountingAgent(BaseAgent):
    name = "counting-agent"

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


class ApprovalGateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.approvals_path = self.temp_path / "approvals.json"
        save_items(self.approvals_path, [])

    def tearDown(self):
        self.temp_dir.cleanup()

    def _patch_approvals_path(self):
        return [
            patch("app.routes.approvals.APPROVALS_PATH", self.approvals_path),
            patch("app.services.task_engine.APPROVALS_PATH", self.approvals_path),
        ]

    def _run_with_patches(self):
        stack = ExitStack()
        for p in self._patch_approvals_path():
            stack.enter_context(p)
        return stack

    def _prepare_waiting_task(self, task_id: str, risk_level: str | None) -> TaskEngine:
        engine = TaskEngine()
        context = {} if risk_level is None else {"risk_level": risk_level}
        task = AgentTask(
            task_id=task_id,
            objective=f"{task_id} objective",
            context=context,
            requested_by="test",
        )
        engine.create_task(task)
        engine.transition(task_id, AgentTaskStatus.PLANNING)
        engine.transition(task_id, AgentTaskStatus.WAITING_APPROVAL)
        return engine

    async def _execute_with_agent(self, engine: TaskEngine, task_id: str) -> tuple[AgentResult, CountingAgent]:
        agent = CountingAgent()
        result = await engine.execute_task(task_id, agent, AgentContext())
        return result, agent

    # ---- Approval Endpoint Tests ----

    def test_1_green_approval_not_required_for_gate(self):
        with self._run_with_patches():
            engine = TaskEngine()
            task = AgentTask(task_id="t1", objective="green task", context={"risk_level": "green"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t1", AgentTaskStatus.PLANNING)
            engine.transition("t1", AgentTaskStatus.WAITING_APPROVAL)
            record = engine.transition("t1", AgentTaskStatus.RUNNING)
            self.assertEqual(record.status, AgentTaskStatus.RUNNING)

    def test_2_yellow_rejected_without_approval(self):
        with self._run_with_patches():
            engine = TaskEngine()
            task = AgentTask(task_id="t2", objective="yellow task", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t2", AgentTaskStatus.PLANNING)
            engine.transition("t2", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t2", AgentTaskStatus.RUNNING)
            self.assertIn("No approval found", str(cm.exception))

    def test_3_yellow_with_approved_approval_passes(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a1", "status": "onaylandı", "risk_level": "yellow", "payload": {"task_id": "t3"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t3", objective="yellow task approved", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t3", AgentTaskStatus.PLANNING)
            engine.transition("t3", AgentTaskStatus.WAITING_APPROVAL)
            record = engine.transition("t3", AgentTaskStatus.RUNNING)
            self.assertEqual(record.status, AgentTaskStatus.RUNNING)

    def test_4_red_rejected_without_approval(self):
        with self._run_with_patches():
            engine = TaskEngine()
            task = AgentTask(task_id="t4", objective="red task", context={"risk_level": "red"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t4", AgentTaskStatus.PLANNING)
            engine.transition("t4", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t4", AgentTaskStatus.RUNNING)
            self.assertIn("No approval found", str(cm.exception))

    def test_5_red_with_approved_approval_passes(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a2", "status": "onaylandı", "risk_level": "red", "payload": {"task_id": "t5"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t5", objective="red task approved", context={"risk_level": "red"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t5", AgentTaskStatus.PLANNING)
            engine.transition("t5", AgentTaskStatus.WAITING_APPROVAL)
            record = engine.transition("t5", AgentTaskStatus.RUNNING)
            self.assertEqual(record.status, AgentTaskStatus.RUNNING)

    def test_6_black_always_rejected_even_with_approval(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a3", "status": "onaylandı", "risk_level": "black", "payload": {"task_id": "t6"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t6", objective="black task", context={"risk_level": "black"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t6", AgentTaskStatus.PLANNING)
            engine.transition("t6", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t6", AgentTaskStatus.RUNNING)
            self.assertIn("black risk level", str(cm.exception))

    def test_7_missing_risk_rejected(self):
        with self._run_with_patches():
            engine = TaskEngine()
            task = AgentTask(task_id="t7", objective="no risk", context={}, requested_by="test")
            engine.create_task(task)
            engine.transition("t7", AgentTaskStatus.PLANNING)
            engine.transition("t7", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t7", AgentTaskStatus.RUNNING)
            self.assertIn("Unknown or missing risk level", str(cm.exception))

    def test_8_unknown_risk_rejected(self):
        with self._run_with_patches():
            engine = TaskEngine()
            task = AgentTask(task_id="t8", objective="unknown risk", context={"risk_level": "purple"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t8", AgentTaskStatus.PLANNING)
            engine.transition("t8", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t8", AgentTaskStatus.RUNNING)
            self.assertIn("Unknown or missing risk level", str(cm.exception))

    def test_9_wrong_task_id_approval_not_accepted(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a4", "status": "onaylandı", "risk_level": "yellow", "payload": {"task_id": "other-task"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t9", objective="wrong task", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t9", AgentTaskStatus.PLANNING)
            engine.transition("t9", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t9", AgentTaskStatus.RUNNING)
            self.assertIn("No approval found", str(cm.exception))

    def test_10_rejected_approval_blocks_transition(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a5", "status": "reddedildi", "risk_level": "yellow", "payload": {"task_id": "t10"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t10", objective="rejected", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t10", AgentTaskStatus.PLANNING)
            engine.transition("t10", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t10", AgentTaskStatus.RUNNING)
            self.assertIn("rejected approval", str(cm.exception))

    def test_11_duplicate_approve_idempotent(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a6", "status": "bekliyor", "risk_level": "yellow", "payload": {"task_id": "t11"}})
            resp1 = approvals.approve_approval("a6")
            self.assertTrue(resp1["success"])
            self.assertEqual(resp1["approval"]["status"], "onaylandı")

            resp2 = approvals.approve_approval("a6")
            self.assertTrue(resp2["success"])
            self.assertEqual(resp2["approval"]["status"], "onaylandı")
            self.assertEqual(resp2["message"], "Zaten onaylanmış.")

    def test_12_reject_approved_returns_409(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a7", "status": "onaylandı", "risk_level": "yellow", "payload": {"task_id": "t12"}})
            with self.assertRaises(Exception) as cm:
                approvals.reject_approval("a7")
            self.assertEqual(cm.exception.status_code, 409)
            self.assertIn("Cannot reject an approved approval", str(cm.exception.detail))

    def test_13_duplicate_reject_idempotent(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a8", "status": "bekliyor", "risk_level": "yellow", "payload": {"task_id": "t13"}})
            resp1 = approvals.reject_approval("a8")
            self.assertTrue(resp1["success"])
            self.assertEqual(resp1["approval"]["status"], "reddedildi")

            resp2 = approvals.reject_approval("a8")
            self.assertTrue(resp2["success"])
            self.assertEqual(resp2["approval"]["status"], "reddedildi")
            self.assertEqual(resp2["message"], "Zaten reddedilmiş.")

    def test_14_approve_rejected_returns_409(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a9", "status": "reddedildi", "risk_level": "yellow", "payload": {"task_id": "t14"}})
            with self.assertRaises(Exception) as cm:
                approvals.approve_approval("a9")
            self.assertEqual(cm.exception.status_code, 409)
            self.assertIn("Cannot approve a rejected approval", str(cm.exception.detail))

    def test_15_second_running_transition_rejected(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a10", "status": "onaylandı", "risk_level": "yellow", "payload": {"task_id": "t15"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t15", objective="second run", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t15", AgentTaskStatus.PLANNING)
            engine.transition("t15", AgentTaskStatus.WAITING_APPROVAL)
            engine.transition("t15", AgentTaskStatus.RUNNING)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t15", AgentTaskStatus.RUNNING)
            self.assertIn("Invalid transition", str(cm.exception))

    def test_16_turkish_onaylandi_works(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a11", "status": "onaylandı", "risk_level": "yellow", "payload": {"task_id": "t16"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t16", objective="turkish", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t16", AgentTaskStatus.PLANNING)
            engine.transition("t16", AgentTaskStatus.WAITING_APPROVAL)
            record = engine.transition("t16", AgentTaskStatus.RUNNING)
            self.assertEqual(record.status, AgentTaskStatus.RUNNING)

    def test_17_ascii_onaylandi_not_accepted(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a12", "status": "onaylandi", "risk_level": "yellow", "payload": {"task_id": "t17"}})
            engine = TaskEngine()
            task = AgentTask(task_id="t17", objective="ascii", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t17", AgentTaskStatus.PLANNING)
            engine.transition("t17", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t17", AgentTaskStatus.RUNNING)
            self.assertIn("approved approval", str(cm.exception))

    def test_18_broken_payload_fail_closed(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a13", "status": "onaylandı", "risk_level": "yellow", "payload": "not-a-dict"})
            engine = TaskEngine()
            task = AgentTask(task_id="t18", objective="broken", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t18", AgentTaskStatus.PLANNING)
            engine.transition("t18", AgentTaskStatus.WAITING_APPROVAL)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t18", AgentTaskStatus.RUNNING)
            self.assertIn("No approval found", str(cm.exception))

    def test_19_black_approval_endpoint_cannot_approve(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a14", "status": "bekliyor", "risk_level": "black", "payload": {"task_id": "t19"}})
            with self.assertRaises(Exception) as cm:
                approvals.approve_approval("a14")
            self.assertEqual(cm.exception.status_code, 409)
            self.assertIn("Black risk approvals cannot be approved", str(cm.exception.detail))

    def test_20_unknown_approval_status_cannot_change(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a15", "status": "unknown_status", "risk_level": "yellow", "payload": {"task_id": "t20"}})
            with self.assertRaises(Exception) as cm:
                approvals.approve_approval("a15")
            self.assertEqual(cm.exception.status_code, 409)
            self.assertIn("Invalid approval status", str(cm.exception.detail))

            with self.assertRaises(Exception) as cm2:
                approvals.reject_approval("a15")
            self.assertEqual(cm2.exception.status_code, 409)

    async def test_21_green_execute_reaches_agent_without_approval(self):
        with self._run_with_patches():
            engine = self._prepare_waiting_task("t21", "green")
            result, agent = await self._execute_with_agent(engine, "t21")
            self.assertEqual(result.task_id, "t21")
            self.assertEqual(agent.execution_count, 1)

    async def test_22_yellow_execute_requires_exact_approved_status_and_risk(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a16", "status": "onaylandı", "risk_level": "YELLOW", "payload": {"task_id": "t22"}})
            engine = self._prepare_waiting_task("t22", "yellow")
            result, agent = await self._execute_with_agent(engine, "t22")
            self.assertEqual(result.task_id, "t22")
            self.assertEqual(agent.execution_count, 1)

    async def test_23_black_execute_never_reaches_agent(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a17", "status": "onaylandı", "payload": {"task_id": "t23"}})
            engine = self._prepare_waiting_task("t23", "black")
            agent = CountingAgent()
            with self.assertRaises(ValueError) as cm:
                await engine.execute_task("t23", agent, AgentContext())
            self.assertIn("black risk level", str(cm.exception))
            self.assertEqual(agent.execution_count, 0)

    async def test_24_duplicate_resume_does_not_start_second_execution(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a18", "status": "onaylandı", "risk_level": "red", "payload": {"task_id": "t24"}})
            engine = self._prepare_waiting_task("t24", "red")
            result, agent = await self._execute_with_agent(engine, "t24")
            self.assertEqual(result.task_id, "t24")
            with self.assertRaises(ValueError) as cm:
                await engine.execute_task("t24", agent, AgentContext())
            self.assertIn("already running", str(cm.exception))
            self.assertEqual(agent.execution_count, 1)

    async def test_25_rejected_approval_blocks_execution_even_with_approved_one(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a19", "status": "onaylandı", "risk_level": "yellow", "payload": {"task_id": "t25"}})
            upsert_item(self.approvals_path, {"id": "a20", "status": "reddedildi", "risk_level": "red", "payload": {"task_id": "t25"}})
            engine = self._prepare_waiting_task("t25", "yellow")
            agent = CountingAgent()
            with self.assertRaises(ValueError) as cm:
                await engine.execute_task("t25", agent, AgentContext())
            self.assertIn("rejected approval", str(cm.exception))
            self.assertEqual(agent.execution_count, 0)

    def test_26_planning_to_running_direct_transition_is_gated(self):
        with self._run_with_patches():
            engine = TaskEngine()
            task = AgentTask(task_id="t26", objective="direct", context={"risk_level": "yellow"}, requested_by="test")
            engine.create_task(task)
            engine.transition("t26", AgentTaskStatus.PLANNING)
            with self.assertRaises(ValueError) as cm:
                engine.transition("t26", AgentTaskStatus.RUNNING)
            self.assertIn("No approval found", str(cm.exception))

    def test_27_approved_risk_mismatch_is_not_accepted(self):
        with self._run_with_patches():
            upsert_item(self.approvals_path, {"id": "a21", "status": "onaylandı", "risk_level": "red", "payload": {"task_id": "t27"}})
            engine = self._prepare_waiting_task("t27", "yellow")
            with self.assertRaises(ValueError) as cm:
                engine.transition("t27", AgentTaskStatus.RUNNING)
            self.assertIn("approved approval for risk level 'yellow'", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)