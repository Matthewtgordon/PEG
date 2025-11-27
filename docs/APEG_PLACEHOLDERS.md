# APEG Placeholder Tracking Register

**Last Updated:** 2025-11-20
**Total Placeholders:** 1
**Status:** All placeholders documented and tracked

## Summary
All current placeholders are intentional stubs for Phase 8 (Production API integration).
Test mode implementations are fully functional for development and testing.

---

## Active Placeholders

### APEG-CONN-001: OpenAI API Real Calls
**Location:** src/apeg_core/connectors/openai_client.py:136-195
**Type:** External API Stub
**Reason:** Real OpenAI calls require API key and incur costs
**Test Mode:** Returns canned response based on input messages
**Resolution Plan:** Phase 8 (Production API integration)
**Impact:** Development and testing can proceed with mock responses

**Test Mode Behavior:**
```python
# Test mode automatically enabled when:
# - APEG_TEST_MODE environment variable is set to "true"
# - OPENAI_API_KEY is not set
# - openai package is not installed

# Returns mock response:
{
    "content": "This is a test mode response. In production, this would be a real OpenAI completion...",
    "role": "assistant",
    "model": "test-mode",
    "finish_reason": "stop",
    "usage": None
}
```

---

## Resolved Placeholders

### APEG-PH-2: Decision Engine Integration
**Status:** ✅ RESOLVED in Phase 3
**Location:** Previously in orchestrator.py
**Resolution:** Bandit selector and loop guard integrated into build and loop_detector nodes

### APEG-PH-3: Scoring System Integration
**Status:** ✅ RESOLVED in Phase 6
**Location:** Previously in orchestrator.py
**Resolution:** Evaluator integrated into review node (src/apeg_core/orchestrator.py:465-513)
**Implementation**: `Evaluator.evaluate()` returns `EvalResult` with score, metrics, and feedback

### APEG-PH-4: Agent Calling Integration
**Status:** ✅ RESOLVED in Phase 4
**Location:** Previously in orchestrator.py:163
**Resolution:** `_call_agent()` method added and integrated into build node (orchestrator.py:327-409)

---

## Future Placeholders (Planned)

These will be added as Phases 5-6 progress:

### APEG-AGENT-001: Shopify API Real Implementation (Phase 5)
**Planned Location:** src/apeg_core/agents/shopify_agent.py
**Type:** Domain Agent Stub
**Reason:** Requires Shopify API key, shop URL, and OAuth setup

### APEG-AGENT-002: Etsy API Real Implementation (Phase 8)
**Planned Location:** src/apeg_core/agents/etsy_agent.py
**Type:** Domain Agent Stub
**Reason:** Requires Etsy OAuth 2.0 token and shop ID
**Status**: Test mode implementation exists

---

## Placeholder Conventions

**ID Format:** `APEG-<CATEGORY>-<NUMBER>`

**Categories:**
- **CONN**: Connector/external API stubs
- **AGENT**: Domain agent stubs
- **EVAL**: Evaluator/scoring stubs
- **LOG**: Logging system stubs
- **PH**: General phase integration placeholders

**Required Fields:**
- **Location:** File path and line numbers
- **Type:** Category (API stub, integration placeholder, etc.)
- **Reason:** Why placeholder exists
- **Test Mode:** Behavior in test/development mode
- **Resolution Plan:** When/how it will be resolved
- **Impact:** Effect on development/testing

---

## Tracking Process

1. **Creation:** When adding a placeholder, document it here immediately
2. **Updates:** Update line numbers if code changes significantly
3. **Resolution:** Move to "Resolved" section when implemented
4. **Review:** Check all placeholders at end of each phase

---

**Document Version:** 1.0.0
**Maintainer:** APEG Development Team
