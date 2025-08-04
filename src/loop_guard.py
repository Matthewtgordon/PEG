#
# This module contains the loop detection logic for the PEG agent.
# It prevents the agent from getting stuck in unproductive cycles by
# analyzing the history of macro selections and their scores.
#
from typing import List, Dict, Any

def detect_loop(history: List[Dict[str, Any]], N: int = 3, epsilon: float = 0.02) -> bool:
    """
    Detects if the same macro has been chosen in the last N 'build' steps
    without a score improvement greater than epsilon.

    This function is now robust and filters the complex orchestrator history
    to find the relevant 'build' events.

    Args:
        history (list of dicts): The full history from the orchestrator.
        N (int): The number of consecutive build repeats to detect as a loop.
        epsilon (float): The minimum score improvement required to be considered "progress".

    Returns:
        bool: True if a loop is detected, False otherwise.
    """
    # Filter the full history to get only 'build' events that have a macro.
    build_actions = [h for h in history if h.get('node') == 'build' and 'macro' in h]

    if len(build_actions) < N:
        return False

    # Get the last N build actions for checking
    recent_builds = build_actions[-N:]

    # Check if the macro is the same in all recent build actions
    last_macro = recent_builds[0].get('macro')
    if not all(action.get('macro') == last_macro for action in recent_builds):
        return False

    # Check if there has been any significant improvement in score across these steps
    for i in range(N - 1):
        score_current = recent_builds[i].get('score', 0)
        score_next = recent_builds[i + 1].get('score', 0)
        if (score_next - score_current) > epsilon:
            return False  # Improvement was found, not a loop

    # If the same macro was used N times with no significant improvement, it's a loop
    print(f"🔎 Loop Guard: Detected '{last_macro}' repeated {N} times without significant improvement.")
    return True
