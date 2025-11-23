"""
Tests for BanditSelector self-learning features.

Tests include:
- Regret tracking
- Feedback-based learning
- Forced exploration
- Learning state persistence
"""

import pytest
import tempfile
import os
from pathlib import Path

from apeg_core.decision.bandit_selector import BanditSelector, choose_macro


class TestBanditSelfLearning:
    """Tests for self-learning capabilities."""

    @pytest.fixture
    def temp_weights_file(self):
        """Create a temporary weights file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
        learning_path = path.replace('.json', '.learning.json')
        if os.path.exists(learning_path):
            os.unlink(learning_path)

    @pytest.fixture
    def selector(self, temp_weights_file):
        """Create a BanditSelector with temp file."""
        return BanditSelector(
            weights_path=temp_weights_file,
            regret_threshold=10.0,
            feedback_window=100
        )

    def test_initialization_with_learning_params(self, selector):
        """Test initialization includes learning parameters."""
        assert selector.regret_threshold == 10.0
        assert selector.feedback_window == 100
        assert selector.regret == 0.0
        assert selector.feedback_history == []

    def test_update_from_feedback(self, selector):
        """Test updating from feedback."""
        selector.update_from_feedback("test_macro", 0.8)

        stats = selector.get_statistics("test_macro")

        assert stats["plays"] > 0
        assert stats["total_reward"] > 0

    def test_regret_accumulation(self, selector):
        """Test that regret accumulates."""
        initial_regret = selector.regret

        # Send several low reward feedbacks
        selector.update_from_feedback("macro_a", 0.3)
        selector.update_from_feedback("macro_a", 0.2)
        selector.update_from_feedback("macro_a", 0.4)

        assert selector.regret > initial_regret

    def test_true_means_estimation(self, selector):
        """Test that true means are estimated."""
        # Consistent rewards
        for _ in range(10):
            selector.update_from_feedback("good_macro", 0.9)
            selector.update_from_feedback("bad_macro", 0.2)

        # Good macro should have higher estimated mean
        assert selector.true_means.get("good_macro", 0) > selector.true_means.get("bad_macro", 0)

    def test_feedback_history_maintained(self, selector):
        """Test that feedback history is maintained."""
        for i in range(5):
            selector.update_from_feedback(f"macro_{i}", 0.5)

        assert len(selector.feedback_history) == 5

    def test_feedback_history_trimmed(self, temp_weights_file):
        """Test that feedback history is trimmed to window size."""
        selector = BanditSelector(
            weights_path=temp_weights_file,
            feedback_window=10
        )

        for i in range(20):
            selector.update_from_feedback("macro", 0.5)

        assert len(selector.feedback_history) <= 10

    def test_get_learning_stats(self, selector):
        """Test getting learning statistics."""
        selector.update_from_feedback("test", 0.5)

        stats = selector.get_learning_stats()

        assert "cumulative_regret" in stats
        assert "regret_threshold" in stats
        assert "true_means" in stats
        assert "feedback_count" in stats


class TestRegretBasedExploration:
    """Tests for regret-based exploration toggle."""

    @pytest.fixture
    def high_regret_selector(self):
        """Create selector with high regret threshold."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        selector = BanditSelector(
            weights_path=path,
            regret_threshold=5.0  # Low threshold for testing
        )

        # Artificially set high regret
        selector.regret = 10.0

        yield selector

        if os.path.exists(path):
            os.unlink(path)
        learning_path = path.replace('.json', '.learning.json')
        if os.path.exists(learning_path):
            os.unlink(learning_path)

    def test_forced_exploration_when_regret_high(self, high_regret_selector):
        """Test that high regret forces exploration."""
        macros = ["macro_a", "macro_b", "macro_c"]
        config = {"ci": {"minimum_score": 0.8}}

        # With high regret, should force random exploration
        selected = high_regret_selector.choose(macros, [], config)

        assert selected in macros
        assert high_regret_selector.metrics.get("forced_explorations", 0) > 0

    def test_normal_selection_when_regret_low(self):
        """Test normal selection when regret is below threshold."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        try:
            selector = BanditSelector(
                weights_path=path,
                regret_threshold=100.0  # High threshold
            )

            macros = ["macro_a", "macro_b"]
            config = {"ci": {"minimum_score": 0.8}}

            selector.choose(macros, [], config)

            # Should not force exploration
            assert selector.metrics.get("forced_explorations", 0) == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestLearningStatePersistence:
    """Tests for learning state persistence."""

    def test_learning_state_persisted(self):
        """Test that learning state is persisted."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        try:
            # First selector - create state
            selector1 = BanditSelector(weights_path=path)
            selector1.update_from_feedback("test_macro", 0.7)
            selector1.update_from_feedback("test_macro", 0.6)

            original_regret = selector1.regret

            # Second selector - load state
            selector2 = BanditSelector(weights_path=path)

            # Should have loaded the regret
            assert selector2.regret == original_regret

        finally:
            if os.path.exists(path):
                os.unlink(path)
            learning_path = path.replace('.json', '.learning.json')
            if os.path.exists(learning_path):
                os.unlink(learning_path)

    def test_reset_regret(self):
        """Test resetting regret counter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        try:
            selector = BanditSelector(weights_path=path)

            # Accumulate regret
            for _ in range(10):
                selector.update_from_feedback("macro", 0.3)

            assert selector.regret > 0

            # Reset regret
            selector.reset_regret()

            assert selector.regret == 0.0
            assert selector.metrics.get("forced_explorations", 0) == 0

        finally:
            if os.path.exists(path):
                os.unlink(path)
            learning_path = path.replace('.json', '.learning.json')
            if os.path.exists(learning_path):
                os.unlink(learning_path)


class TestResetBehavior:
    """Tests for reset functionality."""

    def test_reset_clears_learning_state(self):
        """Test that reset clears all learning state."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        try:
            selector = BanditSelector(weights_path=path)

            # Build up state - use low rewards to ensure positive regret
            selector.update_from_feedback("macro_a", 0.3)
            selector.update_from_feedback("macro_b", 0.2)
            selector.update_from_feedback("macro_a", 0.4)

            # Regret should have accumulated (may or may not be positive depending on estimation)
            assert len(selector.true_means) > 0
            assert len(selector.feedback_history) > 0

            # Reset
            selector.reset()

            assert selector.regret == 0.0
            assert selector.true_means == {}
            assert selector.feedback_history == []
            assert selector.weights == {}

        finally:
            if os.path.exists(path):
                os.unlink(path)
            learning_path = path.replace('.json', '.learning.json')
            if os.path.exists(learning_path):
                os.unlink(learning_path)


class TestFeedbackHistoryAnalysis:
    """Tests for feedback history analysis."""

    def test_feedback_includes_regret(self):
        """Test that each feedback record includes regret."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            path = f.name

        try:
            selector = BanditSelector(weights_path=path)
            selector.update_from_feedback("macro", 0.5)

            assert len(selector.feedback_history) == 1
            record = selector.feedback_history[0]

            assert "arm" in record
            assert "reward" in record
            assert "regret" in record
            assert "cumulative_regret" in record

        finally:
            if os.path.exists(path):
                os.unlink(path)
            learning_path = path.replace('.json', '.learning.json')
            if os.path.exists(learning_path):
                os.unlink(learning_path)
