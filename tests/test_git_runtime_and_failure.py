from datetime import UTC, datetime

import pytest

from agents.base import AgentContext, BaseAgent
from core.events import Event
from core.logging import configure_logging
from domain.models import AgentName, AgentResult, AgentStatus, FactoryRunRequest, FactoryRunResult, ProjectSpec
from orchestration.pipeline import FactoryOrchestrator
from orchestration.runtime import RuntimeState
from services.git_workflow import SmartCommitService


class FakeGit:
    def __init__(self) -> None:
        self.message: str | None = None

    async def commit_all(self, message: str) -> str:
        self.message = message
        return "abc123"

    async def recent_history(self, limit: int = 10) -> list[str]:
        return ["abc123 2026-04-09 Generate service"][:limit]


class FailingAgent(BaseAgent):
    name = AgentName.REVIEWER

    async def execute(self, context: AgentContext, logs: list[str]):
        logs.append("about to fail")
        raise ValueError("review failed")


def _agent_result() -> AgentResult:
    now = datetime.now(UTC)
    return AgentResult(
        run_id="run-1",
        agent_name=AgentName.DEVELOPER,
        status=AgentStatus.SUCCEEDED,
        input={},
        output={"written_files": ["a.py", "b.py"]},
        logs=["developer: succeeded"],
        runtime_seconds=0.1,
        started_at=now,
        finished_at=now,
    )


def test_logging_configuration_can_be_called_more_than_once() -> None:
    configure_logging()
    configure_logging("DEBUG")


@pytest.mark.asyncio
async def test_smart_commit_service_builds_message_and_commits() -> None:
    git = FakeGit()
    result = FactoryRunResult(
        spec=ProjectSpec(name="billing-api", summary="Billing API for finance operators."),
        output_dir="/tmp/billing-api",
        status=AgentStatus.SUCCEEDED,
        agent_results=[_agent_result()],
    )

    outcome = await SmartCommitService(git).commit_factory_run(result)

    assert outcome.sha == "abc123"
    assert "Generate billing-api service" in outcome.message
    assert "Factory wrote 2 files" in outcome.message
    assert git.message == outcome.message


@pytest.mark.asyncio
async def test_runtime_state_keeps_recent_events_and_agent_results() -> None:
    runtime = RuntimeState()
    result = _agent_result()

    await runtime.observe_event(Event(name="factory.run.started", payload={"project": "billing-api"}))
    await runtime.record_agent_result(result)

    assert runtime.events[0].payload == {"project": "billing-api"}
    assert runtime.agent_results == [result]


@pytest.mark.asyncio
async def test_orchestrator_stops_on_failed_agent() -> None:
    orchestrator = FactoryOrchestrator([FailingAgent()])
    result = await orchestrator.run(
        FactoryRunRequest(
            spec=ProjectSpec(name="broken-app", summary="Broken app used to prove failure handling."),
        )
    )

    assert result.status == AgentStatus.FAILED
    assert len(result.agent_results) == 1
    assert result.agent_results[0].status == AgentStatus.FAILED
    assert "ValueError" in result.agent_results[0].error
