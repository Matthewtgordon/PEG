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


class TestAgentsBridgeAgentsSDK:
    """Tests for AgentsBridge Agents SDK integration."""

    def setup_method(self):
        """Reset global state."""
        reset_global_bridge()
        os.environ.pop("APEG_TEST_MODE", None)

    def teardown_method(self):
        """Clean up."""
        os.environ.pop("APEG_TEST_MODE", None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("APEG_USE_AGENTS_SDK", None)
        os.environ.pop("OPENAI_PROJECT_ID", None)
        reset_global_bridge()

    def test_agents_sdk_fallback_on_import_error(self):
        """Test that Agents SDK falls back on ImportError."""
        bridge = AgentsBridge(config={
            "test_mode": False,
            "use_openai_agents": True
        })
        bridge.test_mode = False
        bridge.use_agents_sdk = True

        # The SDK call should fail and fall back to OpenAI API
        # We'll mock the _get_openai_client to avoid real API calls
        with patch.object(bridge, "_run_via_agents_sdk") as mock_sdk:
            mock_sdk.side_effect = ImportError("OpenAI SDK not available")
            with patch.object(bridge, "_run_via_openai_api") as mock_api:
                mock_api.return_value = {
                    "content": "API fallback",
                    "role": "ENGINEER",
                    "model": "gpt-4",
                    "success": True,
                    "test_mode": False,
                    "metadata": {}
                }
                result = bridge.run_role(LLMRole.ENGINEER, "Test")
                assert result["content"] == "API fallback"

    def test_agents_sdk_fallback_on_runtime_error(self):
        """Test that Agents SDK falls back on runtime errors."""
        bridge = AgentsBridge(config={
            "test_mode": False,
            "use_openai_agents": True
        })
        bridge.test_mode = False
        bridge.use_agents_sdk = True

        with patch.object(bridge, "_run_via_agents_sdk") as mock_sdk:
            mock_sdk.side_effect = RuntimeError("Agent run failed")
            with patch.object(bridge, "_run_via_openai_api") as mock_api:
                mock_api.return_value = {
                    "content": "API fallback after error",
                    "role": "ENGINEER",
                    "model": "gpt-4",
                    "success": True,
                    "test_mode": False,
                    "metadata": {}
                }
                result = bridge.run_role(LLMRole.ENGINEER, "Test")
                assert result["content"] == "API fallback after error"

    @patch("apeg_core.llm.agent_bridge.os.environ.get")
    def test_agents_sdk_no_api_key(self, mock_env_get):
        """Test Agents SDK raises error without API key."""
        # Mock env to return None for API key
        def env_side_effect(key, default=None):
            if key == "OPENAI_API_KEY":
                return None
            if key == "OPENAI_PROJECT_ID":
                return "test-project"
            return default

        mock_env_get.side_effect = env_side_effect

        bridge = AgentsBridge(config={
            "test_mode": False,
            "use_openai_agents": True
        })
        bridge.test_mode = False
        bridge.use_agents_sdk = True

        # Should fall back to API (which will also fail without key)
        with patch.object(bridge, "_run_via_openai_api") as mock_api:
            mock_api.return_value = {
                "content": "fallback",
                "role": "ENGINEER",
                "model": "gpt-4",
                "success": True,
                "test_mode": False,
                "metadata": {}
            }
            result = bridge.run_role(LLMRole.ENGINEER, "Test")
            # Should successfully fall back
            assert result["success"] is True

    def test_agents_sdk_successful_execution(self):
        """Test Agents SDK successful execution with mocked client."""
        # Set up environment
        os.environ["OPENAI_API_KEY"] = "test-key"

        bridge = AgentsBridge(config={
            "test_mode": False,
            "use_openai_agents": True
        })
        bridge.test_mode = False
        bridge.use_agents_sdk = True

        # We need to patch OpenAI within the _run_via_agents_sdk method
        with patch("openai.OpenAI") as mock_openai_class:
            # Create mock objects for the entire flow
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            # Mock assistant
            mock_assistant = MagicMock()
            mock_assistant.id = "asst_123"
            mock_client.beta.assistants.create.return_value = mock_assistant
            mock_client.beta.assistants.delete.return_value = None

            # Mock thread
            mock_thread = MagicMock()
            mock_thread.id = "thread_123"
            mock_client.beta.threads.create.return_value = mock_thread

            # Mock message creation
            mock_client.beta.threads.messages.create.return_value = MagicMock()

            # Mock run
            mock_run = MagicMock()
            mock_run.id = "run_123"
            mock_run.status = "completed"
            mock_run.usage = MagicMock()
            mock_run.usage.prompt_tokens = 100
            mock_run.usage.completion_tokens = 50
            mock_client.beta.threads.runs.create_and_poll.return_value = mock_run

            # Mock messages
            mock_text = MagicMock()
            mock_text.value = "Agent response content"
            mock_content = MagicMock()
            mock_content.text = mock_text
            mock_message = MagicMock()
            mock_message.role = "assistant"
            mock_message.content = [mock_content]
            mock_messages = MagicMock()
            mock_messages.data = [mock_message]
            mock_client.beta.threads.messages.list.return_value = mock_messages

            result = bridge._run_via_agents_sdk(
                LLMRole.ENGINEER,
                get_role_config(LLMRole.ENGINEER),
                "Design a workflow",
                {"task": "test"}
            )

            assert result["success"] is True
            assert result["content"] == "Agent response content"
            assert result["metadata"]["backend"] == "agents_sdk"
            assert result["metadata"]["assistant_id"] == "asst_123"

    def test_agents_sdk_disabled_by_default(self):
        """Test that Agents SDK is disabled by default."""
        bridge = AgentsBridge()
        assert bridge.use_agents_sdk is False

    def test_agents_sdk_enabled_by_config(self):
        """Test that Agents SDK can be enabled by config."""
        os.environ.pop("APEG_TEST_MODE", None)
        bridge = AgentsBridge(config={
            "test_mode": False,
            "use_openai_agents": True
        })
        # Test mode being False doesn't force use_agents_sdk to True
        # It's only True if config says so AND test_mode is False
        assert bridge.use_agents_sdk is True

    def test_agents_sdk_disabled_in_test_mode(self):
        """Test that Agents SDK is disabled when test_mode is True."""
        os.environ["APEG_TEST_MODE"] = "true"
        bridge = AgentsBridge(config={"use_openai_agents": True})
        # Even if config enables it, test_mode disables Agents SDK
        assert bridge.use_agents_sdk is False

    def test_agents_sdk_enabled_by_env(self):
        """Test that Agents SDK can be enabled by environment variable."""
        os.environ.pop("APEG_TEST_MODE", None)
        os.environ["APEG_USE_AGENTS_SDK"] = "true"
        bridge = AgentsBridge(config={"test_mode": False})
        assert bridge.use_agents_sdk is True
