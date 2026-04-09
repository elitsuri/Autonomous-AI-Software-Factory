from pathlib import Path

from agents.base import AgentContext, BaseAgent
from core.events import EventBus
from domain.models import AgentStatus, FactoryRunRequest, FactoryRunResult, ScanReport
from domain.ports import AgentRunRepositoryPort, FactoryRunRepositoryPort


class FactoryOrchestrator:
    def __init__(
        self,
        agents: list[BaseAgent],
        *,
        event_bus: EventBus | None = None,
        agent_repository: AgentRunRepositoryPort | None = None,
        run_repository: FactoryRunRepositoryPort | None = None,
    ) -> None:
        self.agents = agents
        self.event_bus = event_bus or EventBus()
        self.agent_repository = agent_repository
        self.run_repository = run_repository

    async def run(self, request: FactoryRunRequest) -> FactoryRunResult:
        context = AgentContext(request)
        agent_results = []
        status = AgentStatus.SUCCEEDED

        await self.event_bus.publish("factory.run.started", {"project": request.spec.name})
        for agent in self.agents:
            await self.event_bus.publish("agent.run.started", {"agent": agent.name.value})
            result = await agent.run(context)
            agent_results.append(result)
            if self.agent_repository is not None:
                await self.agent_repository.save_agent_result(result)
            await self.event_bus.publish(
                "agent.run.finished",
                {"agent": agent.name.value, "status": result.status.value, "run_id": result.run_id},
            )
            if result.status == AgentStatus.FAILED:
                status = AgentStatus.FAILED
                break

        output_dir = context.state.get("project_root")
        if not output_dir:
            base = request.output_dir or Path("workspaces")
            output_dir = str(base.resolve() / request.spec.name)
        scan_report = context.state.get("scan_report")
        if scan_report is not None and not isinstance(scan_report, ScanReport):
            scan_report = None

        final_result = FactoryRunResult(
            spec=request.spec,
            output_dir=str(output_dir),
            status=status,
            agent_results=agent_results,
            architecture=context.state.get("architecture", {}),
            scan_report=scan_report,
            deployment=context.state.get("deployment", {}),
        )
        if self.run_repository is not None:
            await self.run_repository.save_factory_run(final_result)
        await self.event_bus.publish(
            "factory.run.finished",
            {"project": request.spec.name, "status": status.value, "run_id": final_result.id},
        )
        return final_result

