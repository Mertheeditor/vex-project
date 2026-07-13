from __future__ import annotations

import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from app.core.paths import APPROVALS_PATH
from app.schemas.agent_kernel import AgentTask
from app.schemas.task_engine import AgentTaskStatus
from app.services.task_engine import TaskEngine
from app.storage.entity_store import save_items, upsert_item
from app.routes import approvals


class ApprovalGateTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)