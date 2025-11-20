"""
Tests for enhanced scoring with LLM integration.

Tests the hybrid scoring system that combines rule-based heuristics
with LLM-based quality assessment using the SCORER role.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

from apeg_core.scoring.evaluator import Evaluator, EvaluationResult


class TestHybridScoring:
    """Test hybrid scoring with LLM integration."""

    def test_hybrid_score_test_mode(self, monkeypatch):
        """Test that hybrid scoring uses rule-based only in test mode."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        evaluator = Evaluator()
        result = evaluator.hybrid_score("This is a test output with good quality.")

        # Should use rule-based only
        assert "llm_scoring_used" not in result.details
        assert result.score > 0

    def test_hybrid_score_llm_disabled_env(self, monkeypatch):
        """Test that hybrid scoring respects APEG_USE_LLM_SCORING=false."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("APEG_USE_LLM_SCORING", "false")

        evaluator = Evaluator()
        result = evaluator.hybrid_score("This is a test output.")

        # Should use rule-based only
        assert "llm_scoring_used" not in result.details

    @patch("openai.OpenAI")
    def test_hybrid_score_with_llm(self, mock_openai_class, monkeypatch):
        """Test hybrid scoring with LLM enabled."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("APEG_USE_LLM_SCORING", "true")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("APEG_RULE_WEIGHT", "0.6")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "overall_score": 0.9,
                "metrics": {
                    "semantic_relevance": 0.95,
                    "clarity": 0.85
                },
                "feedback": "High quality output with clear structure"
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        evaluator = Evaluator()
        result = evaluator.hybrid_score("This is a high-quality test output with excellent structure and clarity.")

        # Should use hybrid scoring
        assert result.details["llm_scoring_used"] is True
        assert "llm_score" in result.metrics
        assert "rule_score" in result.metrics
        assert result.details["rule_weight"] == 0.6
        assert result.details["llm_weight"] == 0.4

        # Score should be weighted combination
        # If rule score is ~0.8 and LLM score is 0.9:
        # combined = 0.8 * 0.6 + 0.9 * 0.4 = 0.48 + 0.36 = 0.84
        assert 0.5 <= result.score <= 1.0

    @patch("openai.OpenAI")
    def test_hybrid_score_llm_fallback(self, mock_openai_class, monkeypatch):
        """Test graceful fallback when LLM scoring fails."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("APEG_USE_LLM_SCORING", "true")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI to raise an error
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_client

        evaluator = Evaluator()
        result = evaluator.hybrid_score("Test output")

        # Should fallback to rule-based
        assert "llm_scoring_attempted" in result.details
        assert "llm_scoring_error" in result.details
        assert "llm_scoring_used" not in result.details
        assert result.score > 0  # Rule-based score should still work

    def test_should_use_llm_scoring_logic(self, monkeypatch):
        """Test _should_use_llm_scoring decision logic."""
        evaluator = Evaluator()

        # Test mode always disables LLM
        monkeypatch.setenv("APEG_TEST_MODE", "true")
        monkeypatch.setenv("APEG_USE_LLM_SCORING", "true")
        assert evaluator._should_use_llm_scoring() is False

        # Explicit disable via env
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("APEG_USE_LLM_SCORING", "false")
        assert evaluator._should_use_llm_scoring() is False

        # Explicit enable via env
        monkeypatch.setenv("APEG_USE_LLM_SCORING", "true")
        assert evaluator._should_use_llm_scoring() is True

        # Default from config
        monkeypatch.delenv("APEG_USE_LLM_SCORING", raising=False)
        evaluator_with_config = Evaluator(config={"use_llm_scoring": True})
        assert evaluator_with_config._should_use_llm_scoring() is True

    def test_get_rule_weight(self, monkeypatch):
        """Test _get_rule_weight configuration."""
        # Default weight
        evaluator = Evaluator()
        assert evaluator._get_rule_weight() == 0.6

        # From environment
        monkeypatch.setenv("APEG_RULE_WEIGHT", "0.7")
        assert evaluator._get_rule_weight() == 0.7

        # From config
        evaluator_with_config = Evaluator(config={"rule_weight": 0.5})
        monkeypatch.delenv("APEG_RULE_WEIGHT", raising=False)
        assert evaluator_with_config._get_rule_weight() == 0.5

        # Invalid env var falls back to config/default
        monkeypatch.setenv("APEG_RULE_WEIGHT", "invalid")
        assert evaluator._get_rule_weight() == 0.6

    @patch("openai.OpenAI")
    def test_hybrid_score_feedback_combination(self, mock_openai_class, monkeypatch):
        """Test that feedback from both sources is combined."""
        monkeypatch.setenv("APEG_TEST_MODE", "false")
        monkeypatch.setenv("APEG_USE_LLM_SCORING", "true")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "overall_score": 0.85,
                "metrics": {},
                "feedback": "LLM says: Good quality"
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        evaluator = Evaluator()
        result = evaluator.hybrid_score("Test output with sufficient length for validation.")

        # Feedback should contain both rule-based and LLM feedback
        assert "Rule-based:" in result.feedback
        assert "LLM assessment:" in result.feedback
        assert "Good quality" in result.feedback

    def test_integration_with_evaluate_method(self, monkeypatch):
        """Test that evaluate() method uses hybrid_score when configured."""
        monkeypatch.setenv("APEG_TEST_MODE", "true")

        evaluator = Evaluator()
        # The evaluate() method calls hybrid_score internally
        result = evaluator.evaluate("Test output for evaluation")

        assert isinstance(result, EvaluationResult)
        assert result.score >= 0.0
        assert result.score <= 1.0
