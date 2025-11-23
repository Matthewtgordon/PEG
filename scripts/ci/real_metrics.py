#!/usr/bin/env python3
"""
Real metric implementations for CI/CD quality scoring.

This module provides actual metric calculations to replace placeholder
random values in run_scoring.py. Each metric function analyzes real
artifacts and returns a score between 0.0 and 1.0.
"""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def calculate_test_pass_rate(results_path: Path | None = None) -> float:
    """
    Calculate actual test pass rate from pytest JUnit XML results.

    Args:
        results_path: Path to JUnit XML results file.
                     Defaults to test-results/results.xml

    Returns:
        Float between 0.0 and 1.0 representing pass rate.
    """
    if results_path is None:
        results_path = Path("test-results/results.xml")

    if not results_path.exists():
        # Try alternate location
        results_path = Path("test-results.xml")
        if not results_path.exists():
            return 0.0

    try:
        tree = ET.parse(results_path)
        root = tree.getroot()

        # Handle both testsuite and testsuites root elements
        if root.tag == "testsuites":
            total = sum(int(ts.get("tests", 0)) for ts in root.findall("testsuite"))
            failures = sum(
                int(ts.get("failures", 0)) for ts in root.findall("testsuite")
            )
            errors = sum(int(ts.get("errors", 0)) for ts in root.findall("testsuite"))
        else:
            total = int(root.get("tests", 0))
            failures = int(root.get("failures", 0))
            errors = int(root.get("errors", 0))

        if total == 0:
            return 0.0

        passed = total - failures - errors
        return round(passed / total, 4)

    except (ET.ParseError, ValueError, AttributeError):
        return 0.0


def calculate_syntactic_correctness(src_path: Path | None = None) -> float:
    """
    Calculate code quality score from linter results.

    Uses Ruff for linting analysis. Falls back to neutral score
    if linter is unavailable.

    Args:
        src_path: Path to source directory. Defaults to src/apeg_core

    Returns:
        Float between 0.0 and 1.0 representing code quality.
    """
    if src_path is None:
        src_path = Path("src/apeg_core")

    if not src_path.exists():
        return 0.5  # Neutral score if source not found

    scores = []

    # Ruff linting check
    try:
        result = subprocess.run(
            ["ruff", "check", str(src_path), "--output-format=json", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.stdout:
            issues = json.loads(result.stdout)
            # Score: 1.0 - (issues / 100), minimum 0.0
            # 100 issues = 0.0, 0 issues = 1.0
            ruff_score = max(0.0, 1.0 - len(issues) / 100)
            scores.append(ruff_score)
        else:
            scores.append(1.0)  # No output = no issues

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError):
        scores.append(0.5)  # Neutral on error
    except FileNotFoundError:
        # Ruff not installed
        scores.append(0.5)

    # Calculate average of all checks
    return round(sum(scores) / len(scores), 4) if scores else 0.5


def calculate_structure_score(input_file: Path) -> float:
    """
    Calculate structural compliance score for documentation/output.

    Checks for proper formatting, reasonable length, and organization.

    Args:
        input_file: Path to file to analyze

    Returns:
        Float between 0.0 and 1.0 representing structural quality.
    """
    if not input_file.exists():
        return 0.0

    try:
        content = input_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0.0

    checks = [
        # Has proper heading (markdown or text)
        content.startswith("#") or "## " in content or len(content) > 100,
        # Reasonable length (not empty, not huge)
        100 < len(content) < 100000,
        # Has multiple sections (for documentation)
        content.count("##") >= 2 or content.count("\n\n") >= 3,
        # No excessive empty lines (poor formatting)
        "\n\n\n\n" not in content,
        # Has code blocks if technical, or is prose
        "```" in content or "def " not in content or ".py" not in str(input_file),
        # Not just whitespace
        len(content.strip()) > 50,
    ]

    return round(sum(checks) / len(checks), 4)


def calculate_efficiency_score(
    input_file: Path, target_min: int = 500, target_max: int = 5000
) -> float:
    """
    Calculate token efficiency score based on content length.

    Optimal content is within target range. Too short or too long
    reduces the score.

    Args:
        input_file: Path to file to analyze
        target_min: Minimum optimal token count
        target_max: Maximum optimal token count

    Returns:
        Float between 0.0 and 1.0 representing efficiency.
    """
    if not input_file.exists():
        return 0.0

    try:
        content = input_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0.0

    # Rough token estimate (words * 1.3 for typical English)
    words = len(content.split())
    estimated_tokens = int(words * 1.3)

    # Score based on target range
    if target_min <= estimated_tokens <= target_max:
        return 1.0
    elif estimated_tokens < target_min:
        # Too short: proportional score
        return round(estimated_tokens / target_min, 4)
    else:
        # Too long: inverse proportional, minimum 0.3
        return round(max(0.3, target_max / estimated_tokens), 4)


def calculate_selector_accuracy(weights_path: Path | None = None) -> float:
    """
    Calculate bandit selector accuracy from historical data.

    Analyzes bandit_weights.json to determine how well the selector
    is performing based on reward history.

    Args:
        weights_path: Path to bandit weights file

    Returns:
        Float between 0.0 and 1.0 representing selector accuracy.
    """
    if weights_path is None:
        weights_path = Path("bandit_weights.json")

    if not weights_path.exists():
        return 0.5  # Neutral if no history

    try:
        weights = json.loads(weights_path.read_text())
    except (json.JSONDecodeError, OSError):
        return 0.5

    # Calculate average reward across all macros
    total_reward = 0.0
    total_plays = 0

    for macro, data in weights.items():
        if isinstance(data, dict) and "total_reward" in data:
            total_reward += data.get("total_reward", 0)
            total_plays += data.get("plays", 1)

    if total_plays == 0:
        return 0.5

    # Average reward as accuracy proxy
    avg_reward = total_reward / total_plays
    # Normalize to 0-1 range (assuming rewards are 0-1)
    return round(min(1.0, max(0.0, avg_reward)), 4)


def calculate_all_metrics(
    input_file: Path,
    test_results_path: Path | None = None,
    src_path: Path | None = None,
    weights_path: Path | None = None,
) -> dict[str, Any]:
    """
    Calculate all quality metrics with their weights.

    This is the main entry point for comprehensive quality scoring.

    Args:
        input_file: Primary file to evaluate
        test_results_path: Optional path to test results
        src_path: Optional path to source code
        weights_path: Optional path to bandit weights

    Returns:
        Dictionary containing:
        - metrics: Individual metric scores and weights
        - total_score: Weighted sum of all metrics
        - passed: Boolean indicating if quality threshold met
    """
    metrics = {
        "test_pass_rate": {
            "score": calculate_test_pass_rate(test_results_path),
            "weight": 0.40,
            "description": "Functional correctness via test execution",
        },
        "semantic_relevance": {
            "score": 0.85,  # Placeholder until LLM-as-judge integration
            "weight": 0.20,
            "description": "User intent alignment (requires LLM)",
        },
        "syntactic_correctness": {
            "score": calculate_syntactic_correctness(src_path),
            "weight": 0.15,
            "description": "Code quality and linting compliance",
        },
        "selector_accuracy_at_1": {
            "score": calculate_selector_accuracy(weights_path),
            "weight": 0.10,
            "description": "Bandit selector performance",
        },
        "structure": {
            "score": calculate_structure_score(input_file),
            "weight": 0.10,
            "description": "Structural and format compliance",
        },
        "efficiency": {
            "score": calculate_efficiency_score(input_file),
            "weight": 0.05,
            "description": "Token efficiency and conciseness",
        },
    }

    # Calculate weighted total
    total_score = sum(m["score"] * m["weight"] for m in metrics.values())

    # Default threshold
    threshold = 0.80

    return {
        "metrics": metrics,
        "total_score": round(total_score, 4),
        "passed": total_score >= threshold,
        "threshold": threshold,
    }


if __name__ == "__main__":
    # Test the metrics calculation
    import sys

    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
    else:
        test_file = Path("README.md")

    results = calculate_all_metrics(test_file)
    print(json.dumps(results, indent=2))
