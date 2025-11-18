# APEG Runtime - Placeholder Register

**Last Updated:** 2025-11-18

## Purpose
This file tracks all placeholder implementations in the APEG codebase. Each placeholder represents functionality that is stubbed or incomplete and requires future implementation.

## Placeholder Format
```
- id: APEG-PH-{number}
  file: {relative/path/to/file.py}
  line_hint: {description of location}
  summary: {what needs to be implemented}
  priority: {high|medium|low}
  status: {planned|in_progress|deferred}
```

---

## Active Placeholders

### Phase 3: MCTS Planner (Decision Engine)

- **id:** APEG-PH-1
  **file:** src/apeg_core/decision/mcts_planner.py
  **line_hint:** Entire file - MCTSPlanner class
  **summary:** Implement MCTS planning algorithm for multi-step macro selection using UCT
  **priority:** medium
  **status:** planned

### Phase 4-6: Orchestrator Integration

- **id:** APEG-PH-3
  **file:** src/apeg_core/orchestrator.py
  **line_hint:** _execute_node method, "review" node, line ~190
  **summary:** Integrate scoring system for output evaluation
  **priority:** high
  **status:** planned

- **id:** APEG-PH-4
  **file:** src/apeg_core/orchestrator.py
  **line_hint:** _execute_node method, various nodes
  **summary:** Integrate agent calls for domain-specific operations (Shopify, Etsy)
  **priority:** high
  **status:** planned

### Phase 5: Domain Agents
*(Placeholders will be added during implementation)*

### Phase 6: Scoring & Logging
*(Placeholders will be added during implementation)*

---

## Completed Placeholders

- **APEG-PH-2**: ✅ Integrated decision engine (bandit selector + loop guard) into orchestrator
  - **Resolved:** Phase 3
  - **Files:** src/apeg_core/orchestrator.py lines 175-214
  - **Date:** 2025-11-18

---

## Deferred Placeholders
*(None yet)*

---

## Notes
- All placeholders in code must be marked as: `# TODO[APEG-PH-x]: description`
- This register is the single source of truth for placeholder tracking
- Placeholders should be minimized - only create when absolutely necessary
- Each placeholder must have a clear path to implementation or removal
- APEG-PH-1 (MCTS Planner) is intentionally deferred as it's not required for basic functionality
