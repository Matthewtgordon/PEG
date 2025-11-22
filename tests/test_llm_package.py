"""Tests for the APEG LLM package.

Tests cover:
- LLM role definitions and configurations
- AgentsBridge initialization and test mode
- Role execution in test mode
- Scorer and validator convenience methods
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from apeg_core.llm import (
    AgentsBridge,
    AgentsBridgeError,
    LLMRole,
    RoleConfig,
    ROLE_CONFIGS,
)
from apeg_core.llm.roles import get_role_config, list_roles
from apeg_core.llm.agent_bridge import reset_global_bridge, get_global_bridge


class TestLLMRoles:
    """Tests for LLM role definitions."""

    def test_llm_role_enum_values(self):
        """Test that all expected roles are defined."""
        assert LLMRole.ENGINEER.value == "ENGINEER"
        assert LLMRole.VALIDATOR.value == "VALIDATOR"
        assert LLMRole.SCORER.value == "SCORER"
        assert LLMRole.CHALLENGER.value == "CHALLENGER"
        assert LLMRole.LOGGER.value == "LOGGER"
        assert LLMRole.TESTER.value == "TESTER"
        assert LLMRole.TRANSLATOR.value == "TRANSLATOR"
        assert LLMRole.PEG.value == "PEG"

    def test_role_config_structure(self):
        """Test RoleConfig dataclass structure."""
        config = RoleConfig(
            name="TEST",
            description="Test role",
            system_prompt="You are a test agent.",
        )
        assert config.name == "TEST"
        assert config.description == "Test role"
        assert config.model == "gpt-4"  # default
        assert config.temperature == 0.7  # default
        assert config.max_tokens == 2048  # default

    def test_role_config_to_dict(self):
        """Test RoleConfig serialization."""
        config = RoleConfig(
            name="TEST",
            description="Test",
            system_prompt="Test prompt",
        )
        data = config.to_dict()
        assert data["name"] == "TEST"
        assert "system_prompt" in data
        assert "metadata" in data

    def test_all_roles_have_configs(self):
        """Test that all roles have configurations."""
        for role in LLMRole:
            assert role in ROLE_CONFIGS
            config = ROLE_CONFIGS[role]
            assert config.name == role.value

    def test_get_role_config_by_enum(self):
        """Test getting config by enum."""
        config = get_role_config(LLMRole.ENGINEER)
        assert config.name == "ENGINEER"

    def test_get_role_config_by_string(self):
        """Test getting config by string."""
        config = get_role_config("engineer")
        assert config.name == "ENGINEER"

    def test_get_role_config_invalid(self):
        """Test that invalid role raises error."""
        with pytest.raises(ValueError, match="Unknown role"):
            get_role_config("invalid_role")

    def test_list_roles(self):
        """Test listing all available roles."""
        roles = list_roles()
        assert "ENGINEER" in roles
        assert "SCORER" in roles
        assert len(roles) == len(LLMRole)


class TestAgentsBridge:
    """Tests for AgentsBridge class."""

    def setup_method(self):
        """Reset global state before each test."""
        reset_global_bridge()
        # Ensure test mode via environment
        os.environ["APEG_TEST_MODE"] = "true"

    def teardown_method(self):
        """Clean up after each test."""
        os.environ.pop("APEG_TEST_MODE", None)
        reset_global_bridge()

    def test_bridge_initialization(self):
        """Test AgentsBridge initialization."""
        bridge = AgentsBridge()
        assert bridge.test_mode is True
        assert bridge.use_agents_sdk is False

    def test_bridge_config_test_mode(self):
        """Test that config can override test mode."""
        os.environ.pop("APEG_TEST_MODE", None)
        bridge = AgentsBridge(config={"test_mode": True})
        assert bridge.test_mode is True

    def test_run_role_test_mode_engineer(self):
        """Test running ENGINEER role in test mode."""
        bridge = AgentsBridge()
        result = bridge.run_role(LLMRole.ENGINEER, "Design a workflow")

        assert result["success"] is True
        assert result["test_mode"] is True
        assert result["role"] == "ENGINEER"
        assert "content" in result

    def test_run_role_test_mode_scorer(self):
        """Test running SCORER role in test mode."""
        bridge = AgentsBridge()
        result = bridge.run_role(LLMRole.SCORER, "Score this output")

        assert result["success"] is True
        assert "content" in result
        # Scorer returns JSON in test mode
        import json
        data = json.loads(result["content"])
        assert "overall_score" in data

    def test_run_role_test_mode_validator(self):
        """Test running VALIDATOR role in test mode."""
        bridge = AgentsBridge()
        result = bridge.run_role(LLMRole.VALIDATOR, "Validate this")

        assert result["success"] is True
        import json
        data = json.loads(result["content"])
        assert "valid" in data
        assert "score" in data

    def test_run_role_by_string(self):
        """Test running role by string name."""
        bridge = AgentsBridge()
        result = bridge.run_role("engineer", "Test prompt")
        assert result["role"] == "ENGINEER"

    def test_run_role_invalid_role(self):
        """Test that invalid role raises error."""
        bridge = AgentsBridge()
        with pytest.raises(AgentsBridgeError, match="Unknown role"):
            bridge.run_role("invalid", "Test")

    def test_run_scorer_convenience(self):
        """Test run_scorer convenience method."""
        bridge = AgentsBridge()
        result = bridge.run_scorer(
            prompt="Evaluate quality",
            output_to_score="This is some output text",
            metadata={"task_type": "test"}
        )

        assert result["success"] is True
        assert "overall_score" in result

    def test_run_validator_convenience(self):
        """Test run_validator convenience method."""
        bridge = AgentsBridge()
        result = bridge.run_validator(
            prompt="Check format",
            output_to_validate="Some output",
            validation_criteria={"format": "text"}
        )

        assert result["success"] is True
        assert "valid" in result

    def test_get_available_roles(self):
        """Test getting list of available roles."""
        bridge = AgentsBridge()
        roles = bridge.get_available_roles()
        assert "ENGINEER" in roles
        assert "SCORER" in roles

    def test_global_bridge_singleton(self):
        """Test global bridge singleton behavior."""
        bridge1 = get_global_bridge()
        bridge2 = get_global_bridge()
        assert bridge1 is bridge2

    def test_reset_global_bridge(self):
        """Test resetting global bridge."""
        bridge1 = get_global_bridge()
        reset_global_bridge()
        bridge2 = get_global_bridge()
        assert bridge1 is not bridge2


class TestAgentsBridgeRealMode:
    """Tests for AgentsBridge in non-test mode (mocked API)."""

    def setup_method(self):
        """Reset global state."""
        reset_global_bridge()
        os.environ.pop("APEG_TEST_MODE", None)

    def teardown_method(self):
        """Clean up."""
        os.environ.pop("APEG_TEST_MODE", None)
        os.environ.pop("OPENAI_API_KEY", None)
        reset_global_bridge()

    def test_bridge_real_mode_without_key(self):
        """Test that real mode without API key falls back gracefully."""
        # Remove any existing key
        os.environ.pop("OPENAI_API_KEY", None)

        # Should not raise during initialization
        bridge = AgentsBridge(config={"test_mode": False})
        assert bridge.test_mode is False

    @patch("apeg_core.llm.agent_bridge.AgentsBridge._get_openai_client")
    def test_bridge_real_mode_with_mock_client(self, mock_get_client):
        """Test real mode with mocked OpenAI client."""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": "Mocked response",
            "usage": {"total_tokens": 100}
        }
        mock_get_client.return_value = mock_client

        bridge = AgentsBridge(config={"test_mode": False})
        # Force real mode by clearing test_mode
        bridge.test_mode = False
        bridge.use_agents_sdk = False

        result = bridge.run_role(LLMRole.ENGINEER, "Test prompt")

        assert result["success"] is True
        assert result["content"] == "Mocked response"
        assert result["test_mode"] is False
