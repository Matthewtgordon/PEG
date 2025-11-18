"""
Loop detection guard for APEG runtime.

This module implements loop detection logic to prevent the system from
getting stuck in unproductive cycles. It analyzes the history of macro
selections and their scores to detect when the same macro is being
chosen repeatedly without making progress.

Key Features:
- Configurable look-back window (N)
- Score improvement threshold (epsilon)
- Filters history to focus on relevant "build" events
- Returns True if loop detected, False otherwise
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def detect_loop(
    history: List[Dict[str, Any]],
    N: int = 3,
    epsilon: float = 0.02,
) -> bool:
    """
    Detect if the same macro has been chosen repeatedly without improvement.

    This function filters the orchestrator history to find "build" events
    and checks if the same macro was selected in the last N builds without
    a score improvement greater than epsilon.

    Args:
        history: Full history from the orchestrator. Each entry should have:
            - node: Node ID (e.g., "build", "review")
            - macro: Macro name (optional, only for build nodes)
            - score: Output score (optional)
        N: Number of consecutive build repeats to check (default: 3)
        epsilon: Minimum score improvement to be considered progress (default: 0.02)

    Returns:
        True if a loop is detected, False otherwise

    Algorithm:
    1. Filter history to extract only "build" events with macro
    2. Check if we have at least N build events
    3. Get the last N build events
    4. Check if the macro is the same in all N events
    5. Check if there was any significant score improvement (> epsilon)
    6. Return True if same macro + no improvement, False otherwise

    Example:
        history = [
            {"node": "intake", "score": 0},
            {"node": "build", "macro": "macro1", "score": 0.75},
            {"node": "review", "score": 0.75},
            {"node": "build", "macro": "macro1", "score": 0.76},
            {"node": "review", "score": 0.76},
            {"node": "build", "macro": "macro1", "score": 0.76},
        ]
        is_loop = detect_loop(history, N=3, epsilon=0.02)
        # Returns True (same macro, improvement < 0.02)
    """
    # Filter history to get only "build" events that have a macro
    build_actions = [h for h in history if h.get("node") == "build" and "macro" in h]

    if len(build_actions) < N:
        logger.debug("Not enough build actions (%d) to detect loop (need %d)", len(build_actions), N)
        return False

    # Get the last N build actions
    recent_builds = build_actions[-N:]

    # Check if the macro is the same in all recent builds
    last_macro = recent_builds[0].get("macro")
    if not last_macro:
        logger.debug("No macro found in recent builds")
        return False

    # Check if all recent builds used the same macro
    if not all(action.get("macro") == last_macro for action in recent_builds):
        logger.debug("Different macros used in recent builds, no loop")
        return False

    # Check for score improvement across the N builds
    for i in range(N - 1):
        score_current = recent_builds[i].get("score", 0)
        score_next = recent_builds[i + 1].get("score", 0)
        improvement = score_next - score_current

        if improvement > epsilon:
            logger.debug(
                "Score improvement found: %.4f -> %.4f (delta=%.4f > epsilon=%.4f)",
                score_current,
                score_next,
                improvement,
                epsilon,
            )
            return False  # Improvement was found, not a loop

    # If we get here, same macro was used N times with no significant improvement
    logger.warning(
        "🔎 Loop Guard: Detected '%s' repeated %d times without significant improvement (epsilon=%.4f)",
        last_macro,
        N,
        epsilon,
    )

    # Log the recent build scores for debugging
    scores = [action.get("score", 0) for action in recent_builds]
    logger.warning("  Recent scores: %s", scores)

    return True


def get_loop_statistics(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get statistics about potential loops in the history.

    Args:
        history: Full history from orchestrator

    Returns:
        Dictionary with loop statistics:
        - total_builds: Total number of build events
        - macro_distribution: Count of each macro used
        - longest_sequence: Longest sequence of same macro
        - last_macro: Most recently used macro
    """
    build_actions = [h for h in history if h.get("node") == "build" and "macro" in h]

    if not build_actions:
        return {
            "total_builds": 0,
            "macro_distribution": {},
            "longest_sequence": 0,
            "last_macro": None,
        }

    # Count macro usage
    macro_distribution: Dict[str, int] = {}
    for action in build_actions:
        macro = action.get("macro")
        if macro:
            macro_distribution[macro] = macro_distribution.get(macro, 0) + 1

    # Find longest sequence of same macro
    longest_sequence = 1
    current_sequence = 1
    last_macro = build_actions[0].get("macro")

    for action in build_actions[1:]:
        macro = action.get("macro")
        if macro == last_macro:
            current_sequence += 1
            longest_sequence = max(longest_sequence, current_sequence)
        else:
            current_sequence = 1
            last_macro = macro

    return {
        "total_builds": len(build_actions),
        "macro_distribution": macro_distribution,
        "longest_sequence": longest_sequence,
        "last_macro": build_actions[-1].get("macro") if build_actions else None,
    }
