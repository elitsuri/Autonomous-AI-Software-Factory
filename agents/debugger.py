from pathlib import Path
from typing import Any

from agents.base import AgentContext, BaseAgent
from domain.models import AgentName
from services.self_improvement import SelfImprovementService


class DebuggerAgent(BaseAgent):
    name = AgentName.DEBUGGER

    def __init__(self, improver: SelfImprovementService) -> None:
        self.improver = improver

    async def execute(self, context: AgentContext, logs: list[str]) -> dict[str, Any]:
        project_root = Path(context.state["project_root"])
        report, repair = await self.improver.inspect_and_repair(project_root, apply=context.request.apply_repairs)
        context.state["scan_report"] = report
        logs.append(f"debugger: changed {len(repair.changed_files)} files; report saved at {repair.report_path}")
        return {
            "changed_files": repair.changed_files,
            "report_path": repair.report_path,
            "remaining_issues": [issue.model_dump(mode="json") for issue in report.issues],
        }

