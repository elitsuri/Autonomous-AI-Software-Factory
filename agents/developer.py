from pathlib import Path
from typing import Any

from agents.base import AgentContext, BaseAgent
from domain.models import AgentName
from services.project_generator import ProjectGenerator


class DeveloperAgent(BaseAgent):
    name = AgentName.DEVELOPER

    def __init__(self, generator: ProjectGenerator) -> None:
        self.generator = generator

    async def execute(self, context: AgentContext, logs: list[str]) -> dict[str, Any]:
        output_root = context.request.output_dir or Path("workspaces")
        written = await self.generator.generate(context.request.spec, output_root)
        project_root = str(output_root.resolve() / context.request.spec.name)
        context.state["project_root"] = project_root
        context.state["written_files"] = [str(path) for path in written]
        logs.append(f"developer: wrote {len(written)} files into {project_root}")
        return {"project_root": project_root, "written_files": [str(path) for path in written]}

