"""
Tests for OpenAI Agents SDK Adapter.

This module tests the integration between APEG and the OpenAI Agents SDK,
including test mode, role mapping, session management, and error handling.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Import the adapter components
from apeg_core.llm.openai_agents_adapter import (
    OpenAIAgentsAdapter,
    AgentMode,
    AgentRunResult,
    APEGAgentConfig,
    get_adapter,
    reset_adapter,
    _AGENTS_SDK_AVAILABLE,
)
from apeg_core.llm.roles import LLMRole, get_role_config


class TestAgentMode:
    """Tests for AgentMode enum."""

    def test_agent_mode_values(self):
        """Test that all mode values are defined."""
        assert AgentMode.SDK.value == "sdk"
        assert AgentMode.API.value == "api"
        assert AgentMode.TEST.value == "test"
        assert AgentMode.HYBRID.value == "hybrid"

    def test_agent_mode_from_string(self):
        """Test creating mode from string."""
        assert AgentMode("sdk") == AgentMode.SDK
        assert AgentMode("test") == AgentMode.TEST


class TestAgentRunResult:
    """Tests for AgentRunResult dataclass."""

    def test_basic_result(self):
        """Test creating a basic result."""
        result = AgentRunResult(
            content="Test response",
            role="ENGINEER",
            model="gpt-4",
            success=True,
        )

        assert result.content == "Test response"
        assert result.role == "ENGINEER"
        assert result.model == "gpt-4"
        assert result.success is True
        assert result.test_mode is False

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = AgentRunResult(
            content="Test",
            role="SCORER",
            model="gpt-4",
            success=True,
            test_mode=True,
            metadata={"key": "value"},
        )

        d = result.to_dict()
        assert d["content"] == "Test"
        assert d["role"] == "SCORER"
        assert d["success"] is True
        assert d["test_mode"] is True
        assert d["metadata"]["key"] == "value"


class TestOpenAIAgentsAdapterInit:
    """Tests for adapter initialization."""

    def test_default_init(self):
        """Test default initialization."""
        adapter = OpenAIAgentsAdapter()
        assert adapter.config == {}
        assert adapter.mode == AgentMode.HYBRID

    def test_init_with_config(self):
        """Test initialization with config."""
        config = {"session_dir": "/tmp/sessions", "mode": "api"}
        adapter = OpenAIAgentsAdapter(config=config)

        assert adapter.config == config
        assert adapter.session_dir == "/tmp/sessions"
        assert adapter.mode == AgentMode.API

    def test_init_with_mode_override(self):
        """Test that mode parameter overrides config."""
        config = {"mode": "sdk"}
        adapter = OpenAIAgentsAdapter(config=config, mode=AgentMode.TEST)
        assert adapter.mode == AgentMode.TEST

    def test_test_mode_from_env(self):
        """Test that APEG_TEST_MODE env var forces test mode."""
        with patch.dict(os.environ, {"APEG_TEST_MODE": "true"}):
            adapter = OpenAIAgentsAdapter(config={"mode": "sdk"})
            assert adapter.mode == AgentMode.TEST

    def test_sdk_available_check(self):
        """Test SDK availability check."""
        adapter = OpenAIAgentsAdapter()
        # Should return True if SDK is installed, False otherwise
        assert adapter.is_sdk_available() == _AGENTS_SDK_AVAILABLE


class TestTestModeResponses:
    """Tests for test mode responses."""

    @pytest.fixture
    def adapter(self):
        """Create adapter in test mode."""
        return OpenAIAgentsAdapter(mode=AgentMode.TEST)

    def test_engineer_test_response(self, adapter):
        """Test ENGINEER role returns appropriate test response."""
        result = adapter.run_agent(
            LLMRole.ENGINEER,
            "Design a workflow",
            context={"task": "test"}
        )

        assert result.success
        assert result.test_mode
        assert result.role == "ENGINEER"
        assert "ENGINEER" in result.content or "Design" in result.content

    def test_scorer_test_response(self, adapter):
        """Test SCORER role returns JSON with score."""
        result = adapter.run_agent(
            LLMRole.SCORER,
            "Score this output",
            context={"output": "test"}
        )

        assert result.success
        assert result.test_mode

        content = json.loads(result.content)
        assert "overall_score" in content
        assert 0 <= content["overall_score"] <= 1
        assert "metrics" in content
        assert "feedback" in content

    def test_validator_test_response(self, adapter):
        """Test VALIDATOR role returns JSON with validation result."""
        result = adapter.run_agent(
            LLMRole.VALIDATOR,
            "Validate this",
            context={"data": "test"}
        )

        assert result.success
        assert result.test_mode

        content = json.loads(result.content)
        assert "valid" in content
        assert "score" in content
        assert "issues" in content

    def test_challenger_test_response(self, adapter):
        """Test CHALLENGER role returns JSON with issues."""
        result = adapter.run_agent(
            LLMRole.CHALLENGER,
            "Challenge this logic",
            context={}
        )

        assert result.success
        content = json.loads(result.content)
        assert "critical_issues" in content
        assert "warnings" in content
        assert "edge_cases" in content

    def test_tester_test_response(self, adapter):
        """Test TESTER role returns JSON with test cases."""
        result = adapter.run_agent(
            LLMRole.TESTER,
            "Generate tests",
            context={}
        )

        assert result.success
        content = json.loads(result.content)
        assert "test_cases" in content
        assert "coverage" in content

    def test_all_roles_work_in_test_mode(self, adapter):
        """Test that all LLM roles work in test mode."""
        for role in LLMRole:
            result = adapter.run_agent(role, "Test prompt")
            assert result.success, f"Role {role} failed"
            assert result.test_mode, f"Role {role} not in test mode"
            assert result.role == role.value


class TestRoleStringConversion:
    """Tests for role string to enum conversion."""

    @pytest.fixture
    def adapter(self):
        return OpenAIAgentsAdapter(mode=AgentMode.TEST)

    def test_role_as_string(self, adapter):
        """Test passing role as string."""
        result = adapter.run_agent("ENGINEER", "Test")
        assert result.role == "ENGINEER"

    def test_role_as_string_lowercase(self, adapter):
        """Test passing role as lowercase string."""
        result = adapter.run_agent("scorer", "Test")
        assert result.role == "SCORER"

    def test_role_as_enum(self, adapter):
        """Test passing role as enum."""
        result = adapter.run_agent(LLMRole.VALIDATOR, "Test")
        assert result.role == "VALIDATOR"

    def test_invalid_role_string(self, adapter):
        """Test that invalid role string raises error."""
        with pytest.raises(ValueError):
            adapter.run_agent("INVALID_ROLE", "Test")


class TestContextHandling:
    """Tests for context handling in agent calls."""

    @pytest.fixture
    def adapter(self):
        return OpenAIAgentsAdapter(mode=AgentMode.TEST)

    def test_none_context(self, adapter):
        """Test handling None context."""
        result = adapter.run_agent(LLMRole.ENGINEER, "Test", context=None)
        assert result.success

    def test_empty_context(self, adapter):
        """Test handling empty context."""
        result = adapter.run_agent(LLMRole.ENGINEER, "Test", context={})
        assert result.success

    def test_complex_context(self, adapter):
        """Test handling complex nested context."""
        context = {
            "task": "sync",
            "sources": ["shopify", "etsy"],
            "config": {
                "retry": True,
                "timeout": 30,
            },
            "items": [1, 2, 3],
        }
        result = adapter.run_agent(LLMRole.ENGINEER, "Test", context=context)
        assert result.success


class TestGlobalAdapter:
    """Tests for global adapter singleton."""

    def setup_method(self):
        """Reset global adapter before each test."""
        reset_adapter()

    def test_get_adapter_creates_instance(self):
        """Test that get_adapter creates instance on first call."""
        adapter = get_adapter()
        assert isinstance(adapter, OpenAIAgentsAdapter)

    def test_get_adapter_returns_same_instance(self):
        """Test that get_adapter returns same instance."""
        adapter1 = get_adapter()
        adapter2 = get_adapter()
        assert adapter1 is adapter2

    def test_reset_adapter(self):
        """Test that reset_adapter clears the instance."""
        adapter1 = get_adapter()
        reset_adapter()
        adapter2 = get_adapter()
        assert adapter1 is not adapter2


class TestConfigSummary:
    """Tests for configuration summary."""

    def test_get_config_summary(self):
        """Test getting config summary."""
        adapter = OpenAIAgentsAdapter(
            config={"session_dir": "/tmp/test"},
            mode=AgentMode.TEST
        )

        summary = adapter.get_config_summary()

        assert summary["mode"] == "test"
        assert summary["session_dir"] == "/tmp/test"
        assert "sdk_available" in summary
        assert "cached_agents" in summary
        assert "active_sessions" in summary


class TestMetadataInResults:
    """Tests for metadata included in results."""

    @pytest.fixture
    def adapter(self):
        return OpenAIAgentsAdapter(mode=AgentMode.TEST)

    def test_timestamp_in_metadata(self, adapter):
        """Test that timestamp is included in metadata."""
        result = adapter.run_agent(LLMRole.ENGINEER, "Test")
        assert "timestamp" in result.metadata

    def test_prompt_preview_in_metadata(self, adapter):
        """Test that prompt preview is included in metadata."""
        long_prompt = "A" * 200
        result = adapter.run_agent(LLMRole.ENGINEER, long_prompt)

        assert "prompt_preview" in result.metadata
        assert len(result.metadata["prompt_preview"]) <= 100


class TestSessionManagement:
    """Tests for session management."""

    @pytest.fixture
    def adapter(self):
        return OpenAIAgentsAdapter(
            config={"session_dir": "/tmp/test_sessions"},
            mode=AgentMode.TEST
        )

    def test_run_with_session_id(self, adapter):
        """Test running with session ID."""
        result = adapter.run_agent(
            LLMRole.ENGINEER,
            "Test",
            session_id="test_session_123"
        )
        assert result.success

    def test_clear_session(self, adapter):
        """Test clearing a session."""
        # Run with session to create it
        adapter.run_agent(LLMRole.ENGINEER, "Test", session_id="to_clear")

        # Clear should not raise
        adapter.clear_session("to_clear")

    def test_clear_nonexistent_session(self, adapter):
        """Test clearing a session that doesn't exist."""
        # Should not raise
        adapter.clear_session("nonexistent")


# Skip SDK-specific tests if SDK not available
@pytest.mark.skipif(not _AGENTS_SDK_AVAILABLE, reason="OpenAI Agents SDK not installed")
class TestSDKIntegration:
    """Tests that require the actual SDK to be installed."""

    def test_agent_creation(self):
        """Test creating an agent from a role."""
        adapter = OpenAIAgentsAdapter(mode=AgentMode.HYBRID)
        agent = adapter.get_or_create_agent(LLMRole.ENGINEER)

        assert agent is not None
        assert hasattr(agent, 'name')
        assert "ENGINEER" in agent.name

    def test_agent_caching(self):
        """Test that agents are cached."""
        adapter = OpenAIAgentsAdapter(mode=AgentMode.HYBRID)

        agent1 = adapter.get_or_create_agent(LLMRole.ENGINEER)
        agent2 = adapter.get_or_create_agent(LLMRole.ENGINEER)

        assert agent1 is agent2

    def test_different_roles_different_agents(self):
        """Test that different roles create different agents."""
        adapter = OpenAIAgentsAdapter(mode=AgentMode.HYBRID)

        engineer = adapter.get_or_create_agent(LLMRole.ENGINEER)
        scorer = adapter.get_or_create_agent(LLMRole.SCORER)

        assert engineer is not scorer

    def test_orchestrator_creation(self):
        """Test creating an orchestrator agent with handoffs."""
        adapter = OpenAIAgentsAdapter(mode=AgentMode.HYBRID)

        orchestrator = adapter.create_orchestrator_agent(
            name="Test-Orchestrator",
            specialist_roles=[LLMRole.ENGINEER, LLMRole.VALIDATOR]
        )

        assert orchestrator is not None
        assert len(orchestrator.handoffs) > 0


# Integration tests that require API key
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
@pytest.mark.skipif(
    not _AGENTS_SDK_AVAILABLE,
    reason="OpenAI Agents SDK not installed"
)
class TestRealAPIIntegration:
    """Tests that make real API calls."""

    @pytest.mark.asyncio
    async def test_real_agent_execution(self):
        """Test real agent execution (async)."""
        adapter = OpenAIAgentsAdapter(mode=AgentMode.SDK)

        result = await adapter.run_agent_async(
            LLMRole.ENGINEER,
            "Say 'Hello' in exactly one word."
        )

        assert result.success
        assert not result.test_mode
        assert len(result.content) > 0

    def test_real_agent_execution_sync(self):
        """Test real agent execution (sync)."""
        adapter = OpenAIAgentsAdapter(mode=AgentMode.SDK)

        result = adapter.run_agent(
            LLMRole.ENGINEER,
            "Say 'Hello' in exactly one word."
        )

        assert result.success
        assert not result.test_mode
        assert len(result.content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
