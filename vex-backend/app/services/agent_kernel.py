from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.agent_kernel import AgentContext, AgentResult, AgentTask


class BaseAgent(ABC):
    name: str = ""
    description: str = ""
    capabilities: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    risk_level: str = "normal"

    @abstractmethod
    async def execute(
        self,
        task: AgentTask,
        context: AgentContext,
    ) -> AgentResult:
        raise NotImplementedError


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._order: list[str] = []

    def register(self, agent: BaseAgent) -> BaseAgent:
        name = getattr(agent, "name", "")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Agent name cannot be empty.")
        if name in self._agents:
            raise ValueError(f"Agent '{name}' is already registered.")
        self._agents[name] = agent
        self._order.append(name)
        return agent

    def get(self, name: str) -> BaseAgent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(f"Agent '{name}' is not registered.") from exc

    def list_agents(self) -> list[BaseAgent]:
        return [self._agents[name] for name in self._order]

    def find_by_capability(self, capability: str) -> list[BaseAgent]:
        return [
            agent
            for agent in self.list_agents()
            if capability in getattr(agent, "capabilities", ())
        ]
