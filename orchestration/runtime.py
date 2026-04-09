from core.events import Event
from domain.models import AgentResult


class RuntimeState:
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.agent_results: list[AgentResult] = []

    async def observe_event(self, event: Event) -> None:
        self.events.append(event)
        self.events = self.events[-500:]

    async def record_agent_result(self, result: AgentResult) -> None:
        self.agent_results.append(result)
        self.agent_results = self.agent_results[-200:]

