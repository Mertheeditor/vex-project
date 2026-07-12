from __future__ import annotations

import unittest

from app.schemas.agent_kernel import AgentContext, AgentResult, AgentTask
from app.services.agent_kernel import AgentRegistry, BaseAgent


class FakeAgent(BaseAgent):
    name = "planner"
    description = "Test agent"
    capabilities = ("plan", "review")
    allowed_tools = ("read",)
    risk_level = "low"

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            agent=self.name,
            status="success",
            summary=task.objective,
        )


class AgentKernelTestCase(unittest.TestCase):
    def test_agent_task_mutable_defaults_are_not_shared(self):
        first = AgentTask(task_id="t1", objective="one", requested_by="user")
        second = AgentTask(task_id="t2", objective="two", requested_by="user")

        first.context["key"] = "value"
        first.constraints.append("safe")

        self.assertEqual(second.context, {})
        self.assertEqual(second.constraints, [])

    def test_agent_result_mutable_defaults_are_not_shared(self):
        first = AgentResult(task_id="t1", agent="a1", status="ok", summary="done")
        second = AgentResult(task_id="t2", agent="a2", status="ok", summary="done")

        first.artifacts.append({"file": "out.txt"})
        first.evidence.append("log")
        first.risks.append("none")

        self.assertEqual(second.artifacts, [])
        self.assertEqual(second.evidence, [])
        self.assertEqual(second.risks, [])

    def test_agent_context_starts_not_cancelled(self):
        context = AgentContext()

        self.assertFalse(context.is_cancelled())

    def test_agent_context_request_cancel_sets_cancelled(self):
        context = AgentContext()

        context.request_cancel()

        self.assertTrue(context.is_cancelled())

    def test_registry_registers_agent_successfully(self):
        registry = AgentRegistry()
        agent = FakeAgent()

        registered = registry.register(agent)

        self.assertIs(registered, agent)
        self.assertEqual(registry.list_agents(), [agent])

    def test_registry_rejects_duplicate_agent_names(self):
        registry = AgentRegistry()
        registry.register(FakeAgent())

        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(FakeAgent())

    def test_registry_get_returns_agent_by_name(self):
        registry = AgentRegistry()
        agent = FakeAgent()
        registry.register(agent)

        self.assertIs(registry.get("planner"), agent)

    def test_registry_get_missing_agent_raises_clear_error(self):
        registry = AgentRegistry()

        with self.assertRaisesRegex(KeyError, "not registered"):
            registry.get("missing")

    def test_registry_finds_agents_by_capability(self):
        registry = AgentRegistry()
        agent = FakeAgent()
        registry.register(agent)

        self.assertEqual(registry.find_by_capability("plan"), [agent])
        self.assertEqual(registry.find_by_capability("PLAN"), [])

    def test_registry_preserves_registration_order(self):
        class BuilderAgent(FakeAgent):
            name = "builder"
            capabilities = ("build",)

        registry = AgentRegistry()
        first = FakeAgent()
        second = BuilderAgent()

        registry.register(first)
        registry.register(second)

        self.assertEqual([agent.name for agent in registry.list_agents()], ["planner", "builder"])


class AgentKernelAsyncTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_fake_agent_execute_matches_contract(self):
        agent = FakeAgent()
        task = AgentTask(task_id="t1", objective="Plan work", requested_by="user")
        context = AgentContext(metadata={"source": "test"})

        result = await agent.execute(task, context)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.task_id, "t1")
        self.assertEqual(result.agent, "planner")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.summary, "Plan work")


if __name__ == "__main__":
    unittest.main()
