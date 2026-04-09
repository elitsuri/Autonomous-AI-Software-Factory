from pathlib import Path

import pytest

from domain.models import AgentStatus, FactoryRunResult, ProjectSpec, ScanReport
from plugins.loader import PluginLoader
from plugins.runner import PluginRunner


@pytest.mark.asyncio
async def test_plugin_loader_and_runner_can_enrich_project_spec(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "external_plugins" / "enricher"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.py").write_text(
        "class Plugin:\n"
        "    name = 'enricher'\n"
        "    version = '1.2.3'\n"
        "    async def on_project_spec(self, spec, context):\n"
        "        return spec.model_copy(update={'features': [*spec.features, 'audit log']})\n"
        "    async def on_scan_report(self, report, context):\n"
        "        return report\n"
        "    async def on_factory_result(self, result, context):\n"
        "        result.deployment['plugin'] = self.name\n"
        "        return result\n"
        "plugin = Plugin()\n",
        encoding="utf-8",
    )

    plugins = PluginLoader([tmp_path / "external_plugins"]).discover()
    spec = ProjectSpec(name="billing-api", summary="Billing API that coordinates internal work.")

    runner = PluginRunner(plugins, tmp_path)

    prepared = await runner.prepare_spec(spec)
    inspected = await runner.inspect_report(ScanReport(root=str(tmp_path), issues=[], scanned_files=0))
    finalized = await runner.finalize_result(
        FactoryRunResult(
            spec=prepared,
            output_dir=str(tmp_path),
            status=AgentStatus.SUCCEEDED,
            agent_results=[],
        )
    )

    assert [(plugin.name, plugin.version) for plugin in plugins] == [("enricher", "1.2.3")]
    assert prepared.features == ["audit log"]
    assert inspected.root == str(tmp_path)
    assert finalized.deployment["plugin"] == "enricher"


@pytest.mark.asyncio
async def test_plugin_loader_returns_noop_for_empty_directories(tmp_path: Path) -> None:
    plugins = PluginLoader([tmp_path / "no-plugins-here"]).discover()
    runner = PluginRunner(plugins, tmp_path)
    spec = ProjectSpec(name="plain-api", summary="Plain API used to exercise the default plugin.")

    prepared = await runner.prepare_spec(spec)
    finalized = await runner.finalize_result(
        FactoryRunResult(
            spec=prepared,
            output_dir=str(tmp_path),
            status=AgentStatus.SUCCEEDED,
            agent_results=[],
        )
    )

    assert [(plugin.name, plugin.version) for plugin in plugins] == [("noop", "1.0.0")]
    assert prepared == spec
    assert finalized.status == AgentStatus.SUCCEEDED
