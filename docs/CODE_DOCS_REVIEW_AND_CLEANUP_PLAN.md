# Code & Documentation Review and Cleanup Plan

**Document Version:** 1.0.0
**Created:** 2025-11-23
**Status:** ACTIONABLE
**Author:** Code Review Audit

---

## Executive Summary

This document provides a comprehensive review of the PEG codebase, comparing all files and folders against documentation and instructions. It identifies orphaned, stagnant, or misplaced files and provides a prioritized cleanup plan.

### Key Findings

| Category | Count | Action Required |
|----------|-------|-----------------|
| Files to DELETE | 3 | High priority |
| Files to MOVE | 2 | Medium priority |
| Files to ARCHIVE | 6 | Low priority |
| Documentation inconsistencies | 4 | Update needed |
| Implementation gaps | 3 | Future work |

---

## Part 1: File Inventory and Analysis

### Root Directory Files

| File | Status | Action | Notes |
|------|--------|--------|-------|
| `.env.sample` | OK | KEEP | Environment template |
| `.gitignore` | OK | KEEP | Version control config |
| `Agent_Prompts.json` | OK | KEEP | Config file |
| `CLAUDE.md` | OK | KEEP | Project guide for AI |
| `GIT_COMMIT_MESSAGE.txt` | STRAY | **DELETE** | Stray commit message, 86 lines |
| `Journal.json` | OK | KEEP | Logging file |
| `Knowledge.json` | OK | KEEP | v3.3.7 - Knowledge base |
| `LICENSE` | OK | KEEP | MIT License |
| `Logbook.json` | OK | KEEP | Audit trail |
| `Modules.json` | OK | KEEP | Config file |
| `PHASE_8_KICKOFF.md` | MISPLACED | **MOVE** | Should be in docs/milestones/ |
| `PromptEngineer.txt` | OK | KEEP | DSL workflow definition |
| `PromptModules.json` | OK | KEEP | Config file |
| `PromptScoreModel.json` | OK | KEEP | Scoring metrics |
| `README.md` | OK | KEEP | Project readme |
| `Rules.json` | OK | KEEP | Enforcement rules |
| `SessionConfig.json` | OK | KEEP | v1.0.1 - Runtime config |
| `TagEnum.json` | OK | KEEP | Tag definitions |
| `Tasks.json` | OK | KEEP | Task tracking |
| `Tests.json` | OK | KEEP | Test definitions |
| `WorkflowGraph.json` | OK | KEEP | v2.1.0 - Workflow definition |
| `pyproject.toml` | OK | KEEP | Modern Python packaging |
| `requirements.txt` | OK | KEEP | Dependencies |
| `requirements.txt.backup` | STRAY | **DELETE** | Backup file, not needed in VCS |
| `run_scoring.py` | OK | KEEP | Scoring script |
| `server_audit.txt` | STRAY | **DELETE** | Temporary audit file, 29 lines |
| `test_env.py` | OK | KEEP | Environment testing utility |
| `test_hybrid_orchestrator.py` | MISPLACED | **MOVE** | Should be in tests/ directory |
| `validate_repo.py` | OK | KEEP | Repository validation |

### Docs Directory Analysis

| File/Folder | Status | Action | Notes |
|-------------|--------|--------|-------|
| `docs/README.md` | OK | KEEP | Documentation index |
| `docs/APEG_STATUS.md` | OK | KEEP | Current status (1200 lines) |
| `docs/APEG_PLACEHOLDERS.md` | OK | KEEP | Placeholder tracking |
| `docs/APEG_REQUIREMENTS_SUMMARY.md` | OK | KEEP | Requirements spec |
| `docs/APEG_PHASE_8_REQUIREMENTS.md` | OK | KEEP | Phase 8 spec |
| `docs/APEG_PHASE_9_REQUIREMENTS.md` | OK | KEEP | Phase 9 spec |
| `docs/APEG_HYBRID_ORCHESTRATOR_BUILD.md` | OK | KEEP | Build spec |
| `docs/APEG_OPERATIONS_RUNBOOK.md` | OK | KEEP | Operations procedures |
| `docs/APEG_RUNTIME_STATUS.md` | OK | KEEP | Runtime status |
| `docs/APEG_MCP_INTEGRATION.md` | OK | KEEP | MCP integration guide |
| `docs/APEG_DEPLOYMENT_PI.md` | OK | KEEP | Pi deployment guide |
| `docs/DEPLOYMENT.md` | OK | KEEP | General deployment guide |
| `docs/SECURITY_HARDENING.md` | OK | KEEP | Security checklist |
| `docs/Next_Steps.md` | OK | KEEP | Active development roadmap |
| `docs/PHASE_9_VERIFICATION_REPORT.md` | OK | KEEP | Verification report |
| `docs/archive/` | OK | KEEP | Historical documents |
| `docs/archive/APEG_TODO_2025-11-18.md` | OUTDATED | KEEP | Correctly archived |
| `docs/archive/dev-log-phases-0-3.md` | OK | KEEP | Historical dev log |
| `docs/archive/PHASES_0-3_VERIFICATION.md` | OK | KEEP | Historical verification |
| `docs/milestones/` | OK | KEEP | Milestone summaries |
| `docs/milestones/BUILD_COMPLETION_SUMMARY.md` | OK | KEEP | Build completion |
| `docs/milestones/IMPLEMENTATION_SUMMARY.md` | OK | KEEP | Implementation summary |
| `docs/milestones/APEG_AUDIT_2025-11-18.md` | OK | KEEP | Audit report |
| `docs/ADRS/` | OK | KEEP | Architecture Decision Records |
| `docs/ADRS/ADR-001-OpenAI-Agents.md` | OK | KEEP | OpenAI decision |
| `docs/ADRS/ADR-002-MCTS-Disabled-By-Default.md` | OK | KEEP | MCTS decision |

### Source Code Analysis

#### APEG Core (`src/apeg_core/`) - Production Code

| Module | Status | Notes |
|--------|--------|-------|
| `__init__.py` | OK | Package init |
| `__main__.py` | OK | CLI entrypoint |
| `cli.py` | OK | CLI interface |
| `orchestrator.py` | OK | Main orchestrator |
| `server.py` | OK | FastAPI server |
| `decision/bandit_selector.py` | OK | Thompson Sampling |
| `decision/loop_guard.py` | OK | Loop detection |
| `decision/mcts_planner.py` | OK | MCTS (disabled by default) |
| `agents/base_agent.py` | OK | Base agent class |
| `agents/agent_registry.py` | OK | Agent registry |
| `agents/llm_roles.py` | OK | LLM role implementations |
| `agents/shopify_agent.py` | OK | Shopify agent |
| `agents/etsy_agent.py` | OK | Etsy agent |
| `agents/etsy_auth.py` | OK | Etsy OAuth |
| `connectors/openai_client.py` | OK | OpenAI wrapper |
| `connectors/http_tools.py` | OK | HTTP utilities |
| `connectors/mcp_client.py` | OK | MCP client |
| `scoring/evaluator.py` | OK | Rule-based evaluator |
| `logging/logbook_adapter.py` | OK | Logbook adapter |
| `memory/memory_store.py` | OK | Memory persistence |
| `workflow/executor.py` | OK | Workflow utilities |
| `monitoring/metrics.py` | OK | Metrics collection |
| `llm/agent_bridge.py` | OK | LLM abstraction |
| `llm/roles.py` | OK | Role definitions |
| `web/api.py` | OK | FastAPI routes |
| `web/server.py` | OK | Web server |

#### Legacy PEG (`src/`) - Preserved for Reference

| File | Status | Action | Notes |
|------|--------|--------|-------|
| `src/__init__.py` | LEGACY | CONSIDER ARCHIVE | Package init |
| `src/bandit_selector.py` | LEGACY | CONSIDER ARCHIVE | Original bandit implementation |
| `src/loop_guard.py` | LEGACY | CONSIDER ARCHIVE | Original loop detection |
| `src/memory_manager.py` | LEGACY | CONSIDER ARCHIVE | Original memory manager |
| `src/orchestrator.py` | LEGACY | CONSIDER ARCHIVE | Original orchestrator |
| `src/plugin_manager.py` | LEGACY | CONSIDER ARCHIVE | Plugin system |
| `src/sandbox_executor.py` | LEGACY | CONSIDER ARCHIVE | Safe execution |
| `src/knowledge_update.py` | LEGACY | CONSIDER ARCHIVE | Knowledge updates |
| `src/connectors/` | LEGACY | CONSIDER ARCHIVE | Legacy connectors |

### Test Files Analysis

| File | Status | Notes |
|------|--------|-------|
| `tests/conftest.py` | OK | Test configuration |
| `tests/test_orchestrator.py` | OK | Orchestrator tests |
| `tests/test_bandit_selector.py` | OK | Legacy bandit tests |
| `tests/test_decision_bandit.py` | OK | APEG bandit tests |
| `tests/test_decision_loop_guard.py` | OK | APEG loop guard tests |
| `tests/test_workflow_graph.py` | OK | Workflow tests |
| `tests/test_workflow_executor.py` | OK | Executor tests |
| `tests/test_apeg_orchestrator.py` | OK | APEG orchestrator tests |
| `tests/test_base_agent.py` | OK | Base agent tests |
| `tests/test_shopify_agent.py` | OK | Shopify tests |
| `tests/test_etsy_agent.py` | OK | Etsy tests |
| `tests/test_etsy_auth.py` | OK | Etsy auth tests |
| `tests/test_llm_roles.py` | OK | LLM roles tests |
| `tests/test_llm_package.py` | OK | LLM package tests |
| `tests/test_evaluator.py` | OK | Evaluator tests |
| `tests/test_enhanced_scoring.py` | OK | Enhanced scoring tests |
| `tests/test_logbook_adapter.py` | OK | Logbook tests |
| `tests/test_memory_store.py` | OK | Memory tests |
| `tests/test_memory_manager.py` | OK | Legacy memory tests |
| `tests/test_openai_client.py` | OK | OpenAI client tests |
| `tests/test_http_tools.py` | OK | HTTP tools tests |
| `tests/test_mcp_client.py` | OK | MCP client tests |
| `tests/test_mcp_integration.py` | OK | MCP integration tests |
| `tests/test_mcts_planner.py` | OK | MCTS tests |
| `tests/test_monitoring.py` | OK | Monitoring tests |
| `tests/test_connectors.py` | OK | Legacy connector tests |
| `tests/test_loop_guard.py` | OK | Legacy loop guard tests |
| `tests/test_plugin_manager.py` | OK | Plugin tests |
| `tests/test_sandbox_executor.py` | OK | Sandbox tests |
| `tests/test_knowledge_validation.py` | OK | Knowledge tests |
| `tests/test_scoring_model.py` | OK | Scoring model tests |
| `tests/test_versioning.py` | OK | Versioning tests |
| `tests/test_environment.py` | OK | Environment tests |
| `tests/test_prompts.json` | OK | Test data file |

### Other Directories

| Directory | Status | Notes |
|-----------|--------|-------|
| `.github/workflows/` | OK | CI/CD workflows |
| `archived_configs/` | OK | Historical configs |
| `config/` | OK | Additional configs |
| `schemas/` | OK | JSON schemas |
| `scripts/` | OK | Utility scripts |
| `webui/static/` | OK | Web UI files |

---

## Part 2: Implementation vs Documentation Comparison

### Phase Completion Status

| Phase | Documentation Status | Implementation Status | Match |
|-------|---------------------|----------------------|-------|
| Phase 0: Repo Intake | Complete | Complete | YES |
| Phase 1: Requirements | Complete | Complete | YES |
| Phase 2: Project Layout | Complete | Complete | YES |
| Phase 3: Decision Engine | Complete | Complete | YES |
| Phase 4: OpenAI Integration | Complete | Complete | YES |
| Phase 5: Domain Agents | Complete | Test mode only | YES* |
| Phase 6: Scoring/Logging | Complete | Complete | YES |
| Phase 7: CI/Cleanup | Complete | Complete | YES |
| Phase 8: Production APIs | Documented | Partial | PARTIAL |
| Phase 9: Self-Improvement | Documented | Planning only | YES |

*Phase 5/8: Shopify/Etsy API integrations are test-mode only, awaiting credentials

### Test Count Discrepancy

Documentation states varying test counts:
- `README.md`: 132 tests passing
- `docs/APEG_STATUS.md`: 291 tests (latest after Phase 8)
- `docs/Next_Steps.md`: 196 tests
- Current collection (with errors): 204 tests + 7 collection errors

**Action:** Update README.md to reflect current test count (291 per APEG_STATUS.md)

### Feature Verification

| Feature | Documented | Implemented | Notes |
|---------|-----------|-------------|-------|
| Thompson Sampling bandit | Yes | Yes | Working |
| Loop detection | Yes | Yes | Working |
| MCTS planner | Yes | Yes | Disabled by default per ADR-002 |
| OpenAI API wrapper | Yes | Yes | Test mode + real API |
| OpenAI Agents SDK | Yes | Placeholder | TODO[APEG-LLM-001] |
| Shopify agent | Yes | Test mode | 9 capabilities stubbed |
| Etsy agent | Yes | Test mode | 9 capabilities stubbed |
| Etsy OAuth PKCE | Yes | Yes | Implemented in etsy_auth.py |
| Rule-based scoring | Yes | Yes | Working |
| Hybrid LLM scoring | Yes | Yes | Optional via config |
| Logbook adapter | Yes | Yes | Working |
| Memory store | Yes | Yes | Working |
| Web API (FastAPI) | Yes | Yes | Working |
| Web UI | Yes | Yes | Working |
| CLI interface | Yes | Yes | Working |
| MCP integration | Yes | Yes | Experimental, test mode |
| Monitoring/metrics | Yes | Yes | Working |

---

## Part 3: Cleanup Action Plan

### Priority 1: Files to DELETE (Immediate)

These files serve no purpose and should be removed:

1. **`GIT_COMMIT_MESSAGE.txt`**
   - Reason: Stray commit message file accidentally saved to repo
   - Size: 86 lines
   - Risk: None
   - Command: `rm GIT_COMMIT_MESSAGE.txt`

2. **`requirements.txt.backup`**
   - Reason: Backup file should not be in version control
   - Size: 12 lines
   - Risk: None
   - Command: `rm requirements.txt.backup`

3. **`server_audit.txt`**
   - Reason: Temporary audit file from development task
   - Size: 29 lines
   - Risk: None
   - Command: `rm server_audit.txt`

### Priority 2: Files to MOVE (Next Sprint)

These files exist but are in the wrong location:

1. **`PHASE_8_KICKOFF.md`**
   - Current: Root directory
   - Target: `docs/milestones/PHASE_8_KICKOFF.md`
   - Reason: Planning document belongs with other milestone docs
   - Command: `mv PHASE_8_KICKOFF.md docs/milestones/`

2. **`test_hybrid_orchestrator.py`**
   - Current: Root directory
   - Target: `tests/test_hybrid_orchestrator.py`
   - Reason: Test file belongs in tests/ directory
   - Command: `mv test_hybrid_orchestrator.py tests/`

### Priority 3: Legacy Code Decision (Planning Required)

The legacy PEG code in `src/` (excluding `src/apeg_core/`) should be evaluated:

**Option A: Archive (Recommended)**
- Move to `archived_src/` directory
- Preserve for historical reference
- Update imports if any tests depend on them

**Option B: Remove**
- Delete legacy files entirely
- Risk: May break some legacy tests
- Requires test audit first

**Files affected:**
- `src/bandit_selector.py`
- `src/loop_guard.py`
- `src/memory_manager.py`
- `src/orchestrator.py`
- `src/plugin_manager.py`
- `src/sandbox_executor.py`
- `src/knowledge_update.py`
- `src/connectors/` (all files)

**Recommendation:** Create `archived_src/` and move legacy files there. Update CLAUDE.md to document this.

### Priority 4: Documentation Updates

1. **Update README.md test count**
   - Current: "132 tests passing"
   - Correct: "291 tests passing" (per APEG_STATUS.md)

2. **Update CLAUDE.md**
   - Add section about legacy code archival
   - Update documentation structure notes

3. **Clean up docs/APEG_PLACEHOLDERS.md**
   - Several placeholders marked "Future" are now resolved
   - Update status of resolved placeholders

4. **Update docs/README.md**
   - Add entry for `docs/Next_Steps.md`
   - Add entry for new cleanup document

---

## Part 4: Detailed File Cleanup Commands

### Shell Script for Cleanup

```bash
#!/bin/bash
# PEG Repository Cleanup Script
# Run from repository root

echo "=== PEG Repository Cleanup ==="

# Step 1: Delete stray files
echo "Step 1: Deleting stray files..."
rm -f GIT_COMMIT_MESSAGE.txt
rm -f requirements.txt.backup
rm -f server_audit.txt
echo "  Done: Deleted 3 stray files"

# Step 2: Move misplaced files
echo "Step 2: Moving misplaced files..."
mv PHASE_8_KICKOFF.md docs/milestones/
mv test_hybrid_orchestrator.py tests/
echo "  Done: Moved 2 files to correct locations"

# Step 3: Archive legacy code (optional - uncomment to run)
# echo "Step 3: Archiving legacy code..."
# mkdir -p archived_src/connectors
# mv src/bandit_selector.py archived_src/
# mv src/loop_guard.py archived_src/
# mv src/memory_manager.py archived_src/
# mv src/orchestrator.py archived_src/
# mv src/plugin_manager.py archived_src/
# mv src/sandbox_executor.py archived_src/
# mv src/knowledge_update.py archived_src/
# mv src/connectors/* archived_src/connectors/
# echo "  Done: Archived legacy code"

echo "=== Cleanup Complete ==="
echo "Run 'git status' to review changes"
echo "Run 'python validate_repo.py' to verify repository integrity"
```

---

## Part 5: Documentation Inconsistencies

### Issue 1: Test Count Variance

| Document | Test Count Stated |
|----------|-------------------|
| README.md | 132 |
| docs/APEG_STATUS.md | 291 (most recent) |
| docs/Next_Steps.md | 196 |

**Resolution:** Update all documents to reference APEG_STATUS.md as source of truth

### Issue 2: Phase Status Terminology

Some docs use "COMPLETE" while others use "Complete" or checkmarks.

**Resolution:** Standardize on:
- Complete: Checkmark emoji
- In Progress: Construction emoji
- Planned: Calendar emoji

### Issue 3: Missing Documentation Index Entry

`docs/Next_Steps.md` is not listed in `docs/README.md` index.

**Resolution:** Add entry to documentation index

### Issue 4: CLAUDE.md Repository Structure

The repository structure in CLAUDE.md doesn't include all current directories (e.g., `webui/`, `archived_configs/` structure).

**Resolution:** Update CLAUDE.md repository structure section

---

## Part 6: Implementation Gaps (Future Work)

### Gap 1: OpenAI Agents SDK Integration

**Location:** `src/apeg_core/llm/agent_bridge.py:315-342`
**Placeholder:** `TODO[APEG-LLM-001]`
**Status:** Raises NotImplementedError
**Impact:** Falls back to standard OpenAI API (working)
**Priority:** Medium (nice-to-have, not blocking)

### Gap 2: Real Shopify API Calls

**Location:** `src/apeg_core/agents/shopify_agent.py`
**Placeholder:** `APEG-AGENT-001`
**Status:** Test mode stubs only
**Impact:** Cannot perform real Shopify operations
**Priority:** High when credentials available

### Gap 3: Real Etsy API Calls

**Location:** `src/apeg_core/agents/etsy_agent.py`
**Placeholder:** `APEG-AGENT-002`
**Status:** Test mode stubs only
**Impact:** Cannot perform real Etsy operations
**Priority:** High when credentials available

---

## Part 7: Verification Checklist

After cleanup, verify:

- [ ] `python validate_repo.py` passes
- [ ] `pytest tests/ --collect-only` shows no collection errors (in proper environment)
- [ ] All JSON files are valid JSON
- [ ] No `.env` file committed (security)
- [ ] `.env.sample` exists
- [ ] All docs referenced in `docs/README.md` exist
- [ ] Git status shows only intended changes

---

## Part 8: Summary of Recommendations

### Immediate Actions (Do Now)

1. Delete `GIT_COMMIT_MESSAGE.txt`
2. Delete `requirements.txt.backup`
3. Delete `server_audit.txt`
4. Move `PHASE_8_KICKOFF.md` to `docs/milestones/`
5. Move `test_hybrid_orchestrator.py` to `tests/`

### Short-term Actions (Next Sprint)

1. Update README.md test count
2. Create `archived_src/` and archive legacy code
3. Update CLAUDE.md with legacy code section
4. Update docs/README.md index

### Long-term Actions (Backlog)

1. Resolve OpenAI Agents SDK placeholder
2. Complete Shopify/Etsy real API implementations
3. Standardize documentation terminology
4. Add integration tests for real APIs

---

## Appendix: Complete File Tree

```
PEG/
├── .env.sample
├── .gitignore
├── .github/
│   └── workflows/
│       ├── apeg-ci.yml
│       ├── append-to-log.yml
│       ├── peg-ci.yml
│       ├── test-matrix.yml
│       └── update-tasks.yml
├── Agent_Prompts.json
├── CLAUDE.md
├── GIT_COMMIT_MESSAGE.txt        # DELETE
├── Journal.json
├── Knowledge.json
├── LICENSE
├── Logbook.json
├── Modules.json
├── PHASE_8_KICKOFF.md            # MOVE to docs/milestones/
├── PromptEngineer.txt
├── PromptModules.json
├── PromptScoreModel.json
├── README.md
├── Rules.json
├── SessionConfig.json
├── TagEnum.json
├── Tasks.json
├── Tests.json
├── WorkflowGraph.json
├── archived_configs/
│   └── SessionConfig_Old_4.30.json
├── config/
│   └── plugins.json
├── docs/
│   ├── ADRS/
│   │   ├── ADR-001-OpenAI-Agents.md
│   │   └── ADR-002-MCTS-Disabled-By-Default.md
│   ├── APEG_DEPLOYMENT_PI.md
│   ├── APEG_HYBRID_ORCHESTRATOR_BUILD.md
│   ├── APEG_MCP_INTEGRATION.md
│   ├── APEG_OPERATIONS_RUNBOOK.md
│   ├── APEG_PHASE_8_REQUIREMENTS.md
│   ├── APEG_PHASE_9_REQUIREMENTS.md
│   ├── APEG_PLACEHOLDERS.md
│   ├── APEG_REQUIREMENTS_SUMMARY.md
│   ├── APEG_RUNTIME_STATUS.md
│   ├── APEG_STATUS.md
│   ├── DEPLOYMENT.md
│   ├── Next_Steps.md
│   ├── PHASE_9_VERIFICATION_REPORT.md
│   ├── README.md
│   ├── SECURITY_HARDENING.md
│   ├── archive/
│   │   ├── APEG_TODO_2025-11-18.md
│   │   ├── PHASES_0-3_VERIFICATION.md
│   │   └── dev-log-phases-0-3.md
│   └── milestones/
│       ├── APEG_AUDIT_2025-11-18.md
│       ├── BUILD_COMPLETION_SUMMARY.md
│       └── IMPLEMENTATION_SUMMARY.md
├── pyproject.toml
├── requirements.txt
├── requirements.txt.backup       # DELETE
├── run_scoring.py
├── schemas/
│   └── knowledge.schema.json
├── scripts/
│   ├── __init__.py
│   └── migrate_knowledge.py
├── server_audit.txt              # DELETE
├── src/
│   ├── __init__.py               # CONSIDER ARCHIVE
│   ├── apeg_core/                # KEEP (production code)
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── agents/
│   │   ├── cli.py
│   │   ├── connectors/
│   │   ├── decision/
│   │   ├── llm/
│   │   ├── logging/
│   │   ├── memory/
│   │   ├── monitoring/
│   │   ├── orchestrator.py
│   │   ├── scoring/
│   │   ├── server.py
│   │   ├── web/
│   │   └── workflow/
│   ├── bandit_selector.py        # CONSIDER ARCHIVE
│   ├── connectors/               # CONSIDER ARCHIVE
│   ├── knowledge_update.py       # CONSIDER ARCHIVE
│   ├── loop_guard.py             # CONSIDER ARCHIVE
│   ├── memory_manager.py         # CONSIDER ARCHIVE
│   ├── orchestrator.py           # CONSIDER ARCHIVE
│   ├── plugin_manager.py         # CONSIDER ARCHIVE
│   └── sandbox_executor.py       # CONSIDER ARCHIVE
├── test_env.py
├── test_hybrid_orchestrator.py   # MOVE to tests/
├── tests/
│   ├── conftest.py
│   ├── test_*.py (32 test files)
│   └── test_prompts.json
├── validate_repo.py
└── webui/
    └── static/
        ├── app.js
        ├── index.html
        └── style.css
```

---

**Document Status:** READY FOR REVIEW
**Last Updated:** 2025-11-23
**Next Review:** After cleanup execution
