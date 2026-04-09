from pathlib import Path
from typing import Any

from agents.base import AgentContext, BaseAgent
from domain.models import AgentName


class DevOpsAgent(BaseAgent):
    name = AgentName.DEVOPS

    async def execute(self, context: AgentContext, logs: list[str]) -> dict[str, Any]:
        project_root = Path(context.state["project_root"])
        required = ["Dockerfile", "docker-compose.yml", "k8s/deployment.yaml"]
        missing = [relative for relative in required if not (project_root / relative).exists()]
        deployment = {
            "project_root": str(project_root),
            "dockerfile": str(project_root / "Dockerfile"),
            "compose": str(project_root / "docker-compose.yml"),
            "kubernetes": str(project_root / "k8s" / "deployment.yaml"),
            "ready": not missing,
            "missing": missing,
            "runbook": [
                "docker compose up --build",
                "curl http://localhost:8000/health",
                "kubectl apply -f k8s/deployment.yaml",
            ],
        }
        context.state["deployment"] = deployment
        logs.append(f"devops: deployment manifest ready={deployment['ready']}")
        return deployment

