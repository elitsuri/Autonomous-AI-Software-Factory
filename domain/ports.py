from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

from domain.models import AgentResult, CompiledPrompt, FactoryRunResult, ProjectSpec, PromptContext, ScanReport


class CachePort(Protocol):
    async def get_text(self, key: str) -> str | None:
        raise NotImplementedError

    async def set_text(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        raise NotImplementedError


class AgentRunRepositoryPort(Protocol):
    async def save_agent_result(self, result: AgentResult) -> None:
        raise NotImplementedError

    async def list_recent_agent_results(self, limit: int = 50) -> list[AgentResult]:
        raise NotImplementedError


class FactoryRunRepositoryPort(Protocol):
    async def save_factory_run(self, result: FactoryRunResult) -> None:
        raise NotImplementedError


class GitPort(Protocol):
    async def commit_all(self, message: str) -> str | None:
        raise NotImplementedError

    async def recent_history(self, limit: int = 10) -> list[str]:
        raise NotImplementedError


class PromptStrategy(ABC):
    @abstractmethod
    async def compile(self, context: PromptContext) -> CompiledPrompt:
        raise NotImplementedError


class ProjectGeneratorPort(Protocol):
    async def generate(self, spec: ProjectSpec, output_dir: Path) -> list[Path]:
        raise NotImplementedError


class AnalyzerPort(Protocol):
    async def scan(self, root: Path) -> ScanReport:
        raise NotImplementedError


class AsyncUnitOfWork(Protocol):
    async def __aenter__(self) -> "AsyncUnitOfWork":
        raise NotImplementedError

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        raise NotImplementedError

    async def commit(self) -> None:
        raise NotImplementedError


class LogStreamPort(Protocol):
    async def stream_logs(self, run_id: str) -> AsyncIterator[str]:
        raise NotImplementedError

