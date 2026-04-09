from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field


class AgentName(StrEnum):
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"
    DEVOPS = "devops"


class AgentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class ProjectSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    summary: str = Field(min_length=10, max_length=2_000)
    frontend: Literal["htmx", "react"] = "htmx"
    database: Literal["postgresql"] = "postgresql"
    features: list[str] = Field(default_factory=list, max_length=30)

    @computed_field
    @property
    def package_name(self) -> str:
        return self.name.lower().replace("-", "_")


class CodeIssue(BaseModel):
    path: str
    line: int
    rule: str
    severity: Severity
    message: str
    suggestion: str


class ScanReport(BaseModel):
    root: str
    issues: list[CodeIssue]
    scanned_files: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @computed_field
    @property
    def has_blockers(self) -> bool:
        return any(issue.severity in {Severity.CRITICAL, Severity.HIGH} for issue in self.issues)


class PromptContext(BaseModel):
    task: str
    project_summary: str
    files: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    agent_name: AgentName | None = None


class CompiledPrompt(BaseModel):
    version: str
    cache_key: str
    text: str
    token_budget_hint: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentResult(BaseModel):
    run_id: str
    agent_name: AgentName
    status: AgentStatus
    input: dict[str, Any]
    output: dict[str, Any]
    logs: list[str]
    runtime_seconds: float = Field(gt=0)
    error: str | None = None
    started_at: datetime
    finished_at: datetime


class FactoryRunRequest(BaseModel):
    spec: ProjectSpec
    output_dir: Path | None = None
    apply_repairs: bool = True
    commit_changes: bool = False


class FactoryRunResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    spec: ProjectSpec
    output_dir: str
    status: AgentStatus
    agent_results: list[AgentResult]
    architecture: dict[str, Any] = Field(default_factory=dict)
    scan_report: ScanReport | None = None
    deployment: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

