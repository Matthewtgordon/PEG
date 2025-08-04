import sys
import os
from collections import Counter

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from bandit_selector import choose_macro


def test_bandit_converges_on_best_macro():
    """
    Verifies that the bandit selector learns to prefer the macro
    with a higher success rate over time.
    """
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
    
    for _ in range(1000):
        choice = choose_macro(macros, history, config)
        choices.append(choice)

    # Count the choices
    counts = Counter(choices)

    # Assert that 'good_macro' was chosen significantly more often than 'bad_macro'
    assert counts['good_macro'] > counts['bad_macro']
    assert counts['good_macro'] > 800  # Expect strong convergence


def test_bandit_explores_with_no_history():
    """
    Verifies that with no history, the selector gives a chance
    to all macros (exploration).
    """
    macros = ['macro_A', 'macro_B', 'macro_C']
    history = []
    config = {"ci": {"minimum_score": 0.8}}

    choices = []
    for _ in range(300):
        choice = choose_macro(macros, history, config)
        choices.append(choice)

    counts = Counter(choices)

    # Assert that each macro was chosen at least once
    assert 'macro_A' in counts
    assert 'macro_B' in counts
    assert 'macro_C' in counts
    # Check that the distribution isn't wildly skewed
    assert counts['macro_A'] > 50
    assert counts['macro_B'] > 50
    assert counts['macro_C'] > 50
