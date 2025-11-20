"""Tests for BaseAgent abstract base class.

Tests cover:
- Agent initialization
- Configuration management
- Abstract method enforcement
- Logging functionality
"""

import pytest
from typing import Dict, List

from apeg_core.agents.base_agent import BaseAgent


# Concrete implementation for testing
class TestAgent(BaseAgent):
    """Test agent implementation for testing BaseAgent functionality."""

    @property
    def name(self) -> str:
        return "TestAgent"

    def execute(self, action: str, context: Dict) -> Dict:
        """Simple execute implementation for testing."""
        return {"action": action, "context": context, "status": "success"}

    def describe_capabilities(self) -> List[str]:
        """Return test capabilities."""
        return ["test_action_1", "test_action_2", "test_action_3"]


def test_base_agent_initialization():
    """Test agent initialization with and without config."""
    # Without config
    agent1 = TestAgent()
    assert agent1.config == {}
    assert agent1.test_mode is False

    # With config
    config = {"api_key": "test-key", "endpoint": "https://api.example.com"}
    agent2 = TestAgent(config=config, test_mode=True)
    assert agent2.config == config
    assert agent2.test_mode is True


def test_base_agent_config_management():
    """Test configuration get/set methods."""
    agent = TestAgent(config={"initial_key": "initial_value"})

    # Test get_config with existing key
    assert agent.get_config("initial_key") == "initial_value"

    # Test get_config with missing key and default
    assert agent.get_config("missing_key", "default_value") == "default_value"

    # Test set_config
    agent.set_config("new_key", "new_value")
    assert agent.get_config("new_key") == "new_value"

    # Test set_config overwrites existing
    agent.set_config("initial_key", "updated_value")
    assert agent.get_config("initial_key") == "updated_value"


def test_base_agent_abstract_methods():
    """Test that BaseAgent cannot be instantiated directly."""
    # Attempting to instantiate BaseAgent should fail
    with pytest.raises(TypeError):
        BaseAgent()  # type: ignore


def test_base_agent_execute_and_capabilities():
    """Test execute method and describe_capabilities."""
    agent = TestAgent()

    # Test execute
    result = agent.execute("test_action", {"param": "value"})
    assert result["action"] == "test_action"
    assert result["context"] == {"param": "value"}
    assert result["status"] == "success"

    # Test describe_capabilities
    capabilities = agent.describe_capabilities()
    assert len(capabilities) == 3
    assert "test_action_1" in capabilities
    assert "test_action_2" in capabilities
    assert "test_action_3" in capabilities


def test_base_agent_repr():
    """Test string representation of agent."""
    agent = TestAgent()

    repr_str = repr(agent)
    assert "TestAgent" in repr_str
    assert "capabilities=3" in repr_str
