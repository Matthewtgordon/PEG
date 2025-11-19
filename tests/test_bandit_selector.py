import sys
import os
from collections import Counter
from pathlib import Path
import tempfile
import shutil

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from bandit_selector import BanditSelector


def test_bandit_converges_on_best_macro():
    """
    Verifies that the bandit selector learns to prefer the macro
    with a higher success rate over time.
    """
    # Use a temporary weights file to avoid pollution from other tests
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        temp_weights_path = Path(tmp.name)
        tmp.write('{}')

    try:
        macros = ['bad_macro', 'good_macro']

        # Create a history where 'good_macro' has a 90% success rate
        # and 'bad_macro' has a 10% success rate.
        # The bandit selector expects history entries with 'node' == 'build' and 'score' field
        history = []
        for i in range(100):
            # Good macro has 90% success rate (score >= 0.8)
            history.append({
                'node': 'build',
                'macro': 'good_macro',
                'score': 0.9 if i < 90 else 0.3
            })
            # Bad macro has 10% success rate (score >= 0.8)
            history.append({
                'node': 'build',
                'macro': 'bad_macro',
                'score': 0.9 if i < 10 else 0.3
            })

        # Run the selector many times to see which macro it prefers
        choices = []
        config = {"ci": {"minimum_score": 0.8}}

        selector = BanditSelector(weights_path=temp_weights_path)
        for _ in range(1000):
            choice = selector.choose(macros, history, config)
            choices.append(choice)

        # Count the choices
        counts = Counter(choices)

        # Assert that 'good_macro' was chosen significantly more often than 'bad_macro'
        assert counts['good_macro'] > counts['bad_macro']
        assert counts['good_macro'] > 800  # Expect strong convergence
    finally:
        # Clean up temporary file
        if temp_weights_path.exists():
            temp_weights_path.unlink()


def test_bandit_explores_with_no_history():
    """
    Verifies that with no history, the selector gives a chance
    to all macros (exploration).
    """
    # Use a temporary weights file to avoid pollution from other tests
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        temp_weights_path = Path(tmp.name)
        tmp.write('{}')

    try:
        macros = ['macro_A', 'macro_B', 'macro_C']
        history = []
        config = {"ci": {"minimum_score": 0.8}}

        choices = []
        selector = BanditSelector(weights_path=temp_weights_path)
        for _ in range(300):
            choice = selector.choose(macros, history, config)
            choices.append(choice)

        counts = Counter(choices)

        # Assert that each macro was chosen at least once
        assert 'macro_A' in counts, f"macro_A not chosen. Counts: {counts}"
        assert 'macro_B' in counts, f"macro_B not chosen. Counts: {counts}"
        assert 'macro_C' in counts, f"macro_C not chosen. Counts: {counts}"
        # Check that the distribution isn't wildly skewed
        assert counts['macro_A'] > 50, f"macro_A chosen {counts['macro_A']} times (expected > 50)"
        assert counts['macro_B'] > 50, f"macro_B chosen {counts['macro_B']} times (expected > 50)"
        assert counts['macro_C'] > 50, f"macro_C chosen {counts['macro_C']} times (expected > 50)"
    finally:
        # Clean up temporary file
        if temp_weights_path.exists():
            temp_weights_path.unlink()
