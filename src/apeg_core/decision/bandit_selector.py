"""
Bandit-based macro selector with Thompson Sampling.

This module implements a multi-armed bandit (MAB) algorithm for selecting
the best macro (prompt strategy) based on historical performance. It uses
Thompson Sampling with Beta distribution for exploration vs exploitation.

Key Features:
- Thompson Sampling for probabilistic selection
- Exploration bonus to encourage trying under-explored options
- Weight persistence to JSON file
- Decay factor for aging historical data
- Configurable reward mapping from scores
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BanditSelector:
    """
    Thompson Sampling bandit with weight persistence and self-learning.

    Uses Beta distribution sampling with exploration bonus to select
    the best macro based on historical success/failure rates. Includes
    regret tracking for adaptive exploration and feedback loops for
    continuous learning.

    Attributes:
        weights_path: Path to weights persistence file
        decay: Decay factor for aging historical statistics (0-1)
        weights: Dictionary mapping macro names to statistics
        metrics: Tracking metrics (selections count, etc.)
        regret: Cumulative regret for exploration decisions
        regret_threshold: Threshold for forcing exploration mode
        true_means: Estimated true reward means (for regret calculation)
        feedback_history: Recent feedback records for learning
    """

    def __init__(
        self,
        weights_path: Path | str = Path("bandit_weights.json"),
        decay: float = 0.9,
        regret_threshold: float = 10.0,
        feedback_window: int = 100,
    ):
        """
        Initialize the bandit selector.

        Args:
            weights_path: Path to JSON file for weight persistence
            decay: Decay factor for aging statistics (default: 0.9)
            regret_threshold: Cumulative regret that triggers forced exploration
            feedback_window: Number of recent feedback records to maintain
        """
        self.weights_path = Path(weights_path)
        self.decay = decay
        self.regret_threshold = regret_threshold
        self.feedback_window = feedback_window
        self.weights: Dict[str, Dict[str, float]] = self._load()
        self.metrics: Dict[str, Any] = {"selections": 0}

        # Self-learning components
        self.regret: float = 0.0
        self.true_means: Dict[str, float] = {}
        self.feedback_history: List[Dict[str, Any]] = []

        # Load persisted learning state
        self._load_learning_state()

        logger.debug(
            "BanditSelector initialized with %d macros, decay=%.2f, regret_threshold=%.2f",
            len(self.weights),
            self.decay,
            self.regret_threshold,
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

        # Regret-based exploration toggle: force random exploration if regret is high
        if self.regret > self.regret_threshold:
            selected = macros[random.randint(0, len(macros) - 1)]
            logger.info(
                "Regret (%.2f) exceeded threshold (%.2f), forcing exploration: %s",
                self.regret,
                self.regret_threshold,
                selected
            )
            self.metrics["selections"] += 1
            self.metrics["forced_explorations"] = self.metrics.get("forced_explorations", 0) + 1
            self._save()
            return selected

        # Thompson Sampling: sample from Beta distribution for each macro
        best_macro = None
        best_sample = -1.0

        for macro in macros:
            stats = self.weights[macro]

            # Sample from Beta(successes, failures)
            try:
                sample = random.betavariate(stats["successes"], stats["failures"])
            except ValueError:
                # Handle edge case where parameters are invalid
                logger.warning(
                    "Invalid Beta parameters for %s: successes=%s, failures=%s",
                    macro,
                    stats["successes"],
                    stats["failures"],
                )
                sample = 0.5

            # Add exploration bonus (decays with number of plays)
            exploration_bonus = 1.0 / (1 + stats.get("plays", 0))
            sample += exploration_bonus

            logger.debug(
                "Macro %s: sample=%.4f (Beta(%.2f,%.2f)), bonus=%.4f, plays=%d",
                macro,
                sample - exploration_bonus,
                stats["successes"],
                stats["failures"],
                exploration_bonus,
                stats.get("plays", 0),
            )

            if sample > best_sample:
                best_sample = sample
                best_macro = macro

        # Track selection
        self.metrics["selections"] += 1

        # Persist weights
        self._save()

        # Fallback to first macro if something went wrong
        if best_macro is None:
            best_macro = macros[0]
            logger.warning("No macro selected, falling back to %s", best_macro)

        logger.info(
            "Selected macro: %s (sample=%.4f, successes=%.2f, failures=%.2f)",
            best_macro,
            best_sample,
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

    def reset(self) -> None:
        """Reset all weights and metrics."""
        self.weights = {}
        self.metrics = {"selections": 0}
        self.regret = 0.0
        self.true_means = {}
        self.feedback_history = []
        logger.info("Bandit weights and learning state reset")

    def update_from_feedback(self, arm: str, reward: float) -> None:
        """
        Update bandit statistics from direct feedback.

        This method enables continuous self-learning by updating
        the bandit's beliefs based on observed rewards. Also tracks
        regret for adaptive exploration decisions.

        Args:
            arm: The macro/arm that received the reward
            reward: The reward value (0.0 to 1.0)
        """
        # Ensure the arm exists
        self.weights.setdefault(
            arm,
            {"successes": 1, "failures": 1, "plays": 0, "total_reward": 0}
        )

        stats = self.weights[arm]

        # Update Beta distribution parameters
        stats["successes"] += reward
        stats["failures"] += (1 - reward)
        stats["plays"] = stats.get("plays", 0) + 1
        stats["total_reward"] = stats.get("total_reward", 0) + reward

        # Update true mean estimate for this arm (exponential moving average)
        current_mean = self.true_means.get(arm, 0.5)
        alpha = 0.1  # Learning rate for mean estimation
        self.true_means[arm] = current_mean + alpha * (reward - current_mean)

        # Calculate and accumulate regret
        # Regret = optimal_reward - actual_reward
        optimal_reward = max(self.true_means.values()) if self.true_means else 1.0
        instant_regret = optimal_reward - reward
        self.regret += instant_regret

        # Record in feedback history
        self.feedback_history.append({
            "arm": arm,
            "reward": reward,
            "regret": instant_regret,
            "cumulative_regret": self.regret
        })

        # Trim feedback history to window size
        if len(self.feedback_history) > self.feedback_window:
            self.feedback_history = self.feedback_history[-self.feedback_window:]

        # Persist state
        self._save()
        self._save_learning_state()

        logger.info(
            "Updated from feedback: arm=%s, reward=%.3f, regret=%.3f, cumulative=%.3f",
            arm,
            reward,
            instant_regret,
            self.regret
        )

    def get_regret(self) -> float:
        """Get current cumulative regret."""
        return self.regret

    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive learning statistics.

        Returns:
            Dictionary with learning metrics
        """
        return {
            "cumulative_regret": self.regret,
            "regret_threshold": self.regret_threshold,
            "true_means": self.true_means.copy(),
            "feedback_count": len(self.feedback_history),
            "forced_explorations": self.metrics.get("forced_explorations", 0),
            "total_selections": self.metrics.get("selections", 0)
        }

    def reset_regret(self) -> None:
        """Reset regret counter while preserving learned weights."""
        self.regret = 0.0
        self.metrics["forced_explorations"] = 0
        self._save_learning_state()
        logger.info("Regret counter reset")


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
