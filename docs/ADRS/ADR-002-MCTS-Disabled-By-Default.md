# ADR-002: Keep MCTS Implemented but Disabled by Default

## Status
Accepted

## Date
2025-11-22

## Context
APEG's decision engine currently uses Thompson Sampling (bandit algorithm) for macro
selection. This provides a balance of exploration vs exploitation for single-step decisions.

For multi-step planning scenarios, Monte Carlo Tree Search (MCTS) offers potential benefits:
- Look-ahead planning for macro sequences
- Better handling of long-horizon workflows
- State-space exploration for complex decision trees

However, MCTS adds complexity and may not be necessary for all workflows.

## Decision
We will:

1. **Implement MCTS fully** in `src/apeg_core/decision/mcts_planner.py`
   - Complete UCB1-based tree search
   - MacroState class for workflow state representation
   - Configurable iterations, exploration weight, and depth

2. **Keep MCTS inactive by default**
   - Config flag: `enable_mcts_planner: false`
   - Orchestrator uses bandit-only approach when flag is false
   - No performance impact when disabled

3. **Use bandit + scoring as primary decision engine**
   - Proven, simpler approach
   - Well-integrated with Evaluator scores
   - Lower computational overhead

## Implementation

### MCTS Planner
```python
from apeg_core.decision.mcts_planner import MCTSPlanner

planner = MCTSPlanner(config={
    "iterations": 100,
    "exploration_weight": 1.414,
    "max_depth": 5
})
plan = planner.plan(macros, state, depth=3)
```

### Configuration
```json
{
  "enable_mcts_planner": false,
  "mcts": {
    "iterations": 100,
    "exploration_weight": 1.414,
    "max_depth": 5
  }
}
```

### Feature Flag Check
```python
if config.get("enable_mcts_planner"):
    planner = MCTSPlanner(config.get("mcts", {}))
    plan = planner.plan(macros, state)
else:
    # Use existing bandit selector
    macro = choose_macro(macros, history, config)
```

## Consequences

### Positive
- MCTS available for complex planning scenarios
- Zero overhead when disabled
- Clean isolation from existing decision logic
- Comprehensive test coverage for MCTS

### Negative
- Additional code to maintain
- Potential confusion about when to enable
- MCTS effectiveness not yet validated

### Neutral
- Research feature for experimentation
- May be promoted to default in future phases

## Testing
MCTS is tested independently in `tests/test_mcts_planner.py`:
- Node expansion and visit counts
- UCB1 value calculation
- Plan extraction from search tree
- Statistics tracking

## Future Work
- Enable MCTS for specific workflow types
- Integrate MCTS planning with Evaluator scores
- Benchmark MCTS vs bandit performance
- Hybrid approach (MCTS for planning, bandit for execution)

## References
- UCB1 algorithm (Auer et al., 2002)
- src/apeg_core/decision/mcts_planner.py
- tests/test_mcts_planner.py
