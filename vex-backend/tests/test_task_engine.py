from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.agent_kernel import AgentResult, AgentTask
from app.schemas.task_engine import AgentTaskStatus
from app.services.task_engine import TaskEngine


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


class TaskEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.engine = TaskEngine(now_provider=self.clock.now)

    def create_task(self, task_id: str = "t1", objective: str = "Do work", parent_task_id: str | None = None):
        return self.engine.create_task(
            AgentTask(task_id=task_id, objective=objective, requested_by="user"),
            parent_task_id=parent_task_id,
        )

    def test_create_task_sets_initial_fields(self):
        record = self.create_task(parent_task_id=None)
        self.assertEqual(record.status, AgentTaskStatus.CREATED)
        self.assertEqual(record.created_at, datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(record.updated_at, record.created_at)
        self.assertIsNone(record.started_at)
        self.assertIsNone(record.completed_at)

    def test_duplicate_task_ids_are_rejected(self):
        self.create_task()
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.create_task()

    def test_list_tasks_preserves_insertion_order(self):
        self.create_task("t1", "One")
        self.create_task("t2", "Two")
        self.assertEqual([task.task_id for task in self.engine.list_tasks()], ["t1", "t2"])

    def test_get_task_returns_record_and_missing_task_errors(self):
        record = self.create_task()
        self.assertIs(self.engine.get_task("t1"), record)
        with self.assertRaisesRegex(KeyError, "not registered"):
            self.engine.get_task("missing")

    def test_valid_and_invalid_transitions(self):
        self.create_task()
        self.engine.transition("t1", AgentTaskStatus.PLANNING)
        self.assertEqual(self.engine.get_task("t1").status, AgentTaskStatus.PLANNING)
        with self.assertRaisesRegex(ValueError, "Invalid transition"):
            self.engine.transition("t1", AgentTaskStatus.COMPLETED)

    def test_terminal_states_block_exit(self):
        self.create_task()
        self.engine.transition("t1", AgentTaskStatus.FAILED)
        with self.assertRaisesRegex(ValueError, "already terminal"):
            self.engine.transition("t1", AgentTaskStatus.RUNNING)

    def test_running_sets_started_at_once_and_terminal_sets_completed_at(self):
        self.create_task()
        self.engine.transition("t1", AgentTaskStatus.PLANNING)
        running = self.engine.transition("t1", AgentTaskStatus.RUNNING)
        started_at = running.started_at
        self.engine.transition("t1", AgentTaskStatus.BLOCKED)
        running_again = self.engine.transition("t1", AgentTaskStatus.RUNNING)
        self.engine.transition("t1", AgentTaskStatus.VERIFYING)
        completed = self.engine.transition("t1", AgentTaskStatus.COMPLETED)
        self.assertEqual(running_again.started_at, started_at)
        self.assertIsNotNone(completed.completed_at)

    def test_assign_agent_and_empty_agent_name_validation(self):
        self.create_task()
        assigned = self.engine.assign_agent("t1", "planner")
        self.assertEqual(assigned.assigned_agent, "planner")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            self.engine.assign_agent("t1", "   ")

    def test_set_result_and_set_error_do_not_change_status(self):
        record = self.create_task()
        result = AgentResult(task_id="t1", agent="planner", status="ok", summary="done")
        self.engine.set_result("t1", result)
        self.engine.set_error("t1", "boom")
        self.assertIs(record.result, result)
        self.assertEqual(record.error, "boom")
        self.assertEqual(record.status, AgentTaskStatus.CREATED)

    def test_request_cancel_and_terminal_cancel_error(self):
        self.create_task()
        cancelled = self.engine.request_cancel("t1")
        self.assertEqual(cancelled.status, AgentTaskStatus.CANCELLED)
        self.create_task("t2", "Done")
        self.engine.transition("t2", AgentTaskStatus.FAILED)
        with self.assertRaisesRegex(ValueError, "already terminal"):
            self.engine.request_cancel("t2")

    def test_mutable_defaults_and_deterministic_timestamp_updates(self):
        first = self.engine.create_task(AgentTask(task_id="t1", objective="One", requested_by="user", context={"a": 1}))
        second = self.engine.create_task(AgentTask(task_id="t2", objective="Two", requested_by="user"))
        first.metadata["x"] = 1
        self.assertEqual(second.metadata, {})
        created = first.updated_at
        self.engine.assign_agent("t1", "planner")
        assigned = first.updated_at
        self.engine.set_error("t1", "err")
        errored = first.updated_at
        self.assertLess(created, assigned)
        self.assertLess(assigned, errored)


if __name__ == "__main__":
    unittest.main()
