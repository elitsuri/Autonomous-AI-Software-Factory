from typing import Any

from agents.base import AgentContext, BaseAgent
from domain.models import AgentName


class ArchitectAgent(BaseAgent):
    name = AgentName.ARCHITECT

    async def execute(self, context: AgentContext, logs: list[str]) -> dict[str, Any]:
        spec = context.request.spec
        architecture = {
            "style": "clean-architecture-with-hexagonal-adapters",
            "backend": "FastAPI application service with async SQLAlchemy repositories",
            "frontend": spec.frontend,
            "database": spec.database,
            "queue": "Celery over Redis for background factory runs",
            "observability": ["Prometheus metrics", "structured agent logs", "analysis reports"],
            "security": ["JWT authentication", "role-based authorization", "rate-limited API"],
            "features": spec.features,
        }
        context.state["architecture"] = architecture
        logs.append(f"architect: planned {len(architecture)} architecture sections")
        return architecture

