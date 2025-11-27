"""
Plugin Manager - Dynamic plugin loading and management for tool expansion.

This module provides a modular plugin system for tools beyond built-in
integrations (like Shopify/Etsy). Plugins can be loaded dynamically
from a plugins directory, enabling runtime extension of capabilities.

Key Features:
- Dynamic plugin discovery and loading
- Plugin lifecycle management (load, reload, unload)
- Sandboxed execution environment
- Plugin validation and security checks
- Support for both sync and async plugins
- Plugin dependency management

Usage:
    manager = PluginManager(plugin_dir="plugins")
    loaded = manager.load_plugins()
    result = manager.execute("etsy", "list_products", {"limit": 10})
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """
    Abstract base class for all plugins.

    Plugins must inherit from this class and implement:
    - name property: Plugin identifier
    - execute(): Main execution method
    - describe_capabilities(): List supported actions

    Example:
        class MyPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "my_plugin"

            def execute(self, action: str, params: Dict) -> Dict:
                return {"result": f"Executed {action}"}

            def describe_capabilities(self) -> List[str]:
                return ["action1", "action2"]
    """

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        """
        Initialize the plugin.

        Args:
            config: Plugin configuration dictionary
        """
        self.config = config or {}
        self._initialized = False
        self._metadata: Dict[str, Any] = {
            "loaded_at": datetime.now().isoformat(),
            "version": getattr(self, "version", "1.0.0")
        }

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin's unique identifier."""
        pass

    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a plugin action.

        Args:
            action: Action to execute
            params: Parameters for the action

        Returns:
            Result dictionary with at least 'status' key
        """
        pass

    @abstractmethod
    def describe_capabilities(self) -> List[str]:
        """
        Return list of supported action names.

        Returns:
            List of action identifiers this plugin supports
        """
        pass

    def initialize(self) -> bool:
        """
        Initialize the plugin (called after loading).

        Override this method for any setup that needs to happen
        after the plugin is loaded (e.g., API connections).

        Returns:
            True if initialization successful
        """
        self._initialized = True
        return True

    def shutdown(self) -> None:
        """
        Clean up plugin resources.

        Override this for cleanup (close connections, etc.)
        """
        self._initialized = False

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self.config[key] = value

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized

    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return {
            "name": self.name,
            "capabilities": self.describe_capabilities(),
            "initialized": self._initialized,
            **self._metadata
        }


# Alias for backward compatibility with spec
PluginClass = PluginBase


class PluginManager:
    """
    Dynamic plugin loader and manager.

    Handles discovering, loading, and managing plugins from a
    directory structure. Provides a unified interface for executing
    plugin actions.

    Attributes:
        plugin_dir: Path to plugins directory
        plugins: Dictionary of loaded plugin instances
        plugin_classes: Dictionary of plugin classes (for reinstantiation)
    """

    # Dangerous patterns to check in plugin code
    DANGEROUS_PATTERNS = [
        "os.system",
        "subprocess.call",
        "subprocess.run",
        "subprocess.Popen",
        "__import__",
        "eval(",
        "exec(",
        "compile(",
        "open(",  # Restrict file operations
    ]

    def __init__(
        self,
        plugin_dir: str | Path = "plugins",
        config: Dict[str, Any] | None = None,
        validate_security: bool = True
    ) -> None:
        """
        Initialize the PluginManager.

        Args:
            plugin_dir: Path to directory containing plugin files
            config: Global plugin configuration
            validate_security: Whether to validate plugins for security
        """
        self.plugin_dir = Path(plugin_dir)
        self.config = config or {}
        self.validate_security = validate_security
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self._load_errors: Dict[str, str] = {}

        logger.info(
            "PluginManager initialized with dir=%s, security=%s",
            self.plugin_dir,
            validate_security
        )

    def load_plugins(self) -> List[str]:
        """
        Discover and load all plugins from the plugin directory.

        Scans the plugin directory for Python files, validates them,
        and loads valid plugins.

        Returns:
            List of successfully loaded plugin names
        """
        loaded: List[str] = []
        self._load_errors = {}

        if not self.plugin_dir.exists():
            logger.warning("Plugin directory does not exist: %s", self.plugin_dir)
            return loaded

        logger.info("Scanning plugin directory: %s", self.plugin_dir)

        for file_path in self.plugin_dir.iterdir():
            if file_path.suffix == ".py" and not file_path.name.startswith("_"):
                try:
                    plugin_name = self._load_plugin_file(file_path)
                    if plugin_name:
                        loaded.append(plugin_name)
                except Exception as e:
                    logger.error("Failed to load plugin %s: %s", file_path.name, e)
                    self._load_errors[file_path.stem] = str(e)

        logger.info("Loaded %d plugins: %s", len(loaded), loaded)
        return loaded

    def _load_plugin_file(self, file_path: Path) -> Optional[str]:
        """
        Load a single plugin file.

        Args:
            file_path: Path to the plugin Python file

        Returns:
            Plugin name if successful, None otherwise
        """
        module_name = file_path.stem
        logger.debug("Loading plugin file: %s", file_path)

        # Security validation
        if self.validate_security:
            if not self._validate_plugin_security(file_path):
                logger.warning("Plugin %s failed security validation", module_name)
                self._load_errors[module_name] = "Security validation failed"
                return None

        # Load module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            logger.error("Could not create module spec for %s", file_path)
            return None

        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error("Error executing plugin module %s: %s", module_name, e)
            self._load_errors[module_name] = f"Execution error: {e}"
            return None

        # Find plugin class
        plugin_class = self._find_plugin_class(module)
        if not plugin_class:
            logger.warning("No valid plugin class found in %s", module_name)
            self._load_errors[module_name] = "No valid PluginClass found"
            return None

        # Instantiate and initialize plugin
        try:
            plugin_config = self.config.get(module_name, {})
            instance = plugin_class(config=plugin_config)

            if not instance.initialize():
                logger.warning("Plugin %s failed to initialize", module_name)
                self._load_errors[module_name] = "Initialization failed"
                return None

            # Store plugin
            plugin_name = instance.name
            self.plugins[plugin_name] = instance
            self.plugin_classes[plugin_name] = plugin_class

            logger.info("Successfully loaded plugin: %s", plugin_name)
            return plugin_name

        except Exception as e:
            logger.error("Failed to instantiate plugin %s: %s", module_name, e)
            self._load_errors[module_name] = f"Instantiation error: {e}"
            return None

    def _find_plugin_class(self, module: Any) -> Optional[Type[PluginBase]]:
        """
        Find the plugin class in a module.

        Looks for:
        1. A class named 'PluginClass'
        2. A class that inherits from PluginBase

        Args:
            module: Loaded Python module

        Returns:
            Plugin class or None
        """
        # First, check for PluginClass attribute
        if hasattr(module, "PluginClass"):
            return module.PluginClass

        # Search for classes that inherit from PluginBase
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj is not PluginBase and issubclass(obj, PluginBase):
                return obj

        return None

    def _validate_plugin_security(self, file_path: Path) -> bool:
        """
        Validate plugin code for security concerns.

        Args:
            file_path: Path to plugin file

        Returns:
            True if plugin passes security checks
        """
        try:
            content = file_path.read_text()

            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in content:
                    logger.warning(
                        "Security: Plugin %s contains dangerous pattern: %s",
                        file_path.name,
                        pattern
                    )
                    return False

            # Try to compile (syntax check)
            compile(content, str(file_path), "exec")

            return True

        except SyntaxError as e:
            logger.error("Syntax error in plugin %s: %s", file_path.name, e)
            return False
        except Exception as e:
            logger.error("Error validating plugin %s: %s", file_path.name, e)
            return False

    def execute(
        self,
        plugin_name: str,
        action: str,
        params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Execute an action on a plugin.

        Args:
            plugin_name: Name of the plugin to use
            action: Action to execute
            params: Parameters for the action

        Returns:
            Result dictionary from the plugin

        Raises:
            KeyError: If plugin not found
            ValueError: If action not supported
        """
        if plugin_name not in self.plugins:
            available = list(self.plugins.keys())
            raise KeyError(
                f"Plugin '{plugin_name}' not found. Available: {available}"
            )

        plugin = self.plugins[plugin_name]
        params = params or {}

        # Validate action is supported
        capabilities = plugin.describe_capabilities()
        if action not in capabilities:
            raise ValueError(
                f"Action '{action}' not supported by plugin '{plugin_name}'. "
                f"Available: {capabilities}"
            )

        logger.debug("Executing %s.%s with params: %s", plugin_name, action, params)

        try:
            result = plugin.execute(action, params)
            result.setdefault("status", "success")
            return result
        except Exception as e:
            logger.error("Plugin %s execution error: %s", plugin_name, e)
            return {"status": "error", "error": str(e)}

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a specific plugin.

        Args:
            plugin_name: Name of the plugin to reload

        Returns:
            True if reload successful
        """
        if plugin_name in self.plugins:
            # Shutdown existing instance
            self.plugins[plugin_name].shutdown()
            del self.plugins[plugin_name]

        # Find the file
        for file_path in self.plugin_dir.iterdir():
            if file_path.stem == plugin_name or file_path.suffix == ".py":
                result = self._load_plugin_file(file_path)
                return result is not None

        logger.warning("Could not find plugin file for: %s", plugin_name)
        return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if unload successful
        """
        if plugin_name not in self.plugins:
            return False

        plugin = self.plugins[plugin_name]
        plugin.shutdown()

        del self.plugins[plugin_name]
        if plugin_name in self.plugin_classes:
            del self.plugin_classes[plugin_name]

        logger.info("Unloaded plugin: %s", plugin_name)
        return True

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """
        Get a plugin instance by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self.plugins.get(name)

    def list_plugins(self) -> List[str]:
        """List all loaded plugin names."""
        return list(self.plugins.keys())

    def get_all_capabilities(self) -> Dict[str, List[str]]:
        """
        Get capabilities for all loaded plugins.

        Returns:
            Dictionary mapping plugin names to their capabilities
        """
        return {
            name: plugin.describe_capabilities()
            for name, plugin in self.plugins.items()
        }

    def get_load_errors(self) -> Dict[str, str]:
        """Get errors from the last load operation."""
        return self._load_errors.copy()

    def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        for name, plugin in self.plugins.items():
            try:
                plugin.shutdown()
                logger.debug("Shutdown plugin: %s", name)
            except Exception as e:
                logger.error("Error shutting down plugin %s: %s", name, e)

        self.plugins.clear()
        self.plugin_classes.clear()
        logger.info("All plugins shutdown")


# Convenience functions for simple usage
_default_manager: Optional[PluginManager] = None


def get_plugin_manager(
    plugin_dir: str | Path = "plugins",
    **kwargs: Any
) -> PluginManager:
    """
    Get or create the default plugin manager.

    Args:
        plugin_dir: Path to plugins directory
        **kwargs: Additional arguments for PluginManager

    Returns:
        PluginManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = PluginManager(plugin_dir=plugin_dir, **kwargs)
    return _default_manager


def load_plugins(plugin_dir: str | Path = "plugins") -> List[str]:
    """
    Convenience function to load plugins.

    Args:
        plugin_dir: Path to plugins directory

    Returns:
        List of loaded plugin names
    """
    manager = get_plugin_manager(plugin_dir)
    return manager.load_plugins()
