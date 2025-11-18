"""
Tests for loop guard (loop detection).

Tests cover:
- Basic loop detection
- No loop when macro changes
- No loop when score improves
- Edge cases (empty history, insufficient data)
- Loop statistics
"""

import pytest

from apeg_core.decision.loop_guard import detect_loop, get_loop_statistics


def test_detect_loop_basic():
    """Test basic loop detection with same macro and no improvement."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "review", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "review", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
    ]

    # Should detect loop (same macro 3 times, no improvement)
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is True


def test_detect_loop_no_loop_different_macros():
    """Test that different macros don't trigger loop detection."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro2", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
    ]

    # Should NOT detect loop (different macros)
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is False


def test_detect_loop_no_loop_with_improvement():
    """Test that score improvement prevents loop detection."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.78},  # +0.03 improvement
        {"node": "build", "macro": "macro1", "score": 0.81},  # +0.03 improvement
    ]

    # Should NOT detect loop (improvement > epsilon=0.02)
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is False


def test_detect_loop_small_improvement_still_loops():
    """Test that small improvements still trigger loop detection."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.751},  # +0.001 improvement
        {"node": "build", "macro": "macro1", "score": 0.752},  # +0.001 improvement
    ]

    # Should detect loop (improvement < epsilon=0.02)
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is True


def test_detect_loop_insufficient_data():
    """Test with insufficient build events."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
    ]

    # Should NOT detect loop (only 2 builds, need 3)
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is False


def test_detect_loop_empty_history():
    """Test with empty history."""
    history = []

    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is False


def test_detect_loop_filters_non_build_events():
    """Test that non-build events are filtered out."""
    history = [
        {"node": "intake", "score": 0},
        {"node": "prep", "score": 0},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "review", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "review", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "export", "score": 0.75},
    ]

    # Should detect loop despite non-build events
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is True


def test_detect_loop_custom_n():
    """Test with custom N parameter."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
    ]

    # Should detect loop with N=5
    is_loop = detect_loop(history, N=5, epsilon=0.02)
    assert is_loop is True

    # Should NOT detect if we only check last 2
    is_loop = detect_loop(history, N=2, epsilon=0.02)
    assert is_loop is True  # Still true because no improvement


def test_detect_loop_custom_epsilon():
    """Test with custom epsilon parameter."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.76},  # +0.01
        {"node": "build", "macro": "macro1", "score": 0.77},  # +0.01
    ]

    # Should detect loop with epsilon=0.02 (improvement < 0.02)
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is True

    # Should NOT detect loop with epsilon=0.005 (improvement > 0.005)
    is_loop = detect_loop(history, N=3, epsilon=0.005)
    assert is_loop is False


def test_detect_loop_missing_macro():
    """Test with build events missing macro field."""
    history = [
        {"node": "build", "score": 0.75},  # No macro field
        {"node": "build", "macro": "macro1", "score": 0.75},
    ]

    # Should NOT crash, should return False
    is_loop = detect_loop(history, N=2, epsilon=0.02)
    assert is_loop is False


def test_detect_loop_missing_score():
    """Test with build events missing score field."""
    history = [
        {"node": "build", "macro": "macro1"},  # No score field
        {"node": "build", "macro": "macro1"},
        {"node": "build", "macro": "macro1"},
    ]

    # Should use default score of 0
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is True


def test_get_loop_statistics_empty():
    """Test statistics with empty history."""
    stats = get_loop_statistics([])

    assert stats["total_builds"] == 0
    assert stats["macro_distribution"] == {}
    assert stats["longest_sequence"] == 0
    assert stats["last_macro"] is None


def test_get_loop_statistics_basic():
    """Test basic loop statistics."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro1", "score": 0.75},
        {"node": "build", "macro": "macro2", "score": 0.80},
        {"node": "build", "macro": "macro1", "score": 0.75},
    ]

    stats = get_loop_statistics(history)

    assert stats["total_builds"] == 4
    assert stats["macro_distribution"]["macro1"] == 3
    assert stats["macro_distribution"]["macro2"] == 1
    assert stats["longest_sequence"] == 2  # macro1 appears twice in a row
    assert stats["last_macro"] == "macro1"


def test_get_loop_statistics_longest_sequence():
    """Test longest sequence detection."""
    history = [
        {"node": "build", "macro": "macro1"},
        {"node": "build", "macro": "macro1"},
        {"node": "build", "macro": "macro1"},
        {"node": "build", "macro": "macro2"},
        {"node": "build", "macro": "macro1"},
        {"node": "build", "macro": "macro1"},
    ]

    stats = get_loop_statistics(history)

    assert stats["longest_sequence"] == 3  # macro1 three times in a row


def test_detect_loop_score_degradation():
    """Test that score degradation also triggers loop detection."""
    history = [
        {"node": "build", "macro": "macro1", "score": 0.80},
        {"node": "build", "macro": "macro1", "score": 0.79},  # -0.01 (degradation)
        {"node": "build", "macro": "macro1", "score": 0.78},  # -0.01 (degradation)
    ]

    # Should detect loop (no improvement, actually degrading)
    is_loop = detect_loop(history, N=3, epsilon=0.02)
    assert is_loop is True
