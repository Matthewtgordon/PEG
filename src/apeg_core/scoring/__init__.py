"""
APEG Scoring - Output quality assessment and metrics.

This package contains:
- Evaluator: Hybrid scoring system combining rules and LLM
- EvaluationResult: Structured evaluation results
- Convenience functions for quick scoring
- Integration with PromptScoreModel.json
"""

from apeg_core.scoring.evaluator import (
    Evaluator,
    EvaluationResult,
    rule_based_score,
    hybrid_score,
)

__all__ = [
    "Evaluator",
    "EvaluationResult",
    "rule_based_score",
    "hybrid_score",
]
