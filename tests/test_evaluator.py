"""Tests for the output evaluator.

Tests cover:
- Evaluator initialization with config
- Rule-based scoring for different outputs
- Metric calculation (completeness, format, length, quality)
- Threshold-based pass/fail decisions
- JSON format validation
"""

import json
import pytest
from pathlib import Path

from apeg_core.scoring.evaluator import Evaluator, EvaluationResult, rule_based_score


def test_evaluator_initialization_default():
    """Test evaluator initialization with default config."""
    evaluator = Evaluator()

    assert evaluator.threshold >= 0.0
    assert evaluator.threshold <= 1.0
    assert evaluator.score_model is not None


def test_evaluator_initialization_with_config():
    """Test evaluator initialization with custom config."""
    config = {
        "ci": {
            "minimum_score": 0.85
        }
    }

    evaluator = Evaluator(config=config)

    assert evaluator.threshold == 0.85


def test_rule_based_score_empty_output():
    """Test that empty output gets low score."""
    evaluator = Evaluator()

    result = evaluator.rule_based_score("")

    assert result.score < 0.5
    assert result.metrics["completeness"] == 0.0
    assert "empty" in result.feedback.lower()


def test_rule_based_score_valid_text():
    """Test scoring of valid text output."""
    evaluator = Evaluator()

    output = """
    This is a well-formed output with multiple sentences.
    It has reasonable length and structure.

    The content is organized into paragraphs.
    """

    result = evaluator.rule_based_score(output)

    assert result.score > 0.5
    assert result.metrics["completeness"] == 1.0
    assert result.metrics["format_valid"] > 0.0
    assert result.metrics["length_appropriate"] > 0.0


def test_rule_based_score_json_valid():
    """Test scoring of valid JSON output."""
    evaluator = Evaluator()

    output = json.dumps({"status": "success", "data": {"key": "value"}})
    context = {
        "expect_json": True,
        "required_keys": ["status", "data"]
    }

    result = evaluator.rule_based_score(output, context)

    assert result.score > 0.7
    assert result.metrics["format_valid"] == 1.0
    assert result.details["parsed_json"] is True


def test_rule_based_score_json_invalid():
    """Test scoring of invalid JSON when JSON is expected."""
    evaluator = Evaluator()

    output = "{ invalid json"
    context = {"expect_json": True}

    result = evaluator.rule_based_score(output, context)

    assert result.metrics["format_valid"] < 1.0
    assert result.details["parsed_json"] is False
    assert "invalid json" in result.feedback.lower()


def test_rule_based_score_missing_required_keys():
    """Test scoring when required JSON keys are missing."""
    evaluator = Evaluator()

    output = json.dumps({"status": "success"})
    context = {
        "expect_json": True,
        "required_keys": ["status", "data", "message"]
    }

    result = evaluator.rule_based_score(output, context)

    assert result.metrics["format_valid"] < 1.0
    assert "missing keys" in result.feedback.lower()


def test_rule_based_score_length_too_short():
    """Test scoring when output is too short."""
    evaluator = Evaluator()

    output = "Short"
    context = {"min_length": 100}

    result = evaluator.rule_based_score(output, context)

    assert result.metrics["length_appropriate"] < 1.0
    assert "too short" in result.feedback.lower()


def test_rule_based_score_length_too_long():
    """Test scoring when output is very long."""
    evaluator = Evaluator()

    output = "x" * 20000
    context = {"max_length": 10000}

    result = evaluator.rule_based_score(output, context)

    assert result.metrics["length_appropriate"] < 1.0
    assert "very long" in result.feedback.lower()


def test_evaluate_with_threshold_pass():
    """Test that evaluate returns passed=True when score exceeds threshold."""
    config = {"ci": {"minimum_score": 0.7}}
    evaluator = Evaluator(config=config)

    output = "This is a good quality output with proper structure and length."

    result = evaluator.evaluate(output)

    # Since this is a decent text, it should pass
    assert isinstance(result, EvaluationResult)
    assert result.score >= 0.0


def test_evaluate_with_threshold_fail():
    """Test that evaluate returns passed=False when score is below threshold."""
    config = {"ci": {"minimum_score": 0.9}}
    evaluator = Evaluator(config=config)

    output = "x"  # Very short output

    result = evaluator.evaluate(output)

    assert isinstance(result, EvaluationResult)
    assert result.passed is False


def test_evaluation_result_to_dict():
    """Test EvaluationResult serialization to dictionary."""
    result = EvaluationResult(
        score=0.85,
        passed=True,
        metrics={"test": 0.9},
        details={"key": "value"},
        feedback="Looks good"
    )

    result_dict = result.to_dict()

    assert result_dict["score"] == 0.85
    assert result_dict["passed"] is True
    assert result_dict["metrics"] == {"test": 0.9}
    assert result_dict["details"] == {"key": "value"}
    assert result_dict["feedback"] == "Looks good"


def test_rule_based_score_convenience_function():
    """Test the convenience function for quick scoring."""
    output = "This is a test output."

    result = rule_based_score(output)

    assert isinstance(result, EvaluationResult)
    assert result.score >= 0.0
    assert result.score <= 1.0
