"""
APEG Scoring - Output quality assessment and metrics.

This package contains:
- Evaluator: Hybrid scoring system combining rules and LLM
- EvaluationResult: Structured evaluation results
- RealMetricsCalculator: Production-ready CI/CD metrics
- Convenience functions for quick scoring
- Integration with PromptScoreModel.json and quality-thresholds.json
"""

from apeg_core.scoring.evaluator import (
    Evaluator,
    EvaluationResult,
    rule_based_score,
    hybrid_score,
)
from apeg_core.scoring.real_metrics import (
    RealMetricsCalculator,
    MetricResult,
    calculate_test_pass_rate,
    calculate_semantic_relevance,
    calculate_syntactic_correctness,
    calculate_selector_accuracy,
    calculate_structure_compliance,
    calculate_efficiency,
)

__all__ = [
    "Evaluator",
    "EvaluationResult",
    "rule_based_score",
    "hybrid_score",
    "RealMetricsCalculator",
    "MetricResult",
    "calculate_test_pass_rate",
    "calculate_semantic_relevance",
    "calculate_syntactic_correctness",
    "calculate_selector_accuracy",
    "calculate_structure_compliance",
    "calculate_efficiency",
]
