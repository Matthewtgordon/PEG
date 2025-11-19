"""
APEG Evaluator - Hybrid scoring system for output quality assessment.

This module provides:
- Rule-based scoring for basic validation
- Hybrid scoring combining rules with optional LLM evaluation
- Integration with PromptScoreModel.json metrics
- Score calculation for Adoption Gate and Bandit reward

Scoring Pipeline:
1. Rule-based checks (format, length, structure)
2. Optional LLM-based quality assessment (via SCORER role)
3. Weighted metric aggregation
4. Threshold-based pass/fail decision

Usage:
    evaluator = Evaluator(config)
    result = evaluator.evaluate(output_text, context)
    if result.score >= threshold:
        # Pass adoption gate
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """
    Result of output evaluation.

    Attributes:
        score: Overall score (0.0 to 1.0)
        passed: Whether output passes threshold
        metrics: Individual metric scores
        details: Additional evaluation details
        feedback: Human-readable feedback
    """

    score: float
    passed: bool = False
    metrics: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    feedback: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "passed": self.passed,
            "metrics": self.metrics,
            "details": self.details,
            "feedback": self.feedback,
        }


class Evaluator:
    """
    Hybrid evaluator combining rule-based and optional LLM scoring.

    Phase 1: Rule-based scoring with basic heuristics
    Phase 2: Integration with SCORER LLM role for nuanced evaluation
    """

    def __init__(
        self,
        config: Dict[str, Any] | None = None,
        score_model_path: Path | str | None = None,
    ):
        """
        Initialize evaluator with configuration.

        Args:
            config: Optional configuration dictionary
            score_model_path: Path to PromptScoreModel.json (optional)
        """
        self.config = config or {}
        self.score_model = self._load_score_model(score_model_path)
        self.threshold = self._get_threshold()

    def _load_score_model(
        self, path: Path | str | None
    ) -> Dict[str, Any]:
        """
        Load scoring model from PromptScoreModel.json.

        Args:
            path: Path to score model file

        Returns:
            Score model dictionary or default model
        """
        if path is None:
            # Try default location
            path = Path.cwd() / "PromptScoreModel.json"

        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            logger.warning(
                "Score model not found at %s, using default metrics",
                path
            )
            return self._default_score_model()

        try:
            with path.open("r", encoding="utf-8") as f:
                model = json.load(f)
                logger.info("Loaded score model from %s", path)
                return model
        except Exception as e:
            logger.error("Failed to load score model: %s", e)
            return self._default_score_model()

    def _default_score_model(self) -> Dict[str, Any]:
        """
        Return default scoring model.

        Returns:
            Default score model with basic metrics
        """
        return {
            "metrics": [
                {"name": "completeness", "weight": 0.3},
                {"name": "format_valid", "weight": 0.2},
                {"name": "length_appropriate", "weight": 0.2},
                {"name": "quality", "weight": 0.3},
            ],
            "thresholds": {
                "pass": 0.7,
                "good": 0.8,
                "excellent": 0.9,
            },
        }

    def _get_threshold(self) -> float:
        """
        Get passing threshold from config or score model.

        Returns:
            Threshold score (0.0 to 1.0)
        """
        # Check config first
        if "ci" in self.config:
            threshold = self.config["ci"].get("minimum_score")
            if threshold is not None:
                return float(threshold)

        # Check score model
        if "thresholds" in self.score_model:
            threshold = self.score_model["thresholds"].get("pass")
            if threshold is not None:
                return float(threshold)

        # Default
        return 0.7

    def evaluate(
        self,
        output_text: str,
        context: Optional[Dict[str, Any]] = None,
        use_llm: bool = False,
    ) -> EvaluationResult:
        """
        Evaluate output quality using hybrid approach.

        Args:
            output_text: Output text to evaluate
            context: Optional context with goal, history, etc.
            use_llm: Whether to use LLM-based scoring (Phase 2)

        Returns:
            EvaluationResult with score and details
        """
        logger.info("Evaluating output (%d chars)", len(output_text))

        # Phase 1: Rule-based scoring
        rule_result = self.rule_based_score(output_text, context)

        # Phase 2: Optional LLM scoring (not implemented yet)
        if use_llm:
            # TODO[APEG-PH-6]: Integrate with SCORER LLM role
            logger.warning("LLM scoring requested but not implemented yet")

        # For now, return rule-based result
        result = rule_result
        result.passed = result.score >= self.threshold

        logger.info(
            "Evaluation complete: score=%.2f, passed=%s",
            result.score,
            result.passed
        )

        return result

    def rule_based_score(
        self,
        output_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Perform rule-based scoring using heuristics.

        Checks:
        - Non-empty output
        - Minimum length
        - Basic format validation
        - JSON validity (if expected)
        - Required keys presence (if specified)

        Args:
            output_text: Output text to evaluate
            context: Optional context with requirements

        Returns:
            EvaluationResult with rule-based scores
        """
        context = context or {}
        metrics = {}
        details = {}
        feedback_items = []

        # Metric 1: Completeness (non-empty)
        if not output_text or not output_text.strip():
            metrics["completeness"] = 0.0
            feedback_items.append("Output is empty")
        else:
            metrics["completeness"] = 1.0

        # Metric 2: Format validation
        trimmed = output_text.strip()

        # Check if JSON is expected
        expect_json = context.get("expect_json", False)
        if expect_json:
            try:
                parsed = json.loads(trimmed)
                metrics["format_valid"] = 1.0
                details["parsed_json"] = True

                # Check required keys if specified
                required_keys = context.get("required_keys", [])
                if required_keys:
                    missing = [k for k in required_keys if k not in parsed]
                    if missing:
                        metrics["format_valid"] = 0.7
                        feedback_items.append(f"Missing keys: {missing}")
                    else:
                        feedback_items.append("All required keys present")

            except json.JSONDecodeError:
                metrics["format_valid"] = 0.3
                feedback_items.append("Invalid JSON format")
                details["parsed_json"] = False
        else:
            # Non-JSON format validation
            if len(trimmed) > 0:
                metrics["format_valid"] = 0.9
            else:
                metrics["format_valid"] = 0.0

        # Metric 3: Length appropriateness
        min_length = context.get("min_length", 50)
        max_length = context.get("max_length", 10000)

        if len(trimmed) < min_length:
            metrics["length_appropriate"] = max(0.0, len(trimmed) / min_length)
            feedback_items.append(f"Output too short ({len(trimmed)} < {min_length})")
        elif len(trimmed) > max_length:
            metrics["length_appropriate"] = 0.8
            feedback_items.append(f"Output very long ({len(trimmed)} > {max_length})")
        else:
            metrics["length_appropriate"] = 1.0

        # Metric 4: Quality heuristics
        quality_score = self._assess_quality(trimmed)
        metrics["quality"] = quality_score

        if quality_score < 0.7:
            feedback_items.append("Output quality could be improved")

        # Calculate weighted overall score
        overall_score = self._calculate_weighted_score(metrics)

        # Build feedback
        feedback = "; ".join(feedback_items) if feedback_items else "Output looks good"

        return EvaluationResult(
            score=overall_score,
            metrics=metrics,
            details=details,
            feedback=feedback,
        )

    def _assess_quality(self, text: str) -> float:
        """
        Assess text quality using heuristics.

        This is a placeholder for more sophisticated analysis.

        Args:
            text: Text to assess

        Returns:
            Quality score (0.0 to 1.0)

        TODO[APEG-PH-6]: Enhance with:
        - Grammar checking
        - Coherence analysis
        - Relevance to goal
        - Professionalism assessment
        """
        if not text:
            return 0.0

        score = 0.6  # Base score for non-empty text

        # Bonus for reasonable length
        if 100 <= len(text) <= 5000:
            score += 0.1

        # Bonus for proper sentences (ending with punctuation)
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if len(sentences) >= 2:
            score += 0.1

        # Bonus for paragraph structure
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) >= 2:
            score += 0.1

        # Penalty for excessive repetition (simple check)
        words = text.lower().split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                score -= 0.2  # Too repetitive

        return min(1.0, max(0.0, score))

    def _calculate_weighted_score(
        self, metrics: Dict[str, float]
    ) -> float:
        """
        Calculate weighted overall score from individual metrics.

        Uses weights from score model if available, otherwise equal weights.

        Args:
            metrics: Dictionary of metric scores

        Returns:
            Weighted overall score (0.0 to 1.0)
        """
        # Get weights from score model
        model_metrics = self.score_model.get("metrics", [])
        weights = {m["name"]: m["weight"] for m in model_metrics}

        # Calculate weighted sum
        total_score = 0.0
        total_weight = 0.0

        for metric_name, metric_score in metrics.items():
            weight = weights.get(metric_name, 1.0 / len(metrics))
            total_score += metric_score * weight
            total_weight += weight

        # Normalize
        if total_weight > 0:
            return total_score / total_weight
        else:
            return 0.0

    def hybrid_score(
        self,
        output_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Hybrid scoring combining rules and LLM evaluation.

        Phase 1: Uses rule-based scoring
        Phase 2: Will integrate SCORER LLM role for nuanced evaluation

        Args:
            output_text: Output text to evaluate
            context: Optional context

        Returns:
            EvaluationResult with hybrid score

        TODO[APEG-PH-6]: Implement LLM integration
        - Call run_scorer_role() from llm_roles
        - Combine rule-based and LLM scores
        - Use weighted average or ensemble method
        """
        # For now, just use rule-based scoring
        # TODO[APEG-PH-6]: Add LLM scoring integration here
        return self.rule_based_score(output_text, context)


# Convenience functions for backward compatibility
def rule_based_score(output_text: str) -> EvaluationResult:
    """
    Quick rule-based scoring without configuration.

    Args:
        output_text: Output to score

    Returns:
        EvaluationResult with basic scoring
    """
    evaluator = Evaluator()
    return evaluator.rule_based_score(output_text)


def hybrid_score(output_text: str) -> EvaluationResult:
    """
    Quick hybrid scoring without configuration.

    Args:
        output_text: Output to score

    Returns:
        EvaluationResult with hybrid scoring
    """
    evaluator = Evaluator()
    return evaluator.hybrid_score(output_text)


__all__ = [
    "Evaluator",
    "EvaluationResult",
    "rule_based_score",
    "hybrid_score",
]
