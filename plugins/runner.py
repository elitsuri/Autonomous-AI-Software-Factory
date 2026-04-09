from pathlib import Path

from domain.models import FactoryRunResult, ProjectSpec, ScanReport
from plugins.sdk import FactoryPlugin, PluginContext


class PluginRunner:
    def __init__(self, plugins: list[FactoryPlugin], workspace: Path) -> None:
        self.plugins = plugins
        self.context = PluginContext(workspace=workspace)

    async def prepare_spec(self, spec: ProjectSpec) -> ProjectSpec:
        for plugin in self.plugins:
            spec = await plugin.on_project_spec(spec, self.context)
        return spec

    async def inspect_report(self, report: ScanReport) -> ScanReport:
        for plugin in self.plugins:
            report = await plugin.on_scan_report(report, self.context)
        return report

    async def finalize_result(self, result: FactoryRunResult) -> FactoryRunResult:
        for plugin in self.plugins:
            result = await plugin.on_factory_result(result, self.context)
        return result

