"""
Tests for bandit selector (Thompson Sampling).

Tests cover:
- Basic macro selection
- Weight persistence
- Decay behavior
- Exploration bonus
- Reward mapping from scores
- Statistics tracking
"""

import json
import tempfile
from pathlib import Path

import pytest

from apeg_core.decision.bandit_selector import BanditSelector, choose_macro


@pytest.fixture
def temp_weights_file():
    """Create a temporary weights file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_config():
    """Sample configuration dictionary."""
    return {
        "ci": {"minimum_score": 0.8},
        "selector": {
            "algorithm": "thompson_sampling",
            "bandit": {"explore_rounds": 10, "min_delta_pass": 0.05},
        },
    }


@pytest.fixture
def sample_macros():
    """Sample macro names."""
    return ["macro_a", "macro_b", "macro_c"]


def test_bandit_initialization(temp_weights_file):
    """Test bandit selector initialization."""
    selector = BanditSelector(weights_path=temp_weights_file, decay=0.95)
    assert selector.weights_path == temp_weights_file
    assert selector.decay == 0.95
    assert selector.metrics["selections"] == 0
    assert len(selector.weights) == 0


def test_bandit_choose_empty_history(temp_weights_file, sample_macros, sample_config):
    """Test choosing macro with no history."""
    selector = BanditSelector(weights_path=temp_weights_file)
    chosen = selector.choose(sample_macros, history=[], config=sample_config)

    # Should return one of the available macros
    assert chosen in sample_macros

    # All macros should be initialized in weights
    assert len(selector.weights) == len(sample_macros)
    for macro in sample_macros:
        assert macro in selector.weights
        assert selector.weights[macro]["successes"] == 1
        assert selector.weights[macro]["failures"] == 1


def test_bandit_choose_with_history(temp_weights_file, sample_macros, sample_config):
    """Test choosing macro with successful history."""
    selector = BanditSelector(weights_path=temp_weights_file)

    # Create history with macro_a performing well
    history = [
        {"node": "build", "macro": "macro_a", "score": 0.9},
        {"node": "build", "macro": "macro_a", "score": 0.85},
        {"node": "build", "macro": "macro_b", "score": 0.6},
    ]

    chosen = selector.choose(sample_macros, history, sample_config)

    # macro_a should have higher success count
    assert selector.weights["macro_a"]["successes"] > selector.weights["macro_b"]["successes"]

    # At least one macro should be selected
    assert chosen in sample_macros


def test_bandit_reward_mapping(temp_weights_file, sample_macros, sample_config):
    """Test reward mapping from scores."""
    selector = BanditSelector(weights_path=temp_weights_file)

    # Create history with explicit scores
    history = [
        {"macro": "macro_a", "score": 0.9},  # Above threshold -> reward=1
        {"macro": "macro_a", "score": 0.75},  # Below threshold -> reward=0
    ]

    selector.choose(sample_macros, history, sample_config)

    # macro_a should have 1 success + 1 failure (plus initial 1/1)
    stats = selector.weights["macro_a"]
    assert stats["successes"] == 2  # 1 initial + 1 from score 0.9
    assert stats["failures"] == 2   # 1 initial + 1 from score 0.75


def test_bandit_explicit_rewards(temp_weights_file, sample_macros, sample_config):
    """Test using explicit reward values."""
    selector = BanditSelector(weights_path=temp_weights_file)

    # Create history with explicit rewards
    history = [
        {"macro": "macro_a", "reward": 1},
        {"macro": "macro_a", "reward": 1},
        {"macro": "macro_b", "reward": 0},
    ]

    selector.choose(sample_macros, history, sample_config)

    assert selector.weights["macro_a"]["successes"] == 3  # 1 initial + 2
    assert selector.weights["macro_a"]["failures"] == 1   # 1 initial
    assert selector.weights["macro_b"]["successes"] == 1  # 1 initial
    assert selector.weights["macro_b"]["failures"] == 2   # 1 initial + 1


def test_bandit_persistence(temp_weights_file, sample_macros, sample_config):
    """Test weight persistence to file."""
    # First selector creates weights
    selector1 = BanditSelector(weights_path=temp_weights_file)
    history = [{"macro": "macro_a", "reward": 1}]
    selector1.choose(sample_macros, history, sample_config)

    # Second selector should load existing weights
    selector2 = BanditSelector(weights_path=temp_weights_file)
    assert "macro_a" in selector2.weights
    assert selector2.weights["macro_a"]["successes"] > 1


def test_bandit_decay(temp_weights_file, sample_macros, sample_config):
    """Test decay of historical statistics."""
    selector = BanditSelector(weights_path=temp_weights_file, decay=0.5)

    # Create initial history
    history1 = [{"macro": "macro_a", "reward": 1}]
    selector.choose(sample_macros, history1, sample_config)

    initial_successes = selector.weights["macro_a"]["successes"]

    # Add more history (should trigger decay)
    history2 = [{"macro": "macro_b", "reward": 1}]
    selector.choose(sample_macros, history2, sample_config)

    # macro_a successes should have decayed
    assert selector.weights["macro_a"]["successes"] < initial_successes


def test_bandit_metrics(temp_weights_file, sample_macros, sample_config):
    """Test metrics tracking."""
    selector = BanditSelector(weights_path=temp_weights_file)

    assert selector.metrics["selections"] == 0

    selector.choose(sample_macros, [], sample_config)
    assert selector.metrics["selections"] == 1

    selector.choose(sample_macros, [], sample_config)
    assert selector.metrics["selections"] == 2


def test_bandit_statistics(temp_weights_file, sample_macros, sample_config):
    """Test statistics retrieval."""
    selector = BanditSelector(weights_path=temp_weights_file)
    history = [{"macro": "macro_a", "reward": 1}]
    selector.choose(sample_macros, history, sample_config)

    # Get all statistics
    all_stats = selector.get_statistics()
    assert "macro_a" in all_stats

    # Get specific macro statistics
    macro_stats = selector.get_statistics("macro_a")
    assert "successes" in macro_stats
    assert "failures" in macro_stats


def test_bandit_reset(temp_weights_file):
    """Test resetting bandit state."""
    selector = BanditSelector(weights_path=temp_weights_file)
    selector.weights["macro_a"] = {"successes": 10, "failures": 5}
    selector.metrics["selections"] = 5

    selector.reset()

    assert len(selector.weights) == 0
    assert selector.metrics["selections"] == 0


def test_bandit_empty_macros_raises_error(temp_weights_file, sample_config):
    """Test that empty macros list raises error."""
    selector = BanditSelector(weights_path=temp_weights_file)

    with pytest.raises(ValueError, match="macros list cannot be empty"):
        selector.choose([], [], sample_config)


def test_choose_macro_convenience_function(sample_macros, sample_config):
    """Test the convenience function."""
    history = [{"macro": "macro_a", "reward": 1}]
    chosen = choose_macro(sample_macros, history, sample_config)

    assert chosen in sample_macros


def test_bandit_exploration_bonus(temp_weights_file, sample_macros, sample_config):
    """Test that exploration bonus favors less-played macros."""
    selector = BanditSelector(weights_path=temp_weights_file)

    # Create history where macro_a has been played many times
    history = [{"macro": "macro_a", "reward": 1} for _ in range(20)]
    selector.choose(sample_macros, history, sample_config)

    # macro_a should have high plays count
    assert selector.weights["macro_a"]["plays"] > 10

    # Other macros should have lower plays count
    assert selector.weights["macro_b"]["plays"] < 5
    assert selector.weights["macro_c"]["plays"] < 5
