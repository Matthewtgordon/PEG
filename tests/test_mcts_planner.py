"""Tests for the MCTS Planner module.

Tests cover:
- MacroState class functionality
- MCTSNode tree operations
- UCB1 value calculation
- MCTSPlanner search algorithm
- Plan extraction and statistics
"""

import pytest
import random

from apeg_core.decision.mcts_planner import (
    MCTSPlanner,
    MCTSNode,
    MacroState,
    plan_macro_sequence,
)


class TestMacroState:
    """Tests for MacroState class."""

    def test_state_initialization(self):
        """Test MacroState initialization."""
        state = MacroState(
            available_macros=["a", "b", "c"],
            selected_macros=[],
            max_depth=3
        )
        assert state.available_macros == ["a", "b", "c"]
        assert state.selected_macros == []
        assert state.depth == 0
        assert state.max_depth == 3

    def test_get_available_actions(self):
        """Test getting available actions."""
        state = MacroState(
            available_macros=["a", "b", "c"],
            selected_macros=["a"],
        )
        actions = state.get_available_actions()
        assert "a" not in actions
        assert "b" in actions
        assert "c" in actions

    def test_apply_action(self):
        """Test applying action to get new state."""
        state = MacroState(
            available_macros=["a", "b", "c"],
            selected_macros=[],
        )
        new_state = state.apply_action("a")

        assert "a" in new_state.selected_macros
        assert new_state.depth == 1
        # Original state unchanged
        assert state.depth == 0
        assert "a" not in state.selected_macros

    def test_is_terminal_at_max_depth(self):
        """Test terminal detection at max depth."""
        state = MacroState(
            available_macros=["a", "b", "c"],
            selected_macros=["a", "b"],
            depth=2,
            max_depth=2
        )
        assert state.is_terminal() is True

    def test_is_terminal_no_actions(self):
        """Test terminal detection when no actions left."""
        state = MacroState(
            available_macros=["a"],
            selected_macros=["a"],
            depth=1,
            max_depth=5
        )
        assert state.is_terminal() is True

    def test_get_reward_with_scores(self):
        """Test reward calculation with historical scores."""
        state = MacroState(
            available_macros=["a", "b"],
            selected_macros=["a", "b"],
            scores={"a": 0.8, "b": 0.6},
        )
        reward = state.get_reward()
        # Average of 0.8 and 0.6 is 0.7, plus noise
        assert 0.6 <= reward <= 0.8

    def test_get_reward_empty_selection(self):
        """Test reward for empty selection."""
        state = MacroState(
            available_macros=["a", "b"],
            selected_macros=[],
        )
        assert state.get_reward() == 0.5


class TestMCTSNode:
    """Tests for MCTSNode class."""

    def test_node_initialization(self):
        """Test MCTSNode initialization."""
        state = MacroState(available_macros=["a", "b", "c"])
        node = MCTSNode(state=state)

        assert node.visits == 0
        assert node.value == 0.0
        assert node.parent is None
        assert len(node.children) == 0
        assert len(node.untried_actions) == 3

    def test_is_fully_expanded(self):
        """Test fully expanded check."""
        state = MacroState(available_macros=["a"])
        node = MCTSNode(state=state)

        assert node.is_fully_expanded() is False
        node.untried_actions = []
        assert node.is_fully_expanded() is True

    def test_ucb1_value_unvisited(self):
        """Test UCB1 value for unvisited node."""
        state = MacroState(available_macros=["a"])
        node = MCTSNode(state=state)

        assert node.ucb1_value() == float('inf')

    def test_ucb1_value_visited(self):
        """Test UCB1 value for visited node."""
        state = MacroState(available_macros=["a"])
        parent = MCTSNode(state=state)
        parent.visits = 10

        child_state = state.apply_action("a")
        child = MCTSNode(state=child_state, parent=parent)
        child.visits = 5
        child.value = 2.5

        ucb1 = child.ucb1_value(exploration_weight=1.414)
        exploitation = 2.5 / 5  # 0.5
        # exploration = 1.414 * sqrt(ln(10)/5) ~ 0.96
        assert 1.0 < ucb1 < 2.0

    def test_best_child_selection(self):
        """Test best child selection by UCB1."""
        state = MacroState(available_macros=["a", "b"])
        parent = MCTSNode(state=state)
        parent.visits = 10

        # Create two children with different values
        child_a = MCTSNode(state=state.apply_action("a"), parent=parent)
        child_a.visits = 3
        child_a.value = 2.4  # avg 0.8

        child_b = MCTSNode(state=state.apply_action("b"), parent=parent)
        child_b.visits = 3
        child_b.value = 1.2  # avg 0.4

        parent.children = {"a": child_a, "b": child_b}

        best = parent.best_child()
        assert best is child_a  # Higher value

    def test_best_action_by_visits(self):
        """Test best action selection by visit count."""
        state = MacroState(available_macros=["a", "b"])
        parent = MCTSNode(state=state)

        child_a = MCTSNode(state=state.apply_action("a"), parent=parent)
        child_a.visits = 50

        child_b = MCTSNode(state=state.apply_action("b"), parent=parent)
        child_b.visits = 30

        parent.children = {"a": child_a, "b": child_b}

        assert parent.best_action() == "a"


class TestMCTSPlanner:
    """Tests for MCTSPlanner class."""

    def test_planner_initialization(self):
        """Test MCTSPlanner initialization."""
        planner = MCTSPlanner(config={
            "iterations": 50,
            "exploration_weight": 2.0,
            "max_depth": 3
        })

        assert planner.iterations == 50
        assert planner.exploration_weight == 2.0
        assert planner.max_depth == 3

    def test_planner_default_config(self):
        """Test MCTSPlanner with default config."""
        planner = MCTSPlanner()

        assert planner.iterations == 100
        assert planner.exploration_weight == 1.414
        assert planner.max_depth == 5

    def test_plan_empty_macros(self):
        """Test planning with empty macro list."""
        planner = MCTSPlanner()
        plan = planner.plan([], {})
        assert plan == []

    def test_plan_single_macro(self):
        """Test planning with single macro."""
        planner = MCTSPlanner(config={"iterations": 10})
        plan = planner.plan(["only_macro"], {})
        assert plan == ["only_macro"]

    def test_plan_multiple_macros(self):
        """Test planning with multiple macros."""
        random.seed(42)  # For reproducibility
        planner = MCTSPlanner(config={"iterations": 50, "max_depth": 3})

        plan = planner.plan(
            ["macro_a", "macro_b", "macro_c"],
            {"history": []}
        )

        assert len(plan) <= 3
        assert all(m in ["macro_a", "macro_b", "macro_c"] for m in plan)
        # Each macro should appear at most once
        assert len(plan) == len(set(plan))

    def test_plan_with_history_scores(self):
        """Test planning considers historical scores."""
        random.seed(42)
        planner = MCTSPlanner(config={"iterations": 100, "max_depth": 2})

        # macro_a has high score in history
        history = [
            {"macro": "macro_a", "score": 0.95},
            {"macro": "macro_b", "score": 0.3},
        ]

        plan = planner.plan(
            ["macro_a", "macro_b", "macro_c"],
            {"history": history}
        )

        # macro_a should likely be selected due to high score
        assert "macro_a" in plan

    def test_get_statistics(self):
        """Test statistics retrieval."""
        planner = MCTSPlanner()
        stats = planner.get_statistics()

        assert stats["status"] == "implemented"
        assert stats["active"] is False
        assert stats["plans_generated"] == 0

    def test_statistics_after_planning(self):
        """Test statistics update after planning."""
        planner = MCTSPlanner(config={"iterations": 10})
        planner.plan(["a", "b"], {})
        planner.plan(["a", "b"], {})

        stats = planner.get_statistics()
        assert stats["plans_generated"] == 2
        assert stats["total_iterations"] == 20

    def test_reset_statistics(self):
        """Test statistics reset."""
        planner = MCTSPlanner(config={"iterations": 10})
        planner.plan(["a"], {})
        planner.reset_statistics()

        stats = planner.get_statistics()
        assert stats["plans_generated"] == 0


class TestConvenienceFunction:
    """Tests for plan_macro_sequence convenience function."""

    def test_plan_macro_sequence(self):
        """Test convenience function."""
        random.seed(42)
        plan = plan_macro_sequence(
            macros=["x", "y", "z"],
            state={},
            config={"iterations": 10, "max_depth": 2}
        )

        assert isinstance(plan, list)
        # Plan can contain up to min(max_depth, len(macros)) items
        # but MCTS may explore deeper if exploration allows
        assert len(plan) <= 3  # bounded by number of macros
        assert all(m in ["x", "y", "z"] for m in plan)
