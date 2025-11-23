"""
Tests for PluginManager - Dynamic plugin loading and management.

Tests include:
- Plugin loading and discovery
- Plugin execution
- Security validation
- Plugin lifecycle
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock

from apeg_core.connectors.plugin_manager import (
    PluginManager,
    PluginBase,
    get_plugin_manager,
)


class TestPluginBase:
    """Tests for PluginBase abstract class."""

    def test_plugin_base_requires_implementation(self):
        """Test that PluginBase requires implementation of abstract methods."""
        with pytest.raises(TypeError):
            PluginBase()

    def test_concrete_plugin_implementation(self):
        """Test creating a concrete plugin implementation."""

        class ConcretePlugin(PluginBase):
            @property
            def name(self):
                return "concrete"

            def execute(self, action, params):
                return {"status": "success", "action": action}

            def describe_capabilities(self):
                return ["action1", "action2"]

        plugin = ConcretePlugin()
        assert plugin.name == "concrete"
        assert plugin.initialize() is True
        assert "action1" in plugin.describe_capabilities()


class TestPluginManager:
    """Tests for PluginManager."""

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create a temporary plugin directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_plugin_dir):
        """Create a PluginManager with temp directory."""
        return PluginManager(
            plugin_dir=temp_plugin_dir,
            validate_security=True
        )

    def test_manager_initialization(self, manager, temp_plugin_dir):
        """Test PluginManager initialization."""
        assert manager.plugin_dir == temp_plugin_dir
        assert manager.plugins == {}
        assert manager.validate_security is True

    def test_load_plugins_empty_dir(self, manager):
        """Test loading from empty directory."""
        loaded = manager.load_plugins()
        assert loaded == []

    def test_load_plugins_missing_dir(self):
        """Test loading from non-existent directory."""
        manager = PluginManager(plugin_dir="nonexistent_dir_xyz")
        loaded = manager.load_plugins()
        assert loaded == []

    def test_load_valid_plugin(self, temp_plugin_dir, manager):
        """Test loading a valid plugin."""
        plugin_code = '''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "test_plugin"

    def execute(self, action, params):
        return {"status": "success", "action": action}

    def describe_capabilities(self):
        return ["do_something"]
'''
        plugin_file = temp_plugin_dir / "test_plugin.py"
        plugin_file.write_text(plugin_code)

        loaded = manager.load_plugins()

        assert "test_plugin" in loaded
        assert "test_plugin" in manager.plugins

    def test_execute_plugin(self, temp_plugin_dir, manager):
        """Test executing a plugin action."""
        plugin_code = '''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "exec_test"

    def execute(self, action, params):
        if action == "greet":
            return {"status": "success", "message": f"Hello, {params.get('name', 'World')}!"}
        return {"status": "error", "error": "Unknown action"}

    def describe_capabilities(self):
        return ["greet"]
'''
        plugin_file = temp_plugin_dir / "exec_test.py"
        plugin_file.write_text(plugin_code)

        manager.load_plugins()
        result = manager.execute("exec_test", "greet", {"name": "Test"})

        assert result["status"] == "success"
        assert result["message"] == "Hello, Test!"

    def test_execute_unknown_plugin(self, manager):
        """Test executing on unknown plugin raises KeyError."""
        with pytest.raises(KeyError):
            manager.execute("nonexistent_plugin", "action", {})

    def test_execute_unknown_action(self, temp_plugin_dir, manager):
        """Test executing unknown action raises ValueError."""
        plugin_code = '''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "limited_plugin"

    def execute(self, action, params):
        return {"status": "success"}

    def describe_capabilities(self):
        return ["only_action"]
'''
        plugin_file = temp_plugin_dir / "limited.py"
        plugin_file.write_text(plugin_code)

        manager.load_plugins()

        with pytest.raises(ValueError):
            manager.execute("limited_plugin", "unknown_action", {})

    def test_security_validation_rejects_eval(self, temp_plugin_dir, manager):
        """Test that plugins with eval() are rejected."""
        dangerous_code = '''
class PluginClass:
    name = "dangerous"
    def execute(self, action, params):
        return eval("1+1")
    def describe_capabilities(self):
        return ["eval_action"]
'''
        plugin_file = temp_plugin_dir / "dangerous.py"
        plugin_file.write_text(dangerous_code)

        loaded = manager.load_plugins()

        assert "dangerous" not in loaded

    def test_unload_plugin(self, temp_plugin_dir, manager):
        """Test unloading a plugin."""
        plugin_code = '''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "unload_test"

    def execute(self, action, params):
        return {}

    def describe_capabilities(self):
        return []
'''
        plugin_file = temp_plugin_dir / "unload_test.py"
        plugin_file.write_text(plugin_code)

        manager.load_plugins()
        assert "unload_test" in manager.plugins

        manager.unload_plugin("unload_test")
        assert "unload_test" not in manager.plugins

    def test_list_plugins(self, temp_plugin_dir, manager):
        """Test listing loaded plugins."""
        for name in ["plugin_a", "plugin_b"]:
            plugin_code = f'''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "{name}"

    def execute(self, action, params):
        return {{}}

    def describe_capabilities(self):
        return []
'''
            plugin_file = temp_plugin_dir / f"{name}.py"
            plugin_file.write_text(plugin_code)

        manager.load_plugins()
        plugins = manager.list_plugins()

        assert "plugin_a" in plugins
        assert "plugin_b" in plugins

    def test_get_all_capabilities(self, temp_plugin_dir, manager):
        """Test getting capabilities for all plugins."""
        plugin_code = '''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "cap_test"

    def execute(self, action, params):
        return {}

    def describe_capabilities(self):
        return ["cap1", "cap2", "cap3"]
'''
        plugin_file = temp_plugin_dir / "cap_test.py"
        plugin_file.write_text(plugin_code)

        manager.load_plugins()
        caps = manager.get_all_capabilities()

        assert "cap_test" in caps
        assert caps["cap_test"] == ["cap1", "cap2", "cap3"]

    def test_shutdown_all(self, temp_plugin_dir, manager):
        """Test shutting down all plugins."""
        plugin_code = '''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "shutdown_test"

    def execute(self, action, params):
        return {}

    def describe_capabilities(self):
        return []
'''
        plugin_file = temp_plugin_dir / "shutdown_test.py"
        plugin_file.write_text(plugin_code)

        manager.load_plugins()
        assert len(manager.plugins) > 0

        manager.shutdown_all()
        assert len(manager.plugins) == 0

    def test_get_plugin(self, temp_plugin_dir, manager):
        """Test getting a specific plugin instance."""
        plugin_code = '''
from apeg_core.connectors.plugin_manager import PluginBase

class PluginClass(PluginBase):
    @property
    def name(self):
        return "get_test"

    def execute(self, action, params):
        return {}

    def describe_capabilities(self):
        return []
'''
        plugin_file = temp_plugin_dir / "get_test.py"
        plugin_file.write_text(plugin_code)

        manager.load_plugins()
        plugin = manager.get_plugin("get_test")

        assert plugin is not None
        assert plugin.name == "get_test"

    def test_get_plugin_nonexistent(self, manager):
        """Test getting nonexistent plugin returns None."""
        plugin = manager.get_plugin("nonexistent")
        assert plugin is None
