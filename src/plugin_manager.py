"""
Plugin management system for PEGGPT.

Provides discovery via entry points, registration, lifecycle management,
isolation, error handling, and dynamic loading/unloading.
"""
from __future__ import annotations

import importlib.metadata as metadata
import logging
from typing import Any, Callable, Dict, List


class PluginManager:
    """Loads and manages PEGGPT plugins."""

    def __init__(self, namespaces: List[str]):
        self.namespaces = namespaces
        self.plugins: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)

    def discover(self) -> None:
        """Discover plugins from configured entry point namespaces."""
        for ns in self.namespaces:
            try:
                for ep in metadata.entry_points().select(group=ns):
                    self._load_entry_point(ep)
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error("Discovery failed for %s: %s", ns, exc)

    def _load_entry_point(self, ep: metadata.EntryPoint) -> None:
        """Load a plugin from a single entry point."""
        try:
            plugin_cls = ep.load()
            plugin = plugin_cls()
            if hasattr(plugin, "setup"):
                plugin.setup()
            self.plugins[ep.name] = plugin
        except Exception as exc:
            self.logger.error("Failed loading plugin %s: %s", ep.name, exc)

    def register_plugin(self, name: str, plugin_cls: Callable[[], Any]) -> None:
        """Manually register a plugin class."""
        try:
            plugin = plugin_cls()
            if hasattr(plugin, "setup"):
                plugin.setup()
            self.plugins[name] = plugin
        except Exception as exc:
            self.logger.error("Failed registering plugin %s: %s", name, exc)

    def unload(self, name: str) -> None:
        """Unload a previously registered plugin."""
        plugin = self.plugins.pop(name, None)
        if plugin and hasattr(plugin, "teardown"):
            try:
                plugin.teardown()
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error("Error during teardown of %s: %s", name, exc)

    def run(self, name: str, *args, **kwargs) -> Any:
        """Execute a plugin's ``run`` method."""
        plugin = self.plugins.get(name)
        if not plugin:
            raise KeyError(f"Plugin {name} not registered")
        try:
            if hasattr(plugin, "run"):
                return plugin.run(*args, **kwargs)
            raise AttributeError("Plugin has no run method")
        except Exception as exc:
            self.logger.error("Plugin %s raised error: %s", name, exc)
            raise
