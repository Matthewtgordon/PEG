"""
CI Feedback Integration - Connects CI/CD results to Bandit Selector.

This module provides the bridge between CI pipeline results and the
Thompson Sampling bandit selector, enabling the system to learn from
actual CI outcomes rather than just runtime evaluation.

Features:
- Parse CI results from GitHub Actions artifacts
- Map CI outcomes to bandit rewards
- Update selector weights based on CI success/failure
- Track historical CI performance trends
- Support adaptive threshold ratcheting

Usage:
    from apeg_core.decision.ci_feedback import CIFeedbackProcessor

    processor = CIFeedbackProcessor()
    processor.process_ci_result(
        macro="macro_chain_of_thought",
        ci_passed=True,
        score=0.85,
        coverage=75.0
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CIResult:
    """Represents a single CI run result."""
    timestamp: str
    run_id: str
    sha: str
    ref: str
    macro: str
    passed: bool
    score: float
    coverage: Optional[float] = None
    test_count: int = 0
    test_passed: int = 0
    duration_seconds: float = 0.0
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "sha": self.sha,
            "ref": self.ref,
            "macro": self.macro,
            "passed": self.passed,
            "score": self.score,
            "coverage": self.coverage,
            "test_count": self.test_count,
            "test_passed": self.test_passed,
            "duration_seconds": self.duration_seconds,
            "details": self.details,
        }


class CIFeedbackProcessor:
    """
    Processes CI results and updates bandit selector weights.

    This class provides the integration layer between CI/CD pipelines
    and the Thompson Sampling bandit selector, enabling continuous
    learning from deployment outcomes.
    """

    def __init__(
        self,
        history_path: Path | str = Path("ci_feedback_history.json"),
        weights_path: Path | str = Path("bandit_weights.json"),
        thresholds_path: Path | str = Path(".github/quality-thresholds.json"),
    ):
        """
        Initialize the CI feedback processor.

        Args:
            history_path: Path to CI history JSON file
            weights_path: Path to bandit weights JSON file
            thresholds_path: Path to quality thresholds JSON file
        """
        self.history_path = Path(history_path)
        self.weights_path = Path(weights_path)
        self.thresholds_path = Path(thresholds_path)
        self.history = self._load_history()
        self.thresholds = self._load_thresholds()

    def _load_history(self) -> Dict[str, Any]:
        """Load CI history from file."""
        if self.history_path.exists():
            try:
                with self.history_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load CI history: %s", e)

        return {
            "runs": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "success_rate": 0.0,
            },
            "by_macro": {},
        }

    def _save_history(self) -> None:
        """Save CI history to file."""
        try:
            with self.history_path.open("w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
            logger.debug("Saved CI history to %s", self.history_path)
        except Exception as e:
            logger.error("Failed to save CI history: %s", e)

    def _load_thresholds(self) -> Dict[str, Any]:
        """Load quality thresholds from file."""
        if self.thresholds_path.exists():
            try:
                with self.thresholds_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load thresholds: %s", e)

        return {
            "score": {"minimum": 0.80},
            "coverage": {"minimum": 60},
            "learning": {"bandit_feedback_enabled": True},
        }

    def process_ci_result(
        self,
        macro: str,
        ci_passed: bool,
        score: float,
        coverage: Optional[float] = None,
        run_id: Optional[str] = None,
        sha: Optional[str] = None,
        ref: Optional[str] = None,
        test_results: Optional[Dict[str, int]] = None,
        duration_seconds: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Process a CI run result and update bandit weights.

        Args:
            macro: The macro/strategy that was used
            ci_passed: Whether CI passed overall
            score: The quality score achieved
            coverage: Code coverage percentage (optional)
            run_id: GitHub Actions run ID
            sha: Git commit SHA
            ref: Git ref (branch/tag)
            test_results: Dict with 'total' and 'passed' test counts
            duration_seconds: CI run duration

        Returns:
            Dictionary with processing results and recommendations
        """
        # Create result record
        test_results = test_results or {}
        result = CIResult(
            timestamp=datetime.now().isoformat(),
            run_id=run_id or "unknown",
            sha=sha or "unknown",
            ref=ref or "unknown",
            macro=macro,
            passed=ci_passed,
            score=score,
            coverage=coverage,
            test_count=test_results.get("total", 0),
            test_passed=test_results.get("passed", 0),
            duration_seconds=duration_seconds,
        )

        # Add to history
        self.history["runs"].append(result.to_dict())
        self.history["runs"] = self.history["runs"][-100:]  # Keep last 100

        # Update summary
        self.history["summary"]["total"] += 1
        if ci_passed:
            self.history["summary"]["passed"] += 1

        total = self.history["summary"]["total"]
        passed = self.history["summary"]["passed"]
        self.history["summary"]["success_rate"] = round(passed / total, 4)

        # Update per-macro stats
        if macro not in self.history["by_macro"]:
            self.history["by_macro"][macro] = {
                "total": 0,
                "passed": 0,
                "scores": [],
                "coverages": [],
            }

        macro_stats = self.history["by_macro"][macro]
        macro_stats["total"] += 1
        if ci_passed:
            macro_stats["passed"] += 1
        macro_stats["scores"].append(score)
        macro_stats["scores"] = macro_stats["scores"][-50:]  # Keep last 50

        if coverage is not None:
            macro_stats["coverages"].append(coverage)
            macro_stats["coverages"] = macro_stats["coverages"][-50:]

        # Calculate reward for bandit
        reward = self._calculate_reward(score, ci_passed)

        # Update bandit weights
        bandit_updated = self._update_bandit_weights(macro, reward)

        # Save history
        self._save_history()

        # Generate recommendations
        recommendations = self._generate_recommendations(result)

        logger.info(
            "Processed CI result: macro=%s, passed=%s, score=%.3f, reward=%.3f",
            macro, ci_passed, score, reward
        )

        return {
            "result": result.to_dict(),
            "reward": reward,
            "bandit_updated": bandit_updated,
            "success_rate": self.history["summary"]["success_rate"],
            "recommendations": recommendations,
        }

    def _calculate_reward(self, score: float, ci_passed: bool) -> float:
        """
        Calculate bandit reward from CI results.

        Uses a combination of CI pass/fail and score to determine
        the reward signal for the bandit selector.
        """
        min_score = self.thresholds.get("score", {}).get("minimum", 0.80)

        if not ci_passed:
            # Failed CI gets negative or zero reward
            return 0.0

        # Passed CI gets reward proportional to score
        if score >= min_score * 1.1:
            # Significantly above threshold
            return 1.0
        elif score >= min_score:
            # At or slightly above threshold
            return 0.8
        else:
            # Below threshold but CI passed (edge case)
            return 0.5

    def _update_bandit_weights(self, macro: str, reward: float) -> bool:
        """
        Update bandit selector weights with CI feedback.

        Returns True if weights were successfully updated.
        """
        if not self.thresholds.get("learning", {}).get("bandit_feedback_enabled", True):
            logger.debug("Bandit feedback disabled in thresholds")
            return False

        try:
            from apeg_core.decision.bandit_selector import record_bandit_reward

            record_bandit_reward(
                macro=macro,
                reward=reward,
                config={"ci": {"minimum_score": self.thresholds.get("score", {}).get("minimum", 0.80)}},
            )
            return True

        except ImportError:
            logger.warning("Could not import bandit_selector")
            return False
        except Exception as e:
            logger.error("Failed to update bandit weights: %s", e)
            return False

    def _generate_recommendations(self, result: CIResult) -> List[str]:
        """Generate recommendations based on CI result."""
        recommendations = []

        if not result.passed:
            recommendations.append("Investigate failing CI run")

        if result.score < 0.7:
            recommendations.append("Quality score is low - review recent changes")

        if result.coverage is not None and result.coverage < 60:
            recommendations.append("Code coverage is below 60% - add more tests")

        # Check for trends
        macro_stats = self.history.get("by_macro", {}).get(result.macro, {})
        if macro_stats.get("total", 0) >= 5:
            macro_pass_rate = macro_stats.get("passed", 0) / macro_stats["total"]
            if macro_pass_rate < 0.7:
                recommendations.append(
                    f"Macro '{result.macro}' has low success rate ({macro_pass_rate:.0%})"
                )

        return recommendations

    def get_macro_performance(self, macro: str) -> Dict[str, Any]:
        """
        Get performance statistics for a specific macro.

        Args:
            macro: The macro name to get stats for

        Returns:
            Dictionary with performance metrics
        """
        stats = self.history.get("by_macro", {}).get(macro, {})

        if not stats or stats.get("total", 0) == 0:
            return {
                "macro": macro,
                "total_runs": 0,
                "success_rate": None,
                "avg_score": None,
                "avg_coverage": None,
            }

        total = stats["total"]
        passed = stats.get("passed", 0)
        scores = stats.get("scores", [])
        coverages = stats.get("coverages", [])

        return {
            "macro": macro,
            "total_runs": total,
            "success_rate": round(passed / total, 4),
            "avg_score": round(sum(scores) / len(scores), 4) if scores else None,
            "avg_coverage": round(sum(coverages) / len(coverages), 2) if coverages else None,
        }

    def get_all_macro_rankings(self) -> List[Dict[str, Any]]:
        """
        Get all macros ranked by performance.

        Returns:
            List of macro performance dicts, sorted by success rate
        """
        rankings = []

        for macro in self.history.get("by_macro", {}).keys():
            perf = self.get_macro_performance(macro)
            if perf["total_runs"] > 0:
                rankings.append(perf)

        # Sort by success rate, then by average score
        rankings.sort(
            key=lambda x: (
                x["success_rate"] or 0,
                x["avg_score"] or 0
            ),
            reverse=True
        )

        return rankings

    def should_ratchet_thresholds(self) -> Dict[str, Any]:
        """
        Determine if quality thresholds should be ratcheted up.

        Returns:
            Dictionary with ratcheting recommendations
        """
        learning_config = self.thresholds.get("learning", {})
        min_samples = learning_config.get("min_samples_for_adjustment", 10)

        total_runs = self.history["summary"]["total"]
        success_rate = self.history["summary"]["success_rate"]

        result = {
            "should_ratchet": False,
            "current_success_rate": success_rate,
            "total_samples": total_runs,
            "min_samples_required": min_samples,
            "recommendations": [],
        }

        if total_runs < min_samples:
            result["recommendations"].append(
                f"Need {min_samples - total_runs} more samples before ratcheting"
            )
            return result

        if success_rate >= 0.95:
            result["should_ratchet"] = True
            result["recommendations"].append(
                "Success rate is ≥95%, consider ratcheting up thresholds"
            )

        return result


# Convenience functions
def record_ci_result(
    macro: str,
    ci_passed: bool,
    score: float,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience function to record a CI result.

    Args:
        macro: The macro that was used
        ci_passed: Whether CI passed
        score: Quality score achieved
        **kwargs: Additional arguments passed to process_ci_result

    Returns:
        Processing result dictionary
    """
    processor = CIFeedbackProcessor()
    return processor.process_ci_result(
        macro=macro,
        ci_passed=ci_passed,
        score=score,
        **kwargs,
    )


def get_macro_rankings() -> List[Dict[str, Any]]:
    """Get all macros ranked by CI performance."""
    processor = CIFeedbackProcessor()
    return processor.get_all_macro_rankings()


__all__ = [
    "CIFeedbackProcessor",
    "CIResult",
    "record_ci_result",
    "get_macro_rankings",
]
