"""
Decision engine for APEG runtime.

Components:
- BanditSelector: Thompson Sampling multi-armed bandit for macro selection
- LoopGuard: Detects repeated macro selection without improvement
- MCTSPlanner: Monte Carlo Tree Search for multi-step planning (placeholder)
"""

from apeg_core.decision.bandit_selector import BanditSelector, choose_macro
from apeg_core.decision.loop_guard import detect_loop, get_loop_statistics
from apeg_core.decision.mcts_planner import MCTSPlanner, plan_macro_sequence

__all__ = [
    "BanditSelector",
    "choose_macro",
    "detect_loop",
    "get_loop_statistics",
    "MCTSPlanner",
    "plan_macro_sequence",
]
