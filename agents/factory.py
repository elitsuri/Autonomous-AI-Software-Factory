from agents.architect import ArchitectAgent
from agents.base import BaseAgent
from agents.debugger import DebuggerAgent
from agents.developer import DeveloperAgent
from agents.devops import DevOpsAgent
from agents.reviewer import ReviewerAgent
from domain.models import AgentName
from services.analyzer import CodeAnalyzer
from services.project_generator import ProjectGenerator
from services.self_improvement import SelfImprovementService


class AgentFactory:
    """Factory pattern for agent construction."""

    def __init__(
        self,
        *,
        generator: ProjectGenerator,
        analyzer: CodeAnalyzer,
        improver: SelfImprovementService,
    ) -> None:
        self.generator = generator
        self.analyzer = analyzer
        self.improver = improver

    def create(self, name: AgentName) -> BaseAgent:
        if name == AgentName.ARCHITECT:
            return ArchitectAgent()
        if name == AgentName.DEVELOPER:
            return DeveloperAgent(self.generator)
        if name == AgentName.REVIEWER:
            return ReviewerAgent(self.analyzer)
        if name == AgentName.DEBUGGER:
            return DebuggerAgent(self.improver)
        if name == AgentName.DEVOPS:
            return DevOpsAgent()
        raise ValueError(f"Unsupported agent {name}")

    def pipeline(self) -> list[BaseAgent]:
        return [
            self.create(AgentName.ARCHITECT),
            self.create(AgentName.DEVELOPER),
            self.create(AgentName.REVIEWER),
            self.create(AgentName.DEBUGGER),
            self.create(AgentName.DEVOPS),
        ]

