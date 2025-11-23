# Phase 8 Kickoff - Production API Integration

**Status:** 🚀 READY TO BEGIN
**Date:** 2025-11-20

---

## Quick Summary

The APEG Hybrid Orchestrator is **fully functional in test mode** with all Phases 0-7 complete (132 tests passing). Phase 8 transforms it into a production-ready system by integrating real external APIs.

---

## What's Been Completed (Phases 0-7)

✅ **Infrastructure**
- Complete package structure (`src/apeg_core/`)
- Web API with FastAPI
- Web UI for interaction
- CI/CD pipeline
- Memory store (JSON-backed)
- Decision engine (bandit selector, loop guard)

✅ **Agent Framework**
- Base agent abstraction
- Shopify agent (9 stubbed methods)
- Etsy agent (9 stubbed methods)
- LLM roles (6 stubbed roles)
- HTTP client with retry logic

✅ **Quality Systems**
- Rule-based evaluator
- Hybrid scoring framework
- Logbook adapter
- Test suite (132 tests)

---

## What Needs to Be Done (Phase 8)

### Critical Path (High Priority)

#### 1. OpenAI Agents SDK Integration
**Goal:** Replace NotImplementedError stubs with real API calls

**Files:**
- `src/apeg_core/agents/llm_roles.py`

**Roles to Implement:**
- ENGINEER (prompt design)
- VALIDATOR (output validation)
- SCORER (quality scoring)
- CHALLENGER (adversarial testing)
- LOGGER (audit logging)
- TESTER (test generation)

**Requirements:**
- OpenAI API key
- Test mode fallback
- Error handling and retries

**Estimated Effort:** 3-4 days

---

#### 2. Shopify API Integration
**Goal:** Connect to Shopify Admin API for e-commerce operations

**Files:**
- `src/apeg_core/agents/shopify_agent.py`

**Capabilities:**
- Product management (list, get, update inventory)
- Order management (list, get, create, fulfill, cancel)
- Customer messaging

**Requirements:**
- Shopify store URL
- Admin API access token
- OAuth 2.0 setup

**Estimated Effort:** 2-3 days

---

#### 3. Etsy API Integration
**Goal:** Connect to Etsy API v3 for marketplace operations

**Files:**
- `src/apeg_core/agents/etsy_agent.py`

**Capabilities:**
- Listing management (list, create, update inventory)
- Order management (list, ship)
- Customer messaging
- SEO suggestions (uses ENGINEER LLM role)
- Shop analytics

**Requirements:**
- Etsy API key and secret
- Shop ID
- OAuth 2.0 with token refresh

**Estimated Effort:** 3-4 days

---

### Supporting Tasks (Medium Priority)

#### 4. Enhanced Scoring
**Goal:** Use LLM for quality assessment

**Changes:**
- Integrate SCORER role into evaluator
- Add grammar checking
- Weighted combination of rule-based + LLM scores

**Estimated Effort:** 1-2 days

---

#### 5. Configuration Management
**Goal:** Centralize environment setup

**Deliverables:**
- `.env.sample` with all variables
- Setup documentation
- Validation command

**Estimated Effort:** 1 day

---

#### 6. CI/CD Updates
**Goal:** Ensure pipeline supports new dependencies

**Changes:**
- Add secrets configuration
- Integration test job
- Coverage reporting

**Estimated Effort:** 1 day

---

#### 7. Deployment Documentation
**Goal:** Provide production deployment guides

**Deliverables:**
- Deployment guide (systemd, nginx)
- Raspberry Pi optimization guide
- Security hardening checklist

**Estimated Effort:** 1-2 days

---

## How to Get Started

### Step 1: Review Requirements
📖 Read `docs/APEG_PHASE_8_REQUIREMENTS.md` (comprehensive 600+ line spec)

This document contains:
- Detailed implementation steps for each task
- Code examples and patterns
- Testing requirements
- Environment variables
- API documentation links

---

### Step 2: Set Up Environment

**Install Dependencies:**
```bash
cd /home/user/PEG
pip install -e ".[dev]"
```

**Create .env File:**
```bash
cp .env.sample .env  # Will create .env.sample in Task 5
```

**Test Current State:**
```bash
# Verify all tests pass in test mode
APEG_TEST_MODE=true pytest tests/ -v

# Should show: 132 passed, 1 skipped
```

---

### Step 3: Obtain API Credentials

#### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Add to `.env`: `OPENAI_API_KEY=sk-proj-...`

#### Shopify (Choose one)
**Option A: Private App (Legacy)**
1. Shopify Admin > Apps > Manage private apps
2. Enable private app development
3. Create new app with scopes: read_products, write_products, read_orders, write_orders
4. Save API key and access token

**Option B: Custom App (Recommended)**
1. Shopify Partners > Apps > Create app
2. Configure OAuth scopes
3. Install on test store
4. Generate access token

Add to `.env`:
```
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
```

#### Etsy
1. Go to https://www.etsy.com/developers/
2. Create new app
3. Configure OAuth 2.0 scopes
4. Complete OAuth flow to get tokens

Add to `.env`:
```
ETSY_API_KEY=...
ETSY_API_SECRET=...
ETSY_SHOP_ID=...
ETSY_ACCESS_TOKEN=...
ETSY_REFRESH_TOKEN=...
```

---

### Step 4: Choose Your Starting Point

**Option A: Start with OpenAI (Recommended)**
- Easiest to implement
- No OAuth complexity
- Enables enhanced scoring
- See `docs/APEG_PHASE_8_REQUIREMENTS.md` Task 1

**Option B: Start with Shopify**
- More complex (OAuth)
- Good if you have Shopify store ready
- See `docs/APEG_PHASE_8_REQUIREMENTS.md` Task 2

**Option C: Start with Etsy**
- Most complex (OAuth + token refresh)
- Good if you have Etsy shop ready
- See `docs/APEG_PHASE_8_REQUIREMENTS.md` Task 3

---

## Implementation Workflow

### For Each Task:

1. **Read the spec** (Task section in APEG_PHASE_8_REQUIREMENTS.md)
2. **Create tests first** (TDD approach)
3. **Implement the code** (follow examples in spec)
4. **Test in test mode** (APEG_TEST_MODE=true)
5. **Test with real API** (APEG_TEST_MODE=false with credentials)
6. **Update documentation** (docstrings, README)
7. **Commit and push**

---

## Testing Checklist

For each completed task:

- [ ] Unit tests added (minimum 5 per component)
- [ ] Integration tests added (using responses or httpx mocking)
- [ ] Test mode works (no API calls made)
- [ ] Production mode works (real API calls with credentials)
- [ ] Error handling tested (API errors, timeouts, rate limits)
- [ ] All existing tests still pass
- [ ] Coverage maintained above 80%

---

## API Key Setup - Quick Reference

**I need you to provide API keys for:**

### OpenAI
**Required for:** LLM roles (ENGINEER, VALIDATOR, SCORER, etc.)
**How to provide:**
```bash
export OPENAI_API_KEY="sk-proj-YOUR-KEY-HERE"
```

Or add to `.env` file (I will create `.env.sample` template)

**Testing without key:**
Set `APEG_TEST_MODE=true` to use mock responses.

---

### Shopify (Optional for now)
**Required for:** Shopify agent real operations
**How to provide:**
```bash
export SHOPIFY_SHOP_URL="your-store.myshopify.com"
export SHOPIFY_ACCESS_TOKEN="shpat-YOUR-TOKEN-HERE"
```

**Testing without credentials:**
Shopify agent works in test mode with mock data.

---

### Etsy (Optional for now)
**Required for:** Etsy agent real operations
**How to provide:**
```bash
export ETSY_API_KEY="YOUR-KEY"
export ETSY_SHOP_ID="12345678"
export ETSY_ACCESS_TOKEN="YOUR-TOKEN"
```

**Testing without credentials:**
Etsy agent works in test mode with mock data.

---

## Timeline

### Recommended Sequence

**Week 1: Core LLM Integration**
- Day 1-2: Implement OpenAI client and ENGINEER role
- Day 3-4: Implement remaining LLM roles (VALIDATOR, SCORER, etc.)
- Day 5: Add tests and integrate enhanced scoring

**Week 2: E-commerce Integrations**
- Day 1-2: Shopify agent implementation
- Day 3-4: Etsy agent implementation
- Day 5: Integration tests and bug fixes

**Week 3: Polish and Deploy**
- Day 1-2: Configuration management and .env.sample
- Day 3: CI/CD updates
- Day 4-5: Deployment docs and final testing

---

## Success Metrics

### Definition of Done for Phase 8

✅ **Functional:**
- All LLM roles execute real OpenAI calls
- Shopify agent performs 9 operations via Admin API
- Etsy agent performs 9 operations via API v3
- Enhanced scoring uses LLM + rules
- Test mode still works (backward compatible)

✅ **Quality:**
- 85%+ test coverage for new code
- All CI tests pass
- No breaking changes
- Code linted and type-hinted

✅ **Documentation:**
- .env.sample created
- API setup guides written
- Deployment guide complete
- APEG_STATUS.md updated

---

## Current Repository State

**Branch:** `claude/add-agent-stubs-01BPWKQpf5tk6UASEDH4dmra`
**Last Commit:** d1a55e7 (Phases 5-7 complete)
**Test Status:** ✅ 132 passing, 1 skipped

**Key Files:**
```
src/apeg_core/
├── agents/
│   ├── llm_roles.py         # ← START HERE (Task 1)
│   ├── shopify_agent.py     # ← Task 2
│   ├── etsy_agent.py        # ← Task 3
│   └── base_agent.py
├── scoring/
│   └── evaluator.py         # ← Task 4 (enhance)
├── connectors/
│   ├── openai_client.py     # ← Used by Task 1
│   └── http_tools.py        # ← Used by Tasks 2-3
└── web/
    ├── api.py
    └── server.py

docs/
├── APEG_PHASE_8_REQUIREMENTS.md  # ← MAIN SPEC (READ FIRST)
├── APEG_STATUS.md                # ← Update as tasks complete
└── APEG_HYBRID_ORCHESTRATOR_BUILD.md

.env.sample                       # ← CREATE in Task 5
pyproject.toml                    # ← Update dependencies
requirements.txt                  # ← Update dependencies
```

---

## Getting Help

**Documentation:**
- `docs/APEG_PHASE_8_REQUIREMENTS.md` - Full implementation spec
- `CLAUDE.md` - Project conventions and guidelines
- `docs/APEG_STATUS.md` - Current implementation status

**Testing:**
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_llm_roles.py -v

# Run with coverage
pytest --cov=src/apeg_core tests/
```

**Debugging:**
```bash
# Enable debug mode
APEG_DEBUG=true python -m apeg_core

# Test mode (no API calls)
APEG_TEST_MODE=true python -m apeg_core serve
```

---

## Next Steps

### Immediate Actions:

1. **Read** `docs/APEG_PHASE_8_REQUIREMENTS.md` in full
2. **Choose** starting task (recommend Task 1: OpenAI)
3. **Request** API key if implementing Task 1 (I will wait for you to provide)
4. **Begin** implementation following TDD approach

### When You're Ready to Start:

**For OpenAI Integration:**
Say: "I'm ready to start Task 1. Here's my OpenAI API key: sk-proj-..."

**For Shopify Integration:**
Say: "I'm ready to start Task 2. Here are my Shopify credentials: ..."

**For Etsy Integration:**
Say: "I'm ready to start Task 3. Here are my Etsy credentials: ..."

**To Start Without API Keys:**
Say: "Let's start with test mode implementation and add real API calls later"

---

## Questions?

Ask me about:
- Specific implementation details
- Testing strategies
- API authentication flows
- Deployment options
- Timeline adjustments

---

**Phase 8 Status:** 📋 PLANNED - Ready to begin implementation
**Next Milestone:** Task 1 (OpenAI Integration) - 3-4 days

**Let me know when you're ready to start!** 🚀
