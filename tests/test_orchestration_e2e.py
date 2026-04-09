from pathlib import Path

import pytest

from agents.factory import AgentFactory
from core.events import EventBus
from domain.models import AgentStatus, FactoryRunRequest, ProjectSpec
from orchestration.pipeline import FactoryOrchestrator
from services.analyzer import CodeAnalyzer
from services.project_generator import ProjectGenerator
from services.self_improvement import SelfImprovementService


@pytest.mark.asyncio
async def test_full_agent_pipeline_generates_reviews_repairs_and_packages_project(tmp_path: Path) -> None:
    analyzer = CodeAnalyzer()
    agent_factory = AgentFactory(
        generator=ProjectGenerator(),
        analyzer=analyzer,
        improver=SelfImprovementService(analyzer),
    )
    events = []
    event_bus = EventBus()

    async def collect(event):
        events.append(event.name)

    event_bus.subscribe("*", collect)
    orchestrator = FactoryOrchestrator(agent_factory.pipeline(), event_bus=event_bus)

    result = await orchestrator.run(
        FactoryRunRequest(
            spec=ProjectSpec(
                name="ops-portal",
                summary="Operations portal for service readiness and durable work-item tracking.",
            ),
            output_dir=tmp_path,
        )
    )

    assert result.status == AgentStatus.SUCCEEDED
    assert [agent.agent_name.value for agent in result.agent_results] == [
        "architect",
        "developer",
        "reviewer",
        "debugger",
        "devops",
    ]
    assert all(agent.runtime_seconds > 0 for agent in result.agent_results)
    assert all(agent.logs for agent in result.agent_results)
    assert result.scan_report is not None
    assert result.deployment["ready"] is True
    assert (Path(result.output_dir) / ".factory" / "analysis-report.json").exists()
    assert events[0] == "factory.run.started"
    assert events[-1] == "factory.run.finished"

