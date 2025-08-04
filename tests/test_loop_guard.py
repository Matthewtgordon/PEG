import sys
import os

# Add the 'src' directory to the Python path to find the loop_guard module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from loop_guard import detect_loop

def test_loop_guard_triggers_on_repeat_with_no_improvement():
    """
    Verifies that the loop guard triggers after N repeats
    of the same macro without significant score improvement.
    """
    # Simulate a history where 'macro_A' is repeated 3 times with no real progress
    history = [
        {'node': 'build', 'macro': 'macro_A', 'score': 0.70},
        {'node': 'build', 'macro': 'macro_A', 'score': 0.71}, # Improvement is <= epsilon
        {'node': 'build', 'macro': 'macro_A', 'score': 0.71}  # No improvement
    ]
    
    # Use default N=3 and epsilon=0.02
    assert detect_loop(history, N=3, epsilon=0.02) is True

def test_loop_guard_does_not_trigger_with_improvement():
    """
    Verifies that the loop guard does not trigger if there is
    sufficient score improvement.
    """
    history = [
        {'node': 'build', 'macro': 'macro_A', 'score': 0.70},
        {'node': 'build', 'macro': 'macro_A', 'score': 0.73}, # Improvement > epsilon
        {'node': 'build', 'macro': 'macro_A', 'score': 0.74}
    ]
    
    assert detect_loop(history, N=3, epsilon=0.02) is False

def test_loop_guard_does_not_trigger_on_different_macros():
    """
    Verifies that the loop guard does not trigger if different
    macros are used.
    """
    history = [
        {'node': 'build', 'macro': 'macro_A', 'score': 0.70},
        {'node': 'build', 'macro': 'macro_B', 'score': 0.70},
        {'node': 'build', 'macro': 'macro_A', 'score': 0.70}
    ]
    
    assert detect_loop(history, N=3, epsilon=0.02) is False
