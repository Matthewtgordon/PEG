"""
Tests for APEG LLM role adapters (OpenAI integration).

Tests cover:
- OpenAI client initialization
- All 6 LLM roles (ENGINEER, VALIDATOR, SCORER, CHALLENGER, LOGGER, TESTER)
- Test mode fallback
- Error handling
- JSON response parsing
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

from apeg_core.agents.llm_roles import (
    LLMRoleError,
    run_engineer_role,
    run_validator_role,
    run_scorer_role,
    run_challenger_role,
    run_logger_role,
    run_tester_role,
)


class TestOpenAIClientInitialization:
    """Test OpenAI client initialization and configuration."""

    def test_client_initialization_test_mode(self, monkeypatch):
        """Test that client returns None in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Import after setting env vars
        from apeg_core.agents.llm_roles import _get_openai_client

        client = _get_openai_client()
        assert client is None

    def test_client_initialization_missing_key(self, monkeypatch):
        """Test that missing API key raises error when not in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from apeg_core.agents.llm_roles import _get_openai_client

        with pytest.raises(LLMRoleError, match="OPENAI_API_KEY environment variable not set"):
            _get_openai_client()

    @patch("openai.OpenAI")
    def test_client_initialization_success(self, mock_openai_class, monkeypatch):
        """Test successful client initialization."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        from apeg_core.agents.llm_roles import _get_openai_client

        client = _get_openai_client()
        assert client is not None
        mock_openai_class.assert_called_once_with(api_key="sk-test-key")


class TestEngineerRole:
    """Test ENGINEER role for prompt engineering."""

    def test_engineer_role_test_mode(self, monkeypatch):
        """Test ENGINEER role in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        result = run_engineer_role("Design a product description prompt")
        assert "test mode" in result.lower()
        assert isinstance(result, str)

    @patch("openai.OpenAI")
    def test_engineer_role_real_mode(self, mock_openai_class, monkeypatch):
        """Test ENGINEER role with real API call (mocked)."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Here's a product description prompt..."))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = run_engineer_role("Design a product description prompt")
        assert "product description prompt" in result
        assert isinstance(result, str)

        # Verify API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert len(call_args[1]["messages"]) == 2
        assert call_args[1]["messages"][0]["role"] == "system"
        assert call_args[1]["messages"][1]["role"] == "user"

    def test_engineer_role_with_context(self, monkeypatch):
        """Test ENGINEER role with context dictionary."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        context = {"product_type": "handmade jewelry", "target_audience": "collectors"}
        result = run_engineer_role("Design a prompt", context=context)
        assert isinstance(result, str)


class TestValidatorRole:
    """Test VALIDATOR role for output validation."""

    def test_validator_role_test_mode(self, monkeypatch):
        """Test VALIDATOR role in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        result = run_validator_role(
            prompt="Validate this output",
            output_to_validate="Some output text"
        )
        data = json.loads(result)
        assert "valid" in data
        assert "score" in data
        assert "issues" in data
        assert "recommendations" in data

    @patch("openai.OpenAI")
    def test_validator_role_real_mode(self, mock_openai_class, monkeypatch):
        """Test VALIDATOR role with real API call (mocked)."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "valid": True,
                "score": 0.9,
                "issues": [],
                "recommendations": ["Great output!"]
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = run_validator_role(
            prompt="Validate this output",
            output_to_validate="Well-formatted output"
        )
        data = json.loads(result)
        assert data["valid"] is True
        assert data["score"] == 0.9


class TestScorerRole:
    """Test SCORER role for quality scoring."""

    def test_scorer_role_test_mode(self, monkeypatch):
        """Test SCORER role in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        result = run_scorer_role(
            prompt="Score this output",
            output_to_score="Some output text"
        )
        data = json.loads(result)
        assert "overall_score" in data
        assert "metrics" in data
        assert "feedback" in data

    @patch("openai.OpenAI")
    def test_scorer_role_with_scoring_model(self, mock_openai_class, monkeypatch):
        """Test SCORER role with scoring model metrics."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "overall_score": 0.85,
                "metrics": {
                    "clarity": 0.9,
                    "completeness": 0.8
                },
                "feedback": "Good output with minor issues"
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        scoring_model = {
            "metrics": [
                {"name": "clarity", "description": "Output clarity"},
                {"name": "completeness", "description": "Output completeness"}
            ]
        }

        result = run_scorer_role(
            prompt="Score this output",
            output_to_score="Test output",
            scoring_model=scoring_model
        )
        data = json.loads(result)
        assert 0 <= data["overall_score"] <= 1
        assert "clarity" in data["metrics"]


class TestChallengerRole:
    """Test CHALLENGER role for adversarial testing."""

    def test_challenger_role_test_mode(self, monkeypatch):
        """Test CHALLENGER role in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        result = run_challenger_role(
            prompt="Challenge this logic",
            output_to_challenge="Some logic"
        )
        data = json.loads(result)
        assert "critical_issues" in data
        assert "warnings" in data
        assert "stress_test_results" in data

    @patch("openai.OpenAI")
    def test_challenger_role_real_mode(self, mock_openai_class, monkeypatch):
        """Test CHALLENGER role with real API call (mocked)."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "critical_issues": ["Edge case not handled"],
                "warnings": ["Consider error handling"],
                "stress_test_results": {"edge_cases": "some_failures"}
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = run_challenger_role(
            prompt="Challenge this logic",
            output_to_challenge="if x > 0: return x"
        )
        data = json.loads(result)
        assert isinstance(data["critical_issues"], list)


class TestLoggerRole:
    """Test LOGGER role for audit logging."""

    def test_logger_role_structured_logging(self, monkeypatch):
        """Test LOGGER role with structured logging (no LLM)."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        result = run_logger_role(
            event="workflow_completed",
            details={"duration": 1.5, "score": 0.85}
        )
        data = json.loads(result)
        assert "timestamp" in data
        assert data["event"] == "workflow_completed"
        assert "details" in data

    @patch("openai.OpenAI")
    def test_logger_role_with_llm(self, mock_openai_class, monkeypatch):
        """Test LOGGER role with LLM summarization."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "timestamp": "2025-11-20T12:00:00",
                "event": "workflow_completed",
                "summary": "Workflow completed successfully with high score",
                "details": {"duration": 1.5, "score": 0.85}
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = run_logger_role(
            event="workflow_completed",
            details={"duration": 1.5, "score": 0.85},
            use_llm=True
        )
        data = json.loads(result)
        assert "summary" in data


class TestTesterRole:
    """Test TESTER role for test generation."""

    def test_tester_role_test_mode(self, monkeypatch):
        """Test TESTER role in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        result = run_tester_role(
            prompt="Generate tests for this function",
            code_or_output="def add(a, b): return a + b"
        )
        data = json.loads(result)
        assert "test_cases" in data
        assert "coverage" in data
        assert "recommendations" in data

    @patch("openai.OpenAI")
    def test_tester_role_real_mode(self, mock_openai_class, monkeypatch):
        """Test TESTER role with real API call (mocked)."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "test_cases": [
                    {
                        "name": "test_add_positive",
                        "type": "unit",
                        "description": "Test adding positive numbers"
                    }
                ],
                "coverage": "basic",
                "recommendations": ["Add edge case tests"]
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = run_tester_role(
            prompt="Generate tests",
            code_or_output="def add(a, b): return a + b"
        )
        data = json.loads(result)
        assert len(data["test_cases"]) > 0


class TestErrorHandling:
    """Test error handling across all roles."""

    @patch("openai.OpenAI")
    def test_api_error_handling(self, mock_openai_class, monkeypatch):
        """Test that API errors are properly handled."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI to raise an error
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
        mock_openai_class.return_value = mock_client

        with pytest.raises(LLMRoleError, match="ENGINEER role execution failed"):
            run_engineer_role("Test prompt")

    def test_all_roles_work_in_test_mode(self, monkeypatch):
        """Integration test: verify all roles work in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        # Test all roles return valid responses
        engineer_result = run_engineer_role("Test")
        assert isinstance(engineer_result, str)

        validator_result = run_validator_role("Test", "output")
        assert json.loads(validator_result)["valid"] is not None

        scorer_result = run_scorer_role("Test", "output")
        assert json.loads(scorer_result)["overall_score"] >= 0

        challenger_result = run_challenger_role("Test", "output")
        assert "critical_issues" in json.loads(challenger_result)

        logger_result = run_logger_role("test_event", {"key": "value"})
        assert "event" in json.loads(logger_result)

        tester_result = run_tester_role("Test", "code")
        assert "test_cases" in json.loads(tester_result)
