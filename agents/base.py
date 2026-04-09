import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from domain.models import AgentName, AgentResult, AgentStatus, FactoryRunRequest


class AgentContext:
    def __init__(self, request: FactoryRunRequest) -> None:
        self.request = request
        self.state: dict[str, Any] = {}


class BaseAgent(ABC):
    name: AgentName

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list[str] = []
        started_at = datetime.now(UTC)
        timer_started = time.perf_counter()
        run_id = str(uuid4())
        try:
            logs.append(f"{self.name.value}: started")
            output = await self.execute(context, logs)
            status = AgentStatus.SUCCEEDED
            error = None
            logs.append(f"{self.name.value}: succeeded")
        except Exception as exc:
            output = {}
            status = AgentStatus.FAILED
            error = f"{type(exc).__name__}: {exc}"
            logs.append(f"{self.name.value}: failed: {error}")
        finished_at = datetime.now(UTC)
        runtime = max(time.perf_counter() - timer_started, 0.000_001)
        return AgentResult(
            run_id=run_id,
            agent_name=self.name,
            status=status,
            input=context.request.model_dump(mode="json"),
            output=output,
            logs=logs,
            runtime_seconds=runtime,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )

    @abstractmethod
    async def execute(self, context: AgentContext, logs: list[str]) -> dict[str, Any]:
        raise NotImplementedError

