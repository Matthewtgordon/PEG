"""
Bandit-based macro selector with Thompson Sampling and UCB Hybrid.

This module implements an enhanced multi-armed bandit (MAB) algorithm for selecting
the best macro (prompt strategy) based on historical performance. It uses
Thompson Sampling with Beta distribution combined with UCB1 for optimistic
exploration vs exploitation.

Key Features:
- Thompson Sampling for probabilistic selection
- UCB1 hybrid for optimistic exploration (configurable weight)
- Exploration bonus to encourage trying under-explored options
- Weight persistence to JSON file
- Decay factor for aging historical data
- Configurable reward mapping from scores
- MCTS integration hook for high-uncertainty decisions

Algorithm (TS-UCB Hybrid):
1. Sample from Beta(successes, failures) for each macro
2. Calculate UCB1 bonus: sqrt(2 * ln(t) / plays)
3. Combine: final_score = ts_sample + ucb_weight * ucb_bonus + explore_bonus
4. Select macro with highest final_score

References:
- Thompson Sampling: https://en.wikipedia.org/wiki/Thompson_sampling
- UCB1: Auer et al., "Finite-time Analysis of the Multiarmed Bandit Problem"
- TS-UCB hybrid: Kaufmann et al., "Thompson Sampling: An Asymptotically Optimal..."
"""

from __future__ import annotations

import json
import logging
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BanditSelector:
    """
    Thompson Sampling bandit with UCB hybrid and weight persistence.

    Uses Beta distribution sampling combined with UCB1 optimistic bonus
    for enhanced exploration vs exploitation balance.

    Attributes:
        weights_path: Path to weights persistence file
        decay: Decay factor for aging historical statistics (0-1)
        ucb_weight: Weight for UCB1 component in hybrid (0-1)
        weights: Dictionary mapping macro names to statistics
        metrics: Tracking metrics (selections count, etc.)
        total_plays: Total number of selections (for UCB calculation)
    """

    def __init__(
        self,
        weights_path: Path | str = Path("bandit_weights.json"),
        decay: float = 0.9,
        ucb_weight: float = 0.1,
        exploration_constant: float = 2.0,
    ):
        """
        Initialize the bandit selector with UCB hybrid.

        Args:
            weights_path: Path to JSON file for weight persistence
            decay: Decay factor for aging statistics (default: 0.9)
            ucb_weight: Weight for UCB1 component (default: 0.1)
            exploration_constant: UCB exploration constant c (default: 2.0)
        """
        self.weights_path = Path(weights_path)
        self.decay = decay
        self.ucb_weight = ucb_weight
        self.exploration_constant = exploration_constant
        self.weights: Dict[str, Dict[str, float]] = self._load()
        self.metrics: Dict[str, Any] = {"selections": 0, "ucb_triggers": 0}
        self.total_plays = sum(
            w.get("plays", 0) for w in self.weights.values()
        )

        # Self-learning components
        self.regret: float = 0.0
        self.true_means: Dict[str, float] = {}
        self.feedback_history: List[Dict[str, Any]] = []

        # Load persisted learning state
        self._load_learning_state()

        logger.debug(
            "BanditSelector initialized with %d macros, decay=%.2f, ucb_weight=%.2f",
            len(self.weights),
            self.decay,
            self.ucb_weight,
        )

    def _load(self) -> Dict[str, Dict[str, float]]:
        """Load weights from persistence file."""
        if self.weights_path.exists():
            try:
                with self.weights_path.open("r", encoding="utf-8") as f:
                    weights = json.load(f)
                    logger.info("Loaded %d macro weights from %s", len(weights), self.weights_path)
                    return weights
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load weights from %s: %s", self.weights_path, e)
                return {}
        return {}

    def _save(self) -> None:
        """Save weights to persistence file."""
        try:
            with self.weights_path.open("w", encoding="utf-8") as f:
                json.dump(self.weights, f, indent=2)
            logger.debug("Saved weights to %s", self.weights_path)
        except IOError as e:
            logger.error("Failed to save weights to %s: %s", self.weights_path, e)

    def _get_learning_state_path(self) -> Path:
        """Get path for learning state file."""
        return self.weights_path.with_suffix(".learning.json")

    def _load_learning_state(self) -> None:
        """Load persisted learning state (regret, true_means, feedback_history)."""
        state_path = self._get_learning_state_path()
        if state_path.exists():
            try:
                with state_path.open("r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.regret = state.get("regret", 0.0)
                    self.true_means = state.get("true_means", {})
                    self.feedback_history = state.get("feedback_history", [])
                    logger.debug("Loaded learning state: regret=%.2f", self.regret)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load learning state: %s", e)

    def _save_learning_state(self) -> None:
        """Save learning state to persistence file."""
        state_path = self._get_learning_state_path()
        try:
            state = {
                "regret": self.regret,
                "true_means": self.true_means,
                "feedback_history": self.feedback_history[-self.feedback_window:]
            }
            with state_path.open("w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            logger.debug("Saved learning state to %s", state_path)
        except IOError as e:
            logger.error("Failed to save learning state: %s", e)

    def choose(
        self,
        macros: List[str],
        history: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> str:
        """
        Choose the best macro using Thompson Sampling.

        Args:
            macros: List of available macro names
            history: Historical performance data
            config: Configuration dict with scoring thresholds

        Returns:
            Selected macro name

        Algorithm:
        1. Apply decay to existing weights
        2. Update weights from history
        3. Sample from Beta distribution for each macro
        4. Add exploration bonus
        5. Select macro with highest sample value
        """
        if not macros:
            logger.error("No macros available for selection")
            raise ValueError("macros list cannot be empty")

        # Apply decay to all existing weights
        if history:
            for stats in self.weights.values():
                stats["successes"] *= self.decay
                stats["failures"] *= self.decay
                stats["plays"] = stats.get("plays", 0) * self.decay
                stats["total_reward"] = stats.get("total_reward", 0) * self.decay

        # Get pass threshold from config
        pass_threshold = config.get("ci", {}).get("minimum_score", 0.8)

        # Initialize weights for new macros
        for macro in macros:
            self.weights.setdefault(
                macro,
                {
                    "successes": 1,  # Start with 1/1 (uninformed prior)
                    "failures": 1,
                    "plays": 0,
                    "total_reward": 0,
                },
            )

        # Update weights from history
        for record in history:
            macro = record.get("macro")
            if not macro:
                continue

            # Determine reward (1 for success, 0 for failure)
            if "reward" in record:
                reward = record["reward"]
            else:
                # Infer reward from score
                reward = 1 if record.get("score", 0) >= pass_threshold else 0

            # Update statistics
            stats = self.weights.setdefault(
                macro,
                {"successes": 1, "failures": 1, "plays": 0, "total_reward": 0},
            )

            if reward:
                stats["successes"] += 1
            else:
                stats["failures"] += 1

            stats["plays"] += 1
            stats["total_reward"] += reward

        # TS-UCB Hybrid: sample from Beta distribution with UCB bonus
        best_macro = None
        best_score = -1.0
        uncertainty_scores: List[Tuple[str, float, float]] = []  # (macro, score, uncertainty)

        # Update total plays for UCB calculation
        self.total_plays = sum(
            self.weights[m].get("plays", 0) for m in macros
        )
        t = max(1, self.total_plays)  # Total time steps

        for macro in macros:
            stats = self.weights[macro]
            plays = max(1, stats.get("plays", 0))

            # Thompson Sampling: sample from Beta(successes, failures)
            try:
                ts_sample = random.betavariate(stats["successes"], stats["failures"])
            except ValueError:
                # Handle edge case where parameters are invalid
                logger.warning(
                    "Invalid Beta parameters for %s: successes=%s, failures=%s",
                    macro,
                    stats["successes"],
                    stats["failures"],
                )
                ts_sample = 0.5

            # UCB1 bonus: sqrt(c * ln(t) / plays)
            # This provides optimistic exploration for under-sampled arms
            ucb_bonus = math.sqrt(self.exploration_constant * math.log(t + 1) / plays)

            # Exploration bonus (original, decays with plays)
            exploration_bonus = 1.0 / (1 + plays)

            # Combined score: TS + weighted UCB + exploration
            final_score = ts_sample + (self.ucb_weight * ucb_bonus) + exploration_bonus

            # Track uncertainty for potential MCTS fallback
            # Uncertainty = variance of Beta distribution
            alpha, beta = stats["successes"], stats["failures"]
            variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            uncertainty_scores.append((macro, final_score, variance))

            logger.debug(
                "Macro %s: ts=%.4f, ucb=%.4f, explore=%.4f, final=%.4f, var=%.4f, plays=%d",
                macro,
                ts_sample,
                ucb_bonus,
                exploration_bonus,
                final_score,
                variance,
                plays,
            )

            if final_score > best_score:
                best_score = final_score
                best_macro = macro

        # Check for high uncertainty (potential MCTS trigger)
        # If top macros are very close in score, signal uncertainty
        sorted_scores = sorted(uncertainty_scores, key=lambda x: x[1], reverse=True)
        if len(sorted_scores) >= 2:
            score_gap = sorted_scores[0][1] - sorted_scores[1][1]
            avg_variance = sum(s[2] for s in sorted_scores[:3]) / min(3, len(sorted_scores))

            if score_gap < 0.1 and avg_variance > 0.05:
                # High uncertainty - could trigger MCTS
                self.metrics["ucb_triggers"] += 1
                logger.info(
                    "High uncertainty detected (gap=%.4f, var=%.4f) - consider MCTS",
                    score_gap,
                    avg_variance,
                )

        # Track selection
        self.metrics["selections"] += 1

        # Persist weights
        self._save()

        # Fallback to first macro if something went wrong
        if best_macro is None:
            best_macro = macros[0]
            logger.warning("No macro selected, falling back to %s", best_macro)

        logger.info(
            "Selected macro: %s (score=%.4f, successes=%.2f, failures=%.2f)",
            best_macro,
            best_score,
            self.weights[best_macro]["successes"],
            self.weights[best_macro]["failures"],
        )

        return best_macro

    def get_statistics(self, macro: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a macro or all macros.

        Args:
            macro: Macro name (None for all macros)

        Returns:
            Statistics dictionary
        """
        if macro:
            return self.weights.get(macro, {})
        return self.weights.copy()

    def get_uncertainty_metrics(self, macros: List[str]) -> Dict[str, Any]:
        """
        Get uncertainty metrics for MCTS decision.

        Args:
            macros: List of macro names to evaluate

        Returns:
            Dictionary with uncertainty metrics:
            - should_use_mcts: Boolean indicating high uncertainty
            - max_variance: Maximum variance among macros
            - score_gap: Gap between top two scores
            - top_macros: Top 3 macros by mean performance
        """
        metrics = {
            "should_use_mcts": False,
            "max_variance": 0.0,
            "score_gap": 1.0,
            "top_macros": [],
        }

        if not macros:
            return metrics

        scored_macros = []
        for macro in macros:
            stats = self.weights.get(macro, {"successes": 1, "failures": 1, "plays": 0})
            alpha = stats["successes"]
            beta = stats["failures"]

            # Mean of Beta distribution
            mean = alpha / (alpha + beta)
            # Variance of Beta distribution
            variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))

            scored_macros.append((macro, mean, variance))

        # Sort by mean performance
        scored_macros.sort(key=lambda x: x[1], reverse=True)

        metrics["top_macros"] = [m[0] for m in scored_macros[:3]]
        metrics["max_variance"] = max(m[2] for m in scored_macros)

        if len(scored_macros) >= 2:
            metrics["score_gap"] = scored_macros[0][1] - scored_macros[1][1]

        # Decision: use MCTS if high uncertainty and close scores
        metrics["should_use_mcts"] = (
            metrics["score_gap"] < 0.1 and
            metrics["max_variance"] > 0.05
        )

        return metrics

    def get_expected_regret(self, macros: List[str]) -> float:
        """
        Estimate expected regret for current selection.

        Lower regret = better performance.

        Args:
            macros: List of available macros

        Returns:
            Expected regret value
        """
        if not macros:
            return 0.0

        # Estimate best expected value
        best_mean = 0.0
        for macro in macros:
            stats = self.weights.get(macro, {"successes": 1, "failures": 1})
            mean = stats["successes"] / (stats["successes"] + stats["failures"])
            best_mean = max(best_mean, mean)

        # Calculate expected regret as deviation from best
        total_regret = 0.0
        for macro in macros:
            stats = self.weights.get(macro, {"successes": 1, "failures": 1})
            plays = stats.get("plays", 0)
            mean = stats["successes"] / (stats["successes"] + stats["failures"])
            regret = (best_mean - mean) * plays
            total_regret += regret

        return total_regret

    def reset(self) -> None:
        """Reset all weights and metrics."""
        self.weights = {}
        self.metrics = {"selections": 0, "ucb_triggers": 0}
        self.total_plays = 0
        logger.info("Bandit weights reset")


def choose_macro(
    macros: List[str],
    history: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> str:
    """
    Convenience function to choose a macro using the bandit selector.

    Args:
        macros: List of available macro names
        history: Historical performance data
        config: Configuration dict

    Returns:
        Selected macro name
    """
    selector = BanditSelector()
    return selector.choose(macros, history, config)


def record_bandit_reward(
    macro: str,
    reward: float,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record a reward for a specific macro to update bandit weights.

    This function allows the orchestrator to provide continuous feedback
    to the bandit selector based on evaluation scores, rather than just
    binary success/failure from history records.

    Args:
        macro: The macro name that received the reward
        reward: The reward value (0.0 to 1.0, where higher is better)
        config: Optional configuration dict

    Example:
        # After evaluation in review node
        score = evaluator.evaluate(output)
        record_bandit_reward(
            macro="macro_chain_of_thought",
            reward=score.score,
            config=session_config
        )
    """
    config = config or {}
    selector = BanditSelector()

    # Ensure the macro exists in weights
    selector.weights.setdefault(
        macro,
        {"successes": 1, "failures": 1, "plays": 0, "total_reward": 0}
    )

    # Get pass threshold for binary success/failure conversion
    pass_threshold = config.get("ci", {}).get("minimum_score", 0.8)

    # Update statistics
    stats = selector.weights[macro]
    stats["plays"] = stats.get("plays", 0) + 1
    stats["total_reward"] = stats.get("total_reward", 0) + reward

    # Convert to binary for Beta distribution parameters
    if reward >= pass_threshold:
        stats["successes"] += 1
    else:
        stats["failures"] += 1

    # Persist updated weights
    selector._save()

    logger.info(
        "Recorded reward for %s: %.3f (total_reward=%.3f, plays=%d)",
        macro,
        reward,
        stats["total_reward"],
        stats["plays"]
    )
