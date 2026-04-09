import importlib.util
from pathlib import Path
from types import ModuleType

from plugins.sdk import FactoryPlugin, NoopPlugin


class PluginLoadError(RuntimeError):
    pass


class PluginLoader:
    def __init__(self, plugin_dirs: list[Path]) -> None:
        self.plugin_dirs = [path.resolve() for path in plugin_dirs]

    def discover(self) -> list[FactoryPlugin]:
        plugins: list[FactoryPlugin] = []
        for directory in self.plugin_dirs:
            if not directory.exists():
                continue
            for plugin_file in sorted(directory.glob("*/plugin.py")):
                plugins.append(self.load(plugin_file))
        return plugins or [NoopPlugin()]

    def load(self, plugin_file: Path) -> FactoryPlugin:
        module = self._load_module(plugin_file)
        plugin = getattr(module, "plugin", None)
        if plugin is None and hasattr(module, "create_plugin"):
            plugin = module.create_plugin()
        if plugin is None:
            raise PluginLoadError(f"{plugin_file} must expose plugin or create_plugin()")
        for attribute in ("name", "version", "on_project_spec", "on_scan_report", "on_factory_result"):
            if not hasattr(plugin, attribute):
                raise PluginLoadError(f"{plugin_file} plugin is missing {attribute}")
        return plugin

    def _load_module(self, plugin_file: Path) -> ModuleType:
        module_name = f"factory_external_plugin_{plugin_file.parent.name}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Cannot load plugin module from {plugin_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

