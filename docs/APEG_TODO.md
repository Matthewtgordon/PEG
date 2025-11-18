# APEG Runtime - TODO List

**Last Updated:** 2025-11-18

## Priority: HIGH

### Phase 1: Requirements Consolidation
- [ ] Create APEG_REQUIREMENTS_SUMMARY.md from spec files
- [ ] Define core APEG components and acceptance criteria
- [ ] Document OpenAI Agents/Graph integration approach

### Phase 2: Project Layout and Packaging
- [ ] Create pyproject.toml (PEP 621 format)
- [ ] Set up src/apeg_core/ package structure:
  - [ ] Core: `__init__.py`, `orchestrator.py`
  - [ ] Decision: `bandit_selector.py`, `loop_guard.py`, `mcts_planner.py` (stub)
  - [ ] Agents: `base_agent.py`, `shopify_agent.py`, `etsy_agent.py`
  - [ ] Connectors: `openai_tools.py`, `github_tools.py`, `http_tools.py`
  - [ ] Workflow: `graph_executor.py`
  - [ ] Memory: `memory_manager.py`
  - [ ] Scoring: `evaluator.py`
  - [ ] Logging: `logbook_adapter.py`
- [ ] Create CLI entrypoint: `src/apeg_cli.py` or `src/apeg/__main__.py`
- [ ] Update/sync requirements.txt with pyproject.toml

### Phase 3: Port Decision Engine
- [ ] Port bandit_selector.py to src/apeg_core/decision/
- [ ] Port loop_guard.py to src/apeg_core/decision/
- [ ] Add type hints and improve documentation
- [ ] Create mcts_planner.py stub with placeholder
- [ ] Create/update tests:
  - [ ] tests/test_decision_bandit.py
  - [ ] tests/test_decision_loop_guard.py
- [ ] Run pytest and fix failures
- [ ] Register MCTS placeholder in APEG_PLACEHOLDERS.md

### Phase 4: Workflow Orchestrator + OpenAI Agents/Graph
- [ ] Research current OpenAI Python SDK Agents/Graph APIs
- [ ] Implement APEGOrchestrator class
- [ ] Implement openai_tools.py connector
- [ ] Implement graph_executor.py
- [ ] Create simple CLI demo workflow
- [ ] Create tests/test_orchestrator_apeg.py
- [ ] Test config loading and simple workflow execution

### Phase 5: Domain Agents
- [ ] Implement base_agent.py interface
- [ ] Implement shopify_agent.py with stub methods
- [ ] Implement etsy_agent.py with stub methods
- [ ] Implement http_tools.py with test mode support
- [ ] Create tests/test_agents_shopify.py
- [ ] Create tests/test_agents_etsy.py
- [ ] Document all placeholders in APEG_PLACEHOLDERS.md

### Phase 6: Scoring, Logging, Adoption Gate
- [ ] Implement scoring/evaluator.py
- [ ] Implement logging/logbook_adapter.py
- [ ] Integrate scoring with bandit_selector
- [ ] Implement adoption gate in orchestrator
- [ ] Create tests/test_scoring_apeg.py
- [ ] Create tests/test_logging_apeg.py
- [ ] Create tests/test_adoption_gate.py

### Phase 7: CI, Runtime Status, and Cleanup
- [ ] Create/update .github/workflows/apeg-ci.yml
- [ ] Configure Python 3.11+ testing
- [ ] Run full test suite in CI
- [ ] Create APEG_RUNTIME_STATUS.md
- [ ] Move obsolete files to archived_configs/ or archived_src/
- [ ] Document legacy files in APEG_STATUS.md
- [ ] Final verification and cleanup

## Priority: MEDIUM

### Documentation
- [ ] Maintain APEG_PLACEHOLDERS.md throughout development
- [ ] Keep APEG_STATUS.md updated after each phase
- [ ] Document architectural decisions
- [ ] Create API documentation for key modules

### Testing
- [ ] Achieve >80% test coverage
- [ ] Add integration tests
- [ ] Add end-to-end workflow tests
- [ ] Performance benchmarks for bandit selector

## Priority: LOW

### Future Enhancements
- [ ] MCTS planner implementation (currently stub)
- [ ] Real Shopify API integration (currently stub)
- [ ] Real Etsy API integration (currently stub)
- [ ] Enhanced scoring models
- [ ] Telemetry and monitoring
- [ ] Performance optimization

---

## Backlog Items from Existing PEG

From Tasks.json:
- [ ] Consolidate legacy prompt rules into Knowledge.json format (T005)
- [ ] Finish export and version-stamp all system files (T006)

From Notes:
- Consider migration strategy for existing PEG data
- Plan backward compatibility approach
- Document migration path from PEG to APEG
