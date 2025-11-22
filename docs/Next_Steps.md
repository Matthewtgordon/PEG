# APEG Next Steps - Development Roadmap

**Document Version:** 1.0.0
**Created:** 2025-11-22
**Status:** Active Development
**Author:** Development Team

---

## Executive Summary

This document outlines the priority next steps for completing the APEG (Agentic Prompt Engine with Graph) implementation. Based on comprehensive analysis of the codebase, documentation, and Phase 8 requirements, this guide provides actionable items for continued development.

### Current Status Overview

| Phase | Status | Test Coverage |
|-------|--------|---------------|
| Phase 0-2 (Foundation) | Complete | Core tests passing |
| Phase 3 (Decision Engine) | Complete | Bandit selector integrated |
| Phase 4 (Agent Framework) | Complete | BaseAgent + registry |
| Phase 5 (Domain Agents) | Partial | Stubs functional, awaiting credentials |
| Phase 6 (Evaluator) | Complete | Adoption gate operational |
| Phase 7 (Connectors) | Partial | HTTP tools complete, OpenAI test mode |
| Phase 8 (Enhancements) | In Progress | LLM bridge, MCTS, monitoring complete |

**Tests:** 196 tests passing (as of Phase 8 implementation)

---

## Priority 1: Critical Path Items

These items are required for production readiness.

### 1.1 Shopify API Integration (APEG-AGENT-001)

**Status:** Partial - `ShopifyAPIClient` implemented, some methods still stub
**Location:** `src/apeg_core/agents/shopify_agent.py`
**Effort:** Medium
**Prerequisites:** Shopify API credentials (store domain, access token)

**Current State:**
- `ShopifyAPIClient` class implemented with HTTP methods (lines 51-116)
- `list_products()` and `get_product()` have real API implementations (lines 245-357)
- `update_inventory()`, `list_orders()`, `fulfill_order()`, `cancel_order()` remain stubs

**Remaining Tasks:**
1. Implement `update_inventory()` via Shopify Inventory API
2. Implement `list_orders()` via Orders API
3. Implement `get_order()` for detailed order retrieval
4. Implement `fulfill_order()` with tracking number support
5. Implement `cancel_order()` with reason handling
6. Add webhook handlers for order notifications
7. Implement rate limiting (2 calls/second for standard plans)

**Acceptance Criteria:**
- [ ] All 9 capabilities work with real Shopify API
- [ ] Graceful fallback to test mode without credentials
- [ ] Rate limiting respects Shopify's limits
- [ ] Error handling for common API errors (401, 404, 429)

**Code Reference:**
```python
# src/apeg_core/agents/shopify_agent.py:359-394
def update_inventory(self, product_id: str, variant_id: str | None = None, new_quantity: int = 0):
    # TODO[APEG-PH-5]: Replace with real Shopify API call
```

### 1.2 Etsy API Integration (APEG-AGENT-002)

**Status:** Stub only - No real API implementation
**Location:** `src/apeg_core/agents/etsy_agent.py`
**Effort:** High
**Prerequisites:** Etsy API key, shop ID, OAuth 2.0 setup

**Current State:**
- All 9 methods are stubs (lines 99-427)
- OAuth 2.0 PKCE flow not implemented
- Token refresh not implemented

**Remaining Tasks:**
1. Implement OAuth 2.0 PKCE authentication flow
2. Create `EtsyAPIClient` class (similar to `ShopifyAPIClient`)
3. Implement token storage and automatic refresh
4. Implement `list_listings()` via `/v3/application/shops/{shop_id}/listings`
5. Implement `create_listing()` with required fields
6. Implement `update_listing()` and `update_inventory()`
7. Implement `list_orders()` via receipts endpoint
8. Implement `ship_order()` with tracking
9. Implement `send_customer_message()` via conversations API
10. Implement `suggest_listing_seo()` with ENGINEER LLM role integration

**Acceptance Criteria:**
- [ ] OAuth 2.0 PKCE flow completes successfully
- [ ] Token auto-refresh before expiration
- [ ] All 9 capabilities work with real Etsy API v3
- [ ] SEO suggestions integrate with LLM ENGINEER role

**API Reference:**
- Base URL: `https://openapi.etsy.com/v3`
- Authentication: OAuth 2.0 with PKCE
- Rate Limit: 10 requests/second

### 1.3 OpenAI Agents SDK Integration (APEG-LLM-001)

**Status:** Placeholder - Currently falls back to OpenAI API
**Location:** `src/apeg_core/llm/agent_bridge.py:315-342`
**Effort:** Medium
**Prerequisites:** OpenAI Agents SDK access, project ID

**Current State:**
- `AgentsBridge._run_via_agents_sdk()` raises `NotImplementedError`
- Fallback to `_run_via_openai_api()` works correctly
- Test mode provides deterministic responses

**Remaining Tasks:**
1. Install and configure OpenAI Agents SDK
2. Implement agent creation for each LLM role
3. Implement `_run_via_agents_sdk()` with proper error handling
4. Add agent state persistence (optional)
5. Test SDK integration with all 8 roles

**Code Reference:**
```python
# src/apeg_core/llm/agent_bridge.py:315-342
def _run_via_agents_sdk(self, role, role_config, prompt, context, **kwargs):
    # TODO[APEG-LLM-001]: Real Agents SDK integration
    raise NotImplementedError("OpenAI Agents SDK integration not yet implemented.")
```

---

## Priority 2: Enhancement Items

These items improve functionality but are not blocking.

### 2.1 Scoring System Integration in Orchestrator

**Status:** Partial integration
**Location:** `src/apeg_core/orchestrator.py:223`
**Placeholder:** APEG-PH-3

**Current State:**
- Evaluator module complete
- Adoption gate operational
- Orchestrator has placeholder for scoring calls

**Remaining Tasks:**
1. Connect orchestrator's review node to Evaluator
2. Implement score-based routing at review node
3. Add SCORER role calls for output evaluation
4. Integrate scoring with bandit selector feedback

### 2.2 Enable MCTS for Specific Workflows

**Status:** Implemented but inactive by default
**Location:** `src/apeg_core/decision/mcts_planner.py`
**ADR:** ADR-002-MCTS-Disabled-By-Default

**Current State:**
- Complete UCB1-based MCTS implementation
- 19 tests passing
- Feature flag: `enable_mcts_planner: false`

**Remaining Tasks:**
1. Create workflow type detection logic
2. Enable MCTS for multi-step planning scenarios
3. Benchmark MCTS vs bandit selector performance
4. Document when to enable MCTS

**Configuration:**
```json
{
  "enable_mcts_planner": true,
  "mcts": {
    "iterations": 100,
    "exploration_weight": 1.414,
    "max_depth": 5
  }
}
```

### 2.3 Monitoring and Telemetry Dashboard

**Status:** Metrics collection implemented
**Location:** `src/apeg_core/monitoring/metrics.py`

**Current State:**
- MetricsRecorder with counter, gauge, histogram support
- Prometheus-compatible export format
- 21 tests passing

**Remaining Tasks:**
1. Add HTTP endpoint for Prometheus scraping
2. Create Grafana dashboard templates
3. Add workflow execution timing metrics
4. Add LLM token usage tracking
5. Create alerting rules for error rates

---

## Priority 3: Documentation and Quality

### 3.1 API Documentation

**Tasks:**
1. Generate API documentation from docstrings
2. Create integration guides for Shopify/Etsy
3. Document LLM role usage patterns
4. Add workflow configuration examples

### 3.2 Placeholder Cleanup

**File:** `docs/APEG_PLACEHOLDERS.md`

**Active Placeholders to Resolve:**
| ID | Description | Phase |
|----|-------------|-------|
| APEG-CONN-001 | OpenAI API Real Calls | Phase 8 |
| APEG-AGENT-001 | Shopify API Real Implementation | Phase 5 |
| APEG-AGENT-002 | Etsy API Real Implementation | Phase 5 |
| APEG-PH-3 | Scoring System Integration | Phase 6 |

### 3.3 Test Coverage Expansion

**Current:** 196 tests
**Target:** 250+ tests

**Areas Needing Tests:**
1. Integration tests for real API calls (requires credentials)
2. End-to-end workflow execution tests
3. Error recovery and fallback tests
4. Performance/load tests for metrics

---

## Priority 4: Future Development Directions

### 4.1 Plugin Architecture Enhancement

Extend the agent registry to support dynamic plugin loading:
- Load agents from external packages
- Support for custom connectors
- Webhook plugin system

**Reference:** `src/apeg_core/agents/agent_registry.py`

### 4.2 Multi-Provider LLM Support

Extend `AgentsBridge` to support:
- Anthropic Claude via claude-sdk
- Google Gemini via google-generativeai
- Local models via LMStudio/Ollama

### 4.3 Cross-Platform Inventory Sync

Implement bidirectional sync between Shopify and Etsy:
- Real-time inventory updates
- Order synchronization
- Price parity management

**Reference:** `src/apeg_core/agents/shopify_agent.py:457-489` (`create_order_from_etsy`)

### 4.4 Workflow Templates

Create reusable workflow templates:
- Product launch workflow
- SEO optimization workflow
- Order fulfillment workflow
- Customer support workflow

---

## Implementation Guidelines

### Environment Setup

Required environment variables for production:
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Shopify
SHOPIFY_STORE_DOMAIN=mystore.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
SHOPIFY_API_VERSION=2024-01

# Etsy
ETSY_API_KEY=...
ETSY_API_SECRET=...
ETSY_SHOP_ID=...
ETSY_ACCESS_TOKEN=...
ETSY_REFRESH_TOKEN=...

# Optional
APEG_TEST_MODE=false
APEG_USE_AGENTS_SDK=false
```

### Development Workflow

1. Create feature branch: `git checkout -b feature/<name>`
2. Implement with tests: Maintain test coverage
3. Run validation: `python validate_repo.py`
4. Run tests: `pytest tests/`
5. Check CI: Ensure all checks pass
6. Create PR with clear description

### Code Standards

- Type hints on all functions
- Docstrings following Google style
- Logging with appropriate levels
- Error handling with specific exceptions
- Test mode fallback for all external calls

---

## Collaboration and Progress Tracking

### Recommended Sprint Structure

**Sprint 1 (Focus: Shopify):**
- Complete Shopify API integration
- Add integration tests with mock server
- Document Shopify setup process

**Sprint 2 (Focus: Etsy):**
- Implement OAuth 2.0 PKCE flow
- Complete Etsy API integration
- Add integration tests

**Sprint 3 (Focus: LLM & Scoring):**
- Implement OpenAI Agents SDK integration
- Complete scoring system integration
- Performance optimization

**Sprint 4 (Focus: Polish):**
- Monitoring dashboard
- Documentation completion
- Production deployment guide

### Progress Metrics

Track these metrics to measure progress:
- Test count (target: 250+)
- Placeholder resolution rate
- API integration coverage
- Documentation completeness

### Issue Tracking

For each remaining task, create issues with:
- Clear acceptance criteria
- Reference to relevant code locations
- Dependencies on other tasks
- Estimated effort

---

## Quick Reference: Code Locations

| Component | Location | Status |
|-----------|----------|--------|
| Orchestrator | `src/apeg_core/orchestrator.py` | Complete |
| Bandit Selector | `src/apeg_core/decision/bandit_selector.py` | Complete |
| MCTS Planner | `src/apeg_core/decision/mcts_planner.py` | Complete (inactive) |
| LLM Bridge | `src/apeg_core/llm/agent_bridge.py` | Partial |
| LLM Roles | `src/apeg_core/llm/roles.py` | Complete |
| Shopify Agent | `src/apeg_core/agents/shopify_agent.py` | Partial |
| Etsy Agent | `src/apeg_core/agents/etsy_agent.py` | Stub |
| Evaluator | `src/apeg_core/evaluator/` | Complete |
| Monitoring | `src/apeg_core/monitoring/metrics.py` | Complete |
| HTTP Tools | `src/apeg_core/connectors/http_tools.py` | Complete |
| OpenAI Client | `src/apeg_core/connectors/openai_client.py` | Test mode |

---

## Appendix: ADR Summary

### ADR-001: OpenAI Agents SDK as Primary LLM Runtime
- **Decision:** Dual-backend with Agents SDK primary, API fallback
- **Status:** Accepted
- **Location:** `docs/ADRS/ADR-001-OpenAI-Agents.md`

### ADR-002: MCTS Disabled by Default
- **Decision:** MCTS implemented but inactive; bandit + scoring is primary
- **Status:** Accepted
- **Location:** `docs/ADRS/ADR-002-MCTS-Disabled-By-Default.md`

---

**Document Last Updated:** 2025-11-22
**Next Review:** After Sprint 1 completion
