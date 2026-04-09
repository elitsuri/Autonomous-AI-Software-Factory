from pathlib import Path
from typing import Any

from agents.base import AgentContext, BaseAgent
from domain.models import AgentName
from services.analyzer import CodeAnalyzer


class ReviewerAgent(BaseAgent):
    name = AgentName.REVIEWER

    def __init__(self, analyzer: CodeAnalyzer) -> None:
        self.analyzer = analyzer

    async def execute(self, context: AgentContext, logs: list[str]) -> dict[str, Any]:
        project_root = Path(context.state["project_root"])
        report = await self.analyzer.scan(project_root)
        context.state["scan_report"] = report
        logs.append(f"reviewer: scanned {report.scanned_files} Python files and found {len(report.issues)} issues")
        return report.model_dump(mode="json")

