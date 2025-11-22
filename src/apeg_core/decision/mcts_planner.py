"""
Monte Carlo Tree Search (MCTS) Planner for APEG runtime.

This module implements a complete MCTS-based planning algorithm for multi-step
macro selection. It uses UCB1 (Upper Confidence Bound) for exploration vs
exploitation balance.

Key Components:
- MCTSState: Protocol for state representation
- MCTSNode: Tree node with visit counts and values
- MCTSPlanner: Main planner class with search, expand, simulate, backprop

Note: This module is implemented but INACTIVE by default in APEG.
Enable via SessionConfig.json: {"enable_mcts_planner": true}

Usage:
    planner = MCTSPlanner(config)
    plan = planner.plan(available_macros, current_state, depth=5)
    # plan = ["macro1", "macro2", "macro3", ...]
"""

from __future__ import annotations

import logging
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar

logger = logging.getLogger(__name__)


class MCTSState(Protocol):
    """
    Protocol defining the interface for MCTS state representation.

    Implementations must provide methods for getting available actions,
    applying actions, and checking terminal states.
    """

    def get_available_actions(self) -> List[str]:
        """Return list of available actions from this state."""
        ...

    def apply_action(self, action: str) -> "MCTSState":
        """Apply action and return new state."""
        ...

    def is_terminal(self) -> bool:
        """Check if state is terminal (no more actions)."""
        ...

    def get_reward(self) -> float:
        """Get reward value for this state (0.0-1.0)."""
        ...


@dataclass
class MacroState:
    """
    Concrete state implementation for macro selection planning.

    Represents the state of a workflow at a given point, tracking
    which macros have been selected and their outcomes.

    Attributes:
        available_macros: List of macros that can be selected
        selected_macros: List of macros already selected in this plan
        scores: Dictionary of macro -> score mappings
        depth: Current depth in the planning tree
        max_depth: Maximum planning depth
    """
    available_macros: List[str]
    selected_macros: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    depth: int = 0
    max_depth: int = 5

    def get_available_actions(self) -> List[str]:
        """Return available macros that haven't been selected."""
        return [m for m in self.available_macros if m not in self.selected_macros]

    def apply_action(self, action: str) -> "MacroState":
        """Select a macro and return new state."""
        new_selected = self.selected_macros + [action]
        return MacroState(
            available_macros=self.available_macros,
            selected_macros=new_selected,
            scores=self.scores.copy(),
            depth=self.depth + 1,
            max_depth=self.max_depth,
        )

    def is_terminal(self) -> bool:
        """Check if plan is complete (max depth or no more macros)."""
        return self.depth >= self.max_depth or len(self.get_available_actions()) == 0

    def get_reward(self) -> float:
        """
        Calculate reward based on selected macros and their historical scores.

        Uses average of historical scores for selected macros, with small
        random noise to encourage exploration of untested combinations.
        """
        if not self.selected_macros:
            return 0.5

        total_score = 0.0
        for macro in self.selected_macros:
            # Use historical score if available, otherwise neutral
            score = self.scores.get(macro, 0.5)
            total_score += score

        avg_score = total_score / len(self.selected_macros)

        # Add small noise for exploration
        noise = random.uniform(-0.05, 0.05)
        return max(0.0, min(1.0, avg_score + noise))


@dataclass
class MCTSNode:
    """
    Node in the MCTS search tree.

    Tracks visit counts, accumulated value, and tree structure for
    the UCB1 selection algorithm.

    Attributes:
        state: The state represented by this node
        parent: Parent node (None for root)
        action: Action taken to reach this node from parent
        children: Dictionary of action -> child node
        visits: Number of times this node has been visited
        value: Accumulated value from simulations
        untried_actions: Actions not yet expanded
    """
    state: MacroState
    parent: Optional["MCTSNode"] = None
    action: Optional[str] = None
    children: Dict[str, "MCTSNode"] = field(default_factory=dict)
    visits: int = 0
    value: float = 0.0
    untried_actions: Optional[List[str]] = None

    def __post_init__(self):
        if self.untried_actions is None:
            self.untried_actions = self.state.get_available_actions()

    def is_fully_expanded(self) -> bool:
        """Check if all actions have been tried."""
        return len(self.untried_actions) == 0

    def is_terminal(self) -> bool:
        """Check if this node is a terminal state."""
        return self.state.is_terminal()

    def ucb1_value(self, exploration_weight: float = 1.414) -> float:
        """
        Calculate UCB1 value for node selection.

        UCB1 = value/visits + exploration_weight * sqrt(ln(parent.visits) / visits)

        Args:
            exploration_weight: Controls exploration vs exploitation (default: sqrt(2))

        Returns:
            UCB1 value (higher = better candidate for selection)
        """
        if self.visits == 0:
            return float('inf')  # Prefer unvisited nodes

        exploitation = self.value / self.visits

        if self.parent is None or self.parent.visits == 0:
            return exploitation

        exploration = exploration_weight * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

        return exploitation + exploration

    def best_child(self, exploration_weight: float = 1.414) -> "MCTSNode":
        """
        Select best child using UCB1.

        Args:
            exploration_weight: UCB1 exploration parameter

        Returns:
            Child node with highest UCB1 value
        """
        if not self.children:
            raise ValueError("Node has no children")

        return max(
            self.children.values(),
            key=lambda c: c.ucb1_value(exploration_weight)
        )

    def best_action(self) -> str:
        """
        Get best action based on visit counts (for final selection).

        Returns:
            Action with most visits (most robust choice)
        """
        if not self.children:
            raise ValueError("Node has no children")

        return max(
            self.children.keys(),
            key=lambda a: self.children[a].visits
        )


class MCTSPlanner:
    """
    Monte Carlo Tree Search planner for macro sequence optimization.

    Implements the four phases of MCTS:
    1. Selection: Traverse tree using UCB1
    2. Expansion: Add new child node for untried action
    3. Simulation: Random playout to terminal state
    4. Backpropagation: Update values up the tree

    Configuration:
        - iterations: Number of MCTS iterations per plan
        - exploration_weight: UCB1 exploration constant (default: sqrt(2))
        - max_depth: Maximum planning depth

    Note: This planner is INACTIVE by default in APEG.
    Enable via config: {"enable_mcts_planner": true}
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the MCTS planner.

        Args:
            config: Configuration dictionary with MCTS parameters
                - iterations: Number of iterations per plan (default: 100)
                - exploration_weight: UCB1 exploration constant (default: 1.414)
                - max_depth: Maximum plan depth (default: 5)
        """
        self.config = config or {}
        self.iterations = self.config.get("iterations", 100)
        self.exploration_weight = self.config.get("exploration_weight", 1.414)
        self.max_depth = self.config.get("max_depth", 5)

        # Statistics tracking
        self.stats = {
            "plans_generated": 0,
            "total_iterations": 0,
            "avg_iterations_per_plan": 0.0,
        }

        logger.info(
            "MCTSPlanner initialized (iterations=%d, exploration=%.3f, max_depth=%d)",
            self.iterations,
            self.exploration_weight,
            self.max_depth
        )

    def plan(
        self,
        available_macros: List[str],
        current_state: Dict[str, Any],
        depth: int = 5,
    ) -> List[str]:
        """
        Generate a multi-step macro plan using MCTS.

        Args:
            available_macros: List of available macro names
            current_state: Current execution state (with history for scores)
            depth: Plan depth (number of steps to plan ahead)

        Returns:
            List of macro names representing the optimal plan

        Example:
            plan = planner.plan(
                ["macro_a", "macro_b", "macro_c"],
                {"history": [{"macro": "macro_a", "score": 0.8}]},
                depth=3
            )
            # Returns: ["macro_b", "macro_a", "macro_c"] or similar
        """
        if not available_macros:
            logger.warning("No macros available for planning")
            return []

        # Extract historical scores from state
        scores = self._extract_scores(current_state)

        # Create initial state
        initial_state = MacroState(
            available_macros=available_macros,
            selected_macros=[],
            scores=scores,
            depth=0,
            max_depth=min(depth, len(available_macros)),
        )

        # Create root node
        root = MCTSNode(state=initial_state)

        # Run MCTS iterations
        for i in range(self.iterations):
            node = self._select(root)
            if not node.is_terminal():
                node = self._expand(node)
            reward = self._simulate(node)
            self._backpropagate(node, reward)

        # Extract best plan
        plan = self._extract_plan(root)

        # Update statistics
        self.stats["plans_generated"] += 1
        self.stats["total_iterations"] += self.iterations
        self.stats["avg_iterations_per_plan"] = (
            self.stats["total_iterations"] / self.stats["plans_generated"]
        )

        logger.info("MCTS plan generated: %s (iterations=%d)", plan, self.iterations)
        return plan

    def _extract_scores(self, state: Dict[str, Any]) -> Dict[str, float]:
        """Extract macro scores from execution history."""
        scores = {}
        history = state.get("history", [])

        for entry in history:
            macro = entry.get("macro")
            score = entry.get("score", 0.5)
            if macro:
                # Use exponential moving average for multiple entries
                if macro in scores:
                    scores[macro] = 0.7 * score + 0.3 * scores[macro]
                else:
                    scores[macro] = score

        return scores

    def _select(self, node: MCTSNode) -> MCTSNode:
        """
        Selection phase: Traverse tree using UCB1 until leaf.

        Args:
            node: Starting node (usually root)

        Returns:
            Selected leaf node for expansion
        """
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node
            node = node.best_child(self.exploration_weight)
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        """
        Expansion phase: Add new child for untried action.

        Args:
            node: Node to expand

        Returns:
            Newly created child node
        """
        if not node.untried_actions:
            return node

        # Pick random untried action
        action = random.choice(node.untried_actions)
        node.untried_actions.remove(action)

        # Create new state and node
        new_state = node.state.apply_action(action)
        child = MCTSNode(state=new_state, parent=node, action=action)
        node.children[action] = child

        return child

    def _simulate(self, node: MCTSNode) -> float:
        """
        Simulation phase: Random playout to terminal state.

        Args:
            node: Node to simulate from

        Returns:
            Reward from simulation (0.0-1.0)
        """
        state = node.state

        # Random playout until terminal
        while not state.is_terminal():
            actions = state.get_available_actions()
            if not actions:
                break
            action = random.choice(actions)
            state = state.apply_action(action)

        return state.get_reward()

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        """
        Backpropagation phase: Update values up the tree.

        Args:
            node: Starting node (leaf)
            reward: Reward to propagate
        """
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent

    def _extract_plan(self, root: MCTSNode) -> List[str]:
        """
        Extract best plan from search tree.

        Follows most-visited path from root to build plan.

        Args:
            root: Root node of search tree

        Returns:
            List of actions representing best plan
        """
        plan = []
        node = root

        while node.children:
            best_action = node.best_action()
            plan.append(best_action)
            node = node.children[best_action]

        return plan

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get MCTS planning statistics.

        Returns:
            Dictionary with planning metrics
        """
        return {
            "status": "implemented",
            "active": False,  # MCTS is inactive by default
            "plans_generated": self.stats["plans_generated"],
            "total_iterations": self.stats["total_iterations"],
            "avg_iterations_per_plan": self.stats["avg_iterations_per_plan"],
            "config": {
                "iterations": self.iterations,
                "exploration_weight": self.exploration_weight,
                "max_depth": self.max_depth,
            },
        }

    def reset_statistics(self) -> None:
        """Reset planning statistics."""
        self.stats = {
            "plans_generated": 0,
            "total_iterations": 0,
            "avg_iterations_per_plan": 0.0,
        }


def plan_macro_sequence(
    macros: List[str],
    state: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Convenience function for MCTS planning.

    Args:
        macros: Available macro names
        state: Current execution state
        config: MCTS configuration

    Returns:
        Planned macro sequence
    """
    planner = MCTSPlanner(config)
    return planner.plan(macros, state)


__all__ = [
    "MCTSPlanner",
    "MCTSNode",
    "MCTSState",
    "MacroState",
    "plan_macro_sequence",
]
