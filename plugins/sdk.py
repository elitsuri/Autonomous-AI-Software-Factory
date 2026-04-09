from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from domain.models import FactoryRunResult, ProjectSpec, ScanReport


@dataclass
class PluginContext:
    workspace: Path
    metadata: dict[str, Any] = field(default_factory=dict)


class FactoryPlugin(Protocol):
    name: str
    version: str

    async def on_project_spec(self, spec: ProjectSpec, context: PluginContext) -> ProjectSpec:
        return spec

    async def on_scan_report(self, report: ScanReport, context: PluginContext) -> ScanReport:
        return report

    async def on_factory_result(self, result: FactoryRunResult, context: PluginContext) -> FactoryRunResult:
        return result


class NoopPlugin:
    name = "noop"
    version = "1.0.0"

    async def on_project_spec(self, spec: ProjectSpec, context: PluginContext) -> ProjectSpec:
        return spec

    async def on_scan_report(self, report: ScanReport, context: PluginContext) -> ScanReport:
        return report

    async def on_factory_result(self, result: FactoryRunResult, context: PluginContext) -> FactoryRunResult:
        return result

