# APEG Phase 8: Production API Integration - Requirements & Expectations

**Document Version:** 1.0.0
**Created:** 2025-11-20
**Status:** PLANNING
**Prerequisites:** Phases 0-7 Complete (✅ All 132 tests passing)

---

## Executive Summary

Phase 8 focuses on transforming the APEG Hybrid Orchestrator from a fully functional test-mode system into a production-ready AI agent platform by integrating real external APIs. This phase implements:

1. **OpenAI Agents SDK** integration for LLM-powered agent roles
2. **Shopify Admin API** integration for e-commerce operations
3. **Etsy API v3** integration for marketplace operations
4. **Enhanced scoring** with LLM-based quality assessment
5. **Production deployment** configurations and security hardening

**Timeline Estimate:** 2-3 weeks for core integrations, 1 week for testing and hardening

**Risk Level:** Medium (external API dependencies, authentication complexity)

---

## Current State Verification

### ✅ Phase 0-7 Completion Audit

**Package Structure:**
```
src/apeg_core/
├── agents/
│   ├── llm_roles.py          # 6 LLM role stubs (NotImplementedError)
│   ├── shopify_agent.py      # 9 stubbed capabilities (test mode only)
│   ├── etsy_agent.py         # 9 stubbed capabilities (test mode only)
│   └── base_agent.py         # Abstract base class
├── connectors/
│   ├── openai_client.py      # Test mode wrapper (APEG-CONN-001)
│   └── http_tools.py         # HTTP client with retry logic
├── scoring/
│   └── evaluator.py          # Rule-based + hybrid scoring
├── memory/
│   └── memory_store.py       # JSON-backed persistence
└── web/
    ├── api.py                # FastAPI endpoints
    └── server.py             # Uvicorn launcher
```

**Test Coverage:**
- 132 tests passing (1 skipped)
- Full coverage of decision engine, agents, connectors, scoring, memory
- Integration tests for orchestrator and workflow execution

**TODO Markers Identified:**
- `TODO[APEG-PH-4]`: OpenAI Agents SDK integration (6 LLM roles)
- `TODO[APEG-PH-5]`: Shopify API implementation (9 methods)
- `TODO[APEG-PH-5]`: Etsy API implementation (9 methods)
- `TODO[APEG-PH-6]`: Enhanced scoring with LLM integration
- `TODO[APEG-AGENT-001]`: Shopify API real calls
- `TODO[APEG-AGENT-002]`: Etsy API real calls
- `TODO[APEG-CONN-001]`: OpenAI API real calls

---

## Phase 8 Objectives

### Primary Goals
1. Replace all `NotImplementedError` stubs with functional API integrations
2. Maintain backward compatibility with test mode for CI/CD
3. Implement secure credential management
4. Achieve 80%+ test coverage for new integrations
5. Document deployment procedures for production environments

### Success Criteria
- [ ] All LLM roles execute real OpenAI API calls when `APEG_TEST_MODE=false`
- [ ] Shopify agent performs live API operations with proper OAuth
- [ ] Etsy agent performs live API operations with OAuth 2.0
- [ ] Enhanced scoring uses LLM for quality assessment
- [ ] All existing tests pass with test mode enabled
- [ ] New integration tests added (minimum 30 new tests)
- [ ] CI/CD pipeline updated with secret management
- [ ] Production deployment guide completed
- [ ] .env.sample file created with all required variables

---

## Task Breakdown

### Task 1: OpenAI Agents SDK Integration (HIGH PRIORITY)

**Objective:** Implement real LLM role adapters for ENGINEER, VALIDATOR, SCORER, CHALLENGER, LOGGER, and TESTER roles.

**Files to Modify:**
- `src/apeg_core/agents/llm_roles.py` (327 lines)
- `pyproject.toml` (add dependencies)
- `requirements.txt` (add dependencies)
- `docs/APEG_STATUS.md` (update completion status)

**Dependencies to Add:**
```toml
# In pyproject.toml dependencies section:
"openai>=1.0.0",           # Already present
```

**Implementation Steps:**

#### 1.1 Update `_get_openai_client()` (lines 35-62)
**Current State:**
```python
def _get_openai_client() -> Any:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMRoleError(...)
    # TODO[APEG-PH-4]: Replace with actual OpenAI client initialization
    return None  # Placeholder
```

**Expected Implementation:**
```python
def _get_openai_client() -> Any:
    """Get OpenAI client for API calls."""
    # Check test mode first
    test_mode = os.environ.get("APEG_TEST_MODE", "false").lower() == "true"
    if test_mode:
        logger.info("Test mode enabled - using mock client")
        return None  # Will trigger test mode in role functions

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMRoleError(
            "OPENAI_API_KEY environment variable not set. "
            "Please set it to use LLM roles, or enable APEG_TEST_MODE=true."
        )

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
        return client
    except ImportError:
        raise LLMRoleError(
            "openai package not installed. Install with: pip install openai"
        )
```

#### 1.2 Implement `run_engineer_role()` (lines 64-108)
**Requirements:**
- Accept `prompt`, `context`, and `**kwargs`
- Build system prompt from `Knowledge.json` and role description
- Call OpenAI Chat Completions API
- Parse and return response content
- Handle errors gracefully with retries

**Expected Implementation:**
```python
def run_engineer_role(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> str:
    """Execute ENGINEER role using OpenAI API."""
    logger.info("ENGINEER role called with prompt: %s", prompt[:100])

    client = _get_openai_client()

    # Test mode fallback
    if client is None:
        return "ENGINEER test mode: This is a stubbed response for prompt engineering."

    # Build system prompt
    system_prompt = """You are an expert prompt engineer. Your role is to:
- Design macro chains and workflows
- Construct prompts with proper structure
- Inject constraints and requirements
- Build solutions from specifications

Be concise, structured, and follow best practices from Knowledge.json."""

    # Add context if provided
    if context:
        system_prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

    try:
        response = client.chat.completions.create(
            model=kwargs.get("model", "gpt-4"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2048),
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("ENGINEER role failed: %s", e)
        raise LLMRoleError(f"ENGINEER role execution failed: {e}")
```

#### 1.3 Implement Remaining Roles
Apply similar pattern to:
- `run_validator_role()` (lines 111-154)
- `run_scorer_role()` (lines 157-203)
- `run_challenger_role()` (lines 206-239)
- `run_logger_role()` (lines 242-276) - May use structured logging instead
- `run_tester_role()` (lines 279-314)

**Role-Specific System Prompts:**

**VALIDATOR:**
```
You are a validation expert. Review outputs against requirements.
Return JSON: {"valid": bool, "score": float, "issues": [], "recommendations": []}
```

**SCORER:**
```
You are a quality scorer. Evaluate outputs using PromptScoreModel metrics.
Return JSON: {"overall_score": float, "metrics": {}, "feedback": str}
```

**CHALLENGER:**
```
You are an adversarial tester. Identify flaws, edge cases, and weaknesses.
Return JSON: {"critical_issues": [], "warnings": [], "stress_test_results": {}}
```

**LOGGER:**
```
You are an audit logger. Summarize events for compliance tracking.
Return structured log entry.
```

**TESTER:**
```
You are a test engineer. Generate regression and edge case tests.
Return test cases in executable format.
```

#### 1.4 Add Test Mode Support
**Requirements:**
- When `APEG_TEST_MODE=true`, return canned responses
- When `OPENAI_API_KEY` is not set, fall back to test mode
- Log test mode activation for debugging

#### 1.5 Testing Requirements
**New Test File:** `tests/test_llm_roles.py`

**Test Cases:**
1. `test_openai_client_initialization()` - Test client setup
2. `test_openai_client_missing_key()` - Error handling
3. `test_engineer_role_real_mode()` - Mock OpenAI response
4. `test_engineer_role_test_mode()` - Test mode fallback
5. `test_validator_role_json_response()` - JSON parsing
6. `test_scorer_role_metrics()` - Scoring output
7. `test_all_roles_test_mode()` - Verify all roles work in test mode
8. `test_error_handling()` - API errors, retries, timeouts

**Mocking Strategy:**
```python
from unittest.mock import patch, MagicMock

@patch('openai.OpenAI')
def test_engineer_role_real_mode(mock_openai):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client

    result = run_engineer_role("Test prompt")
    assert "Test response" in result
```

#### 1.6 Environment Variables
**Add to `.env.sample`:**
```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-...
APEG_TEST_MODE=false  # Set to 'true' to disable real API calls
OPENAI_DEFAULT_MODEL=gpt-4  # or gpt-4-turbo, gpt-3.5-turbo
```

#### 1.7 Documentation Updates
**Update `docs/APEG_STATUS.md`:**
```markdown
## Phase 8: Production API Integration - 🔄 IN PROGRESS

### Task 1: OpenAI Agents SDK Integration - ✅ COMPLETE
- [x] Implement _get_openai_client() with error handling
- [x] Implement run_engineer_role() with real API calls
- [x] Implement run_validator_role() with JSON parsing
- [x] Implement run_scorer_role() with metrics
- [x] Implement run_challenger_role() with adversarial testing
- [x] Implement run_logger_role() with structured logging
- [x] Implement run_tester_role() with test generation
- [x] Add test mode fallback for all roles
- [x] Create tests/test_llm_roles.py (8+ tests)
- [x] Update .env.sample with OPENAI_API_KEY
- [x] Document API key setup in README.md
```

**Update `CLAUDE.md`:**
Add section on LLM role usage:
```markdown
### Using LLM Roles

The APEG orchestrator uses six specialized LLM roles:

1. **ENGINEER**: Designs prompts and workflows
2. **VALIDATOR**: Validates outputs against requirements
3. **SCORER**: Evaluates quality and assigns scores
4. **CHALLENGER**: Stress-tests logic for flaws
5. **LOGGER**: Audits operations for compliance
6. **TESTER**: Generates and runs tests

**Usage Example:**
```python
from apeg_core.agents.llm_roles import run_engineer_role

result = run_engineer_role(
    prompt="Design a product description prompt",
    context={"product_type": "handmade jewelry"},
    temperature=0.7
)
```

**Test Mode:**
Set `APEG_TEST_MODE=true` to use mock responses without API calls.
```

---

### Task 2: Shopify API Integration (HIGH PRIORITY)

**Objective:** Replace stub methods in ShopifyAgent with real Shopify Admin API calls.

**Files to Modify:**
- `src/apeg_core/agents/shopify_agent.py` (382 lines)
- `pyproject.toml` (add shopify dependencies)
- `requirements.txt`
- `.env.sample`

**Dependencies to Add:**
```toml
# Option 1: Official Shopify Python SDK
"shopifyapi>=12.0.0",

# Option 2: Direct REST API (recommended for flexibility)
"requests>=2.31.0",  # Already present
"requests-oauthlib>=1.3.0",
```

**Recommendation:** Use direct REST API via `requests` for better control and error handling.

**Shopify API Overview:**
- **API Version:** Admin API 2024-01
- **Authentication:** OAuth 2.0 or private app credentials
- **Base URL:** `https://{shop_url}/admin/api/2024-01/`
- **Rate Limits:** 2 requests/second (REST), 50 points/second (GraphQL)

**Implementation Steps:**

#### 2.1 Add OAuth 2.0 Authentication
**New Method:** `_authenticate()` in `ShopifyAgent.__init__()`

```python
def __init__(self, config: Dict[str, Any], test_mode: bool = True):
    super().__init__(config, test_mode)
    self.shop_url = config.get("shop_url")
    self.api_key = config.get("api_key")
    self.api_secret = config.get("api_secret")
    self.access_token = config.get("access_token")

    if not test_mode:
        if not all([self.shop_url, self.access_token]):
            raise ValueError(
                "Shopify agent requires 'shop_url' and 'access_token' "
                "in config for production mode"
            )
        self.base_url = f"https://{self.shop_url}/admin/api/2024-01/"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }
```

#### 2.2 Implement `list_products()` (lines 97-122)
**Current State:**
```python
def list_products(self, status_filter: str | None = None, limit: int = 50) -> List[Dict]:
    """List products from Shopify store."""
    logger.info(f"Listing products (filter={status_filter}, limit={limit})")

    # TODO[APEG-PH-5]: Replace with real Shopify API call
    return [
        {
            "id": "mock-product-123",
            "title": "Test Product",
            ...
        }
    ]
```

**Expected Implementation:**
```python
def list_products(
    self,
    status_filter: str | None = None,
    limit: int = 50
) -> List[Dict]:
    """List products from Shopify store."""
    if self.test_mode:
        # Return mock data for testing
        return [
            {
                "id": "mock-product-123",
                "title": "Test Product",
                "status": "active",
                "inventory_quantity": 10,
            }
        ]

    # Real API call
    params = {"limit": min(limit, 250)}
    if status_filter:
        params["status"] = status_filter

    try:
        response = requests.get(
            f"{self.base_url}products.json",
            headers=self.headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("products", [])
    except requests.RequestException as e:
        logger.error(f"Shopify API error: {e}")
        raise RuntimeError(f"Failed to list products: {e}")
```

#### 2.3 Implement Remaining Methods
Apply similar pattern to:
- `get_product(product_id)` - GET `/products/{id}.json`
- `update_inventory(product_id, new_quantity)` - POST `/inventory_levels/set.json`
- `list_orders()` - GET `/orders.json`
- `get_order(order_id)` - GET `/orders/{id}.json`
- `create_order_from_etsy(etsy_order)` - POST `/orders.json`
- `send_customer_message(order_id, message)` - POST `/orders/{id}/events.json`
- `fulfill_order(order_id)` - POST `/orders/{id}/fulfillments.json`
- `cancel_order(order_id, reason)` - POST `/orders/{id}/cancel.json`

#### 2.4 Add Rate Limiting
**Use HTTPClient from `connectors/http_tools.py`:**
```python
from apeg_core.connectors.http_tools import HTTPClient

class ShopifyAgent(BaseAgent):
    def __init__(self, config, test_mode=True):
        super().__init__(config, test_mode)
        self.http_client = HTTPClient(
            max_retries=3,
            retry_delay=1.0,
            timeout=10.0,
        )
```

#### 2.5 Testing Requirements
**New Test File:** `tests/test_shopify_agent_integration.py`

**Test Cases:**
1. `test_shopify_authentication()` - OAuth setup
2. `test_list_products_real_mode()` - Mock API response
3. `test_list_products_test_mode()` - Test mode fallback
4. `test_update_inventory()` - Inventory update
5. `test_rate_limiting()` - Verify rate limit handling
6. `test_error_handling()` - API errors, retries
7. `test_all_methods_test_mode()` - All 9 methods work in test mode

**Mocking Strategy:**
```python
import responses

@responses.activate
def test_list_products_real_mode():
    responses.add(
        responses.GET,
        "https://test-shop.myshopify.com/admin/api/2024-01/products.json",
        json={"products": [{"id": 123, "title": "Test"}]},
        status=200,
    )

    agent = ShopifyAgent(
        config={
            "shop_url": "test-shop.myshopify.com",
            "access_token": "test-token",
        },
        test_mode=False,
    )
    products = agent.list_products()
    assert len(products) == 1
    assert products[0]["title"] == "Test"
```

#### 2.6 Environment Variables
**Add to `.env.sample`:**
```bash
# Shopify API Configuration
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_API_KEY=your-api-key
SHOPIFY_API_SECRET=your-api-secret
SHOPIFY_ACCESS_TOKEN=shpat_...
```

#### 2.7 Documentation
**Create `docs/SHOPIFY_SETUP.md`:**
```markdown
# Shopify API Setup Guide

## 1. Create Private App (Legacy)
1. Go to Shopify Admin > Apps > Manage private apps
2. Enable private app development
3. Create new private app
4. Grant permissions: read_products, write_products, read_orders, write_orders
5. Save API credentials

## 2. Generate Access Token (Recommended)
1. Go to Shopify Partners dashboard
2. Create new app
3. Configure OAuth scopes
4. Install app on test store
5. Exchange authorization code for access token

## 3. Configure APEG
Add to `.env`:
```bash
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
```

## 4. Test Connection
```python
from apeg_core.agents import ShopifyAgent

agent = ShopifyAgent(config={
    "shop_url": os.environ["SHOPIFY_SHOP_URL"],
    "access_token": os.environ["SHOPIFY_ACCESS_TOKEN"],
}, test_mode=False)

products = agent.list_products(limit=5)
print(f"Found {len(products)} products")
```
```

---

### Task 3: Etsy API Integration (HIGH PRIORITY)

**Objective:** Replace stub methods in EtsyAgent with real Etsy API v3 calls.

**Files to Modify:**
- `src/apeg_core/agents/etsy_agent.py` (425 lines)
- `pyproject.toml`
- `requirements.txt`
- `.env.sample`

**Dependencies to Add:**
```toml
"requests-oauthlib>=1.3.0",
```

**Etsy API Overview:**
- **API Version:** v3 (REST)
- **Authentication:** OAuth 2.0 with PKCE
- **Base URL:** `https://openapi.etsy.com/v3/`
- **Rate Limits:** 10 requests/second, 10,000 requests/day

**Implementation Steps:**

#### 3.1 Implement OAuth 2.0 with Token Refresh
**New Methods:**
```python
def _refresh_token(self) -> str:
    """Refresh OAuth 2.0 access token."""
    if self.test_mode:
        return "test-token"

    from requests_oauthlib import OAuth2Session

    token_url = "https://api.etsy.com/v3/public/oauth/token"
    client_id = self.config.get("api_key")
    refresh_token = self.config.get("refresh_token")

    extra = {
        "client_id": client_id,
        "client_secret": self.config.get("api_secret"),
    }

    oauth = OAuth2Session(client_id, token={"refresh_token": refresh_token})
    new_token = oauth.refresh_token(token_url, **extra)

    # Save new tokens
    self.config["access_token"] = new_token["access_token"]
    self.config["refresh_token"] = new_token.get("refresh_token", refresh_token)

    return new_token["access_token"]
```

#### 3.2 Implement API Methods
Similar to Shopify, implement all 9 methods:
- `list_listings()` - GET `/application/shops/{shop_id}/listings/active`
- `create_listing(data)` - POST `/application/shops/{shop_id}/listings`
- `update_listing(listing_id, updates)` - PATCH `/application/listings/{listing_id}`
- `update_inventory(listing_id, quantity)` - PUT `/application/listings/{listing_id}/inventory`
- `list_orders()` - GET `/application/shops/{shop_id}/receipts`
- `ship_order(order_id, tracking)` - POST `/application/shops/{shop_id}/receipts/{order_id}/tracking`
- `send_customer_message(order_id, message)` - POST `/application/shops/{shop_id}/conversations/{conversation_id}/messages`
- `suggest_listing_seo(listing)` - Uses ENGINEER LLM role
- `get_shop_stats()` - GET `/application/shops/{shop_id}/stats`

#### 3.3 Integrate ENGINEER Role for SEO
**Special Implementation for `suggest_listing_seo()`:**
```python
def suggest_listing_seo(self, listing: Dict) -> Dict:
    """Generate SEO suggestions using ENGINEER LLM role."""
    if self.test_mode:
        return {
            "title_suggestions": ["Handmade Silver Ring"],
            "tag_suggestions": ["handmade", "silver", "ring"],
            "description_improvements": ["Add material details"],
        }

    from apeg_core.agents.llm_roles import run_engineer_role

    prompt = f"""Analyze this Etsy listing and suggest SEO improvements:

Title: {listing.get('title')}
Description: {listing.get('description', '')[:500]}
Tags: {listing.get('tags', [])}

Provide:
1. Improved title (max 140 chars)
2. Additional tags (max 13 total)
3. Description improvements

Return as JSON.
"""

    try:
        result = run_engineer_role(prompt, context={"listing": listing})
        return json.loads(result)
    except Exception as e:
        logger.error(f"SEO suggestion failed: {e}")
        return {"error": str(e)}
```

#### 3.4 Testing Requirements
**New Test File:** `tests/test_etsy_agent_integration.py`

Similar test structure to Shopify, with focus on OAuth token refresh.

#### 3.5 Environment Variables
**Add to `.env.sample`:**
```bash
# Etsy API Configuration
ETSY_API_KEY=your-api-key
ETSY_API_SECRET=your-api-secret
ETSY_SHOP_ID=12345678
ETSY_ACCESS_TOKEN=...
ETSY_REFRESH_TOKEN=...
```

---

### Task 4: Enhanced Scoring with LLM (MEDIUM PRIORITY)

**Objective:** Use SCORER LLM role for nuanced quality assessment.

**Files to Modify:**
- `src/apeg_core/scoring/evaluator.py` (444 lines)
- `PromptScoreModel.json`
- `tests/test_evaluator.py`

**Implementation Steps:**

#### 4.1 Enhance `hybrid_score()` Method (lines 247-304)
**Current State:**
```python
def hybrid_score(self, output: str, context: Dict) -> EvaluationResult:
    """Combine rule-based and LLM scoring."""
    # TODO[APEG-PH-6]: Add LLM scoring integration here
    rule_score = self.rule_based_score(output, context)
    return rule_score
```

**Expected Implementation:**
```python
def hybrid_score(self, output: str, context: Dict) -> EvaluationResult:
    """Combine rule-based and LLM scoring."""
    # Get rule-based score
    rule_result = self.rule_based_score(output, context)

    # Check if test mode or LLM scoring disabled
    test_mode = os.environ.get("APEG_TEST_MODE", "false").lower() == "true"
    use_llm = self.config.get("use_llm_scoring", True)

    if test_mode or not use_llm:
        return rule_result

    # Use SCORER LLM role
    try:
        from apeg_core.agents.llm_roles import run_scorer_role

        llm_response = run_scorer_role(
            prompt="Evaluate this output using PromptScoreModel metrics",
            output_to_score=output,
            scoring_model=self.scoring_model,
        )
        llm_data = json.loads(llm_response)
        llm_score = llm_data.get("overall_score", 0.0)

        # Weighted combination: 60% rule-based, 40% LLM
        rule_weight = self.config.get("rule_weight", 0.6)
        llm_weight = 1.0 - rule_weight

        combined_score = (rule_result.score * rule_weight) + (llm_score * llm_weight)

        return EvaluationResult(
            score=combined_score,
            passed=combined_score >= self.threshold,
            metrics={
                "rule_based": rule_result.metrics,
                "llm_based": llm_data.get("metrics", {}),
            },
            feedback=f"Rule-based: {rule_result.feedback}\n\nLLM: {llm_data.get('feedback', '')}",
        )
    except Exception as e:
        logger.warning(f"LLM scoring failed, using rule-based only: {e}")
        return rule_result
```

#### 4.2 Add Grammar and Coherence Checks
**New Dependency:**
```toml
"language-tool-python>=2.7.0",
```

**New Methods:**
```python
def _check_grammar(self, text: str) -> float:
    """Check grammar using LanguageTool."""
    try:
        import language_tool_python
        tool = language_tool_python.LanguageTool('en-US')
        matches = tool.check(text)
        # Score based on error density
        error_rate = len(matches) / max(len(text.split()), 1)
        return max(0.0, 1.0 - error_rate)
    except Exception as e:
        logger.warning(f"Grammar check failed: {e}")
        return 0.8  # Default score if check fails
```

#### 4.3 Update PromptScoreModel.json
**Add new metrics:**
```json
{
  "metrics": [
    {
      "name": "grammar",
      "weight": 0.1,
      "description": "Grammar and spelling correctness"
    },
    {
      "name": "coherence",
      "weight": 0.1,
      "description": "Logical flow and coherence"
    },
    {
      "name": "semantic_relevance",
      "weight": 0.15,
      "description": "Relevance to task requirements"
    }
  ],
  "llm_scoring": {
    "enabled": true,
    "rule_weight": 0.6,
    "llm_weight": 0.4
  }
}
```

**Ensure weights sum to 1.0.**

---

### Task 5: Configuration and Environment Management (MEDIUM PRIORITY)

**Objective:** Centralize configuration and provide clear setup instructions.

**Files to Create/Modify:**
- `.env.sample` (create)
- `docs/APEG_ENVIRONMENT_SETUP.md` (create)
- `src/apeg_core/cli.py` (enhance)

**Implementation Steps:**

#### 5.1 Create `.env.sample`
```bash
# =============================================================================
# APEG Environment Configuration Template
# =============================================================================
# Copy this file to .env and fill in your actual values
# Never commit .env to version control!

# -----------------------------------------------------------------------------
# Core Settings
# -----------------------------------------------------------------------------
APEG_TEST_MODE=false  # Set to 'true' to disable all real API calls
APEG_CONFIG_DIR=.     # Directory containing JSON config files
APEG_DEBUG=false      # Enable debug logging

# -----------------------------------------------------------------------------
# OpenAI API
# -----------------------------------------------------------------------------
OPENAI_API_KEY=sk-proj-...
OPENAI_DEFAULT_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2048

# -----------------------------------------------------------------------------
# Gemini API (Optional)
# -----------------------------------------------------------------------------
GEMINI_API_KEY=AI...
GOOGLE_API_KEY=AI...  # Alternative name

# -----------------------------------------------------------------------------
# Shopify API
# -----------------------------------------------------------------------------
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_API_KEY=your-api-key
SHOPIFY_API_SECRET=your-api-secret
SHOPIFY_ACCESS_TOKEN=shpat_...

# -----------------------------------------------------------------------------
# Etsy API
# -----------------------------------------------------------------------------
ETSY_API_KEY=your-api-key
ETSY_API_SECRET=your-api-secret
ETSY_SHOP_ID=12345678
ETSY_ACCESS_TOKEN=...
ETSY_REFRESH_TOKEN=...

# -----------------------------------------------------------------------------
# GitHub Integration
# -----------------------------------------------------------------------------
GITHUB_PAT=ghp_...
GITHUB_REPO=Matthewtgordon/PEG

# -----------------------------------------------------------------------------
# Web Server Settings
# -----------------------------------------------------------------------------
APEG_HOST=0.0.0.0
APEG_PORT=8000
APEG_RELOAD=false  # Auto-reload for development

# -----------------------------------------------------------------------------
# Scoring Configuration
# -----------------------------------------------------------------------------
APEG_USE_LLM_SCORING=true
APEG_RULE_WEIGHT=0.6
APEG_LLM_WEIGHT=0.4
APEG_SCORE_THRESHOLD=0.7
```

#### 5.2 Create Setup Documentation
**File:** `docs/APEG_ENVIRONMENT_SETUP.md`

**Sections:**
1. Prerequisites (Python 3.11+, API accounts)
2. Installation Steps
3. API Key Acquisition (step-by-step for each service)
4. Configuration Validation
5. Troubleshooting Common Issues

#### 5.3 Add Validation Command
**Enhance `src/apeg_core/cli.py`:**
```python
def validate_environment():
    """Validate environment configuration."""
    required_vars = {
        "production": [
            "OPENAI_API_KEY",
            "SHOPIFY_SHOP_URL",
            "SHOPIFY_ACCESS_TOKEN",
            "ETSY_API_KEY",
            "ETSY_SHOP_ID",
        ],
        "development": [
            "OPENAI_API_KEY",
        ],
    }

    test_mode = os.environ.get("APEG_TEST_MODE", "false").lower() == "true"
    mode = "development" if test_mode else "production"

    print(f"Validating environment for {mode} mode...")

    missing = []
    for var in required_vars[mode]:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nSee .env.sample for required variables")
        return False

    print("✅ All required environment variables are set")
    return True

# Add to CLI:
parser.add_argument(
    "command",
    nargs="?",
    choices=["serve", "validate", "version"],
    default=None,
    help="Command to run",
)

if args.command == "validate":
    sys.exit(0 if validate_environment() else 1)
```

**Usage:**
```bash
python -m apeg_core validate
```

---

### Task 6: CI and Test Pipeline Updates (LOW PRIORITY)

**Objective:** Ensure CI reflects new dependencies and integration tests.

**Files to Modify:**
- `.github/workflows/apeg-ci.yml`
- `pyproject.toml`
- `requirements.txt`

**Implementation Steps:**

#### 6.1 Update CI Workflow
**Add secrets configuration:**
```yaml
env:
  APEG_TEST_MODE: 'true'
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  SHOPIFY_ACCESS_TOKEN: ${{ secrets.SHOPIFY_ACCESS_TOKEN }}
  ETSY_ACCESS_TOKEN: ${{ secrets.ETSY_ACCESS_TOKEN }}
```

**Add integration test job:**
```yaml
  integration-tests:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install responses
      - name: Run integration tests
        env:
          APEG_TEST_MODE: 'false'
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/test_*_integration.py -v
```

#### 6.2 Update Dependencies
**Consolidate `requirements.txt` and `pyproject.toml`:**
```toml
dependencies = [
    "openai>=1.0.0",
    "requests>=2.31.0",
    "requests-oauthlib>=1.3.0",
    "jsonschema>=4.23.0",
    "python-dotenv>=1.0.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0.0",
    "language-tool-python>=2.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "responses>=0.24.0",
    "httpx>=0.25.0",
]
```

#### 6.3 Add Coverage Reporting
```yaml
      - name: Run tests with coverage
        run: |
          pytest --cov=src/apeg_core --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

### Task 7: Deployment and Raspberry Pi Considerations (LOW PRIORITY)

**Objective:** Provide deployment instructions for production environments.

**Files to Create:**
- `docs/APEG_DEPLOYMENT.md`
- `docs/RASPBERRY_PI_SETUP.md`

**Implementation Steps:**

#### 7.1 Create Deployment Guide
**File:** `docs/APEG_DEPLOYMENT.md`

**Sections:**
1. System Requirements
2. Installation Steps
3. Production Configuration
4. Systemd Service Setup
5. Nginx Reverse Proxy Configuration
6. SSL/TLS with Let's Encrypt
7. Monitoring and Logging
8. Backup and Recovery

**Example Systemd Service:**
```ini
[Unit]
Description=APEG Hybrid Orchestrator
After=network.target

[Service]
Type=simple
User=apeg
WorkingDirectory=/opt/apeg
Environment="PATH=/opt/apeg/venv/bin"
EnvironmentFile=/opt/apeg/.env
ExecStart=/opt/apeg/venv/bin/python -m apeg_core serve --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 7.2 Raspberry Pi Optimization
**File:** `docs/RASPBERRY_PI_SETUP.md`

**Optimizations:**
1. Use SQLite for memory store instead of JSON (reduce I/O)
2. Limit concurrent requests (single worker)
3. Reduce OpenAI token limits
4. Enable response caching
5. Use lightweight models (gpt-3.5-turbo)

**Recommended Settings for Pi:**
```bash
APEG_HOST=127.0.0.1
APEG_PORT=8000
APEG_RELOAD=false
OPENAI_DEFAULT_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1024
APEG_USE_LLM_SCORING=false  # Disable to reduce API calls
```

**Performance Tips:**
```bash
# Run with limited resources
python -m apeg_core serve --workers 1 --limit-concurrency 2
```

#### 7.3 Security Hardening
**Checklist:**
- [ ] Change default host to 127.0.0.1 for local-only access
- [ ] Use reverse proxy (nginx/caddy) with HTTPS
- [ ] Implement rate limiting (10 requests/minute)
- [ ] Add API authentication (Bearer tokens)
- [ ] Validate all user inputs
- [ ] Set proper CORS headers
- [ ] Use environment variables for all secrets
- [ ] Enable firewall rules
- [ ] Regular security updates

---

### Task 8: LangGraph/MCP Integration (EXPERIMENTAL)

**Objective:** Investigate integration with LangGraph MCP for dynamic tool discovery.

**Status:** RESEARCH PHASE - Do not implement until core integrations are stable

**Files to Create:**
- `docs/LANGGRAPH_MCP_RESEARCH.md`
- `src/apeg_core/connectors/mcp_client.py` (stub)

**Research Tasks:**
1. Review langgraph-mcp architecture
2. Identify integration points with APEG orchestrator
3. Design adapter interface
4. Create proof-of-concept
5. Document findings

**Integration Approach (Preliminary):**
```python
# src/apeg_core/connectors/mcp_client.py
class MCPClient:
    """Client for Model Context Protocol servers."""

    def discover_tools(self, server_url: str) -> List[Dict]:
        """Discover available tools from MCP server."""
        pass

    def call_tool(self, tool_name: str, params: Dict) -> Any:
        """Call a tool via MCP protocol."""
        pass
```

**Node Type in WorkflowGraph.json:**
```json
{
  "id": "mcp_call",
  "type": "mcp_tool_call",
  "config": {
    "server_url": "http://localhost:8080",
    "tool_name": "dynamic_tool"
  }
}
```

**Status:** POSTPONED until Phase 8 core tasks complete

---

## Testing Strategy

### Test Coverage Goals
- **Target:** 85% coverage for new code
- **Minimum:** 80% coverage overall
- **Critical paths:** 100% coverage for authentication, API calls, error handling

### Test Categories

#### Unit Tests (Existing + New)
- All LLM roles (8 tests per role = 48 tests)
- Shopify agent methods (9 tests)
- Etsy agent methods (9 tests)
- Enhanced scoring (10 tests)
- Total new unit tests: ~76

#### Integration Tests (New)
- OpenAI API integration (5 tests)
- Shopify API integration (5 tests)
- Etsy API integration (5 tests)
- End-to-end workflow with real APIs (3 tests)
- Total integration tests: ~18

#### Acceptance Tests
- Test mode functionality (all APIs work in test mode)
- Production mode functionality (real API calls)
- Error handling and retries
- Configuration validation

### Test Execution
```bash
# Run all tests with test mode
APEG_TEST_MODE=true pytest tests/ -v

# Run integration tests with real APIs (requires keys)
APEG_TEST_MODE=false pytest tests/test_*_integration.py -v

# Run with coverage
pytest --cov=src/apeg_core --cov-report=html tests/
```

---

## Risk Assessment

### High Risk
1. **API Authentication Complexity**
   - Mitigation: Start with test mode, thorough documentation
2. **API Rate Limiting**
   - Mitigation: Implement exponential backoff, use HTTPClient with retries
3. **Credential Management**
   - Mitigation: Use environment variables, clear documentation, .env.sample

### Medium Risk
1. **API Schema Changes**
   - Mitigation: Version pinning, graceful degradation
2. **Test Coverage**
   - Mitigation: Strict CI requirements, code review

### Low Risk
1. **Performance on Raspberry Pi**
   - Mitigation: Documented optimizations, resource limits

---

## Timeline and Milestones

### Week 1: OpenAI and Scoring
- Days 1-2: Implement LLM roles with OpenAI API
- Days 3-4: Add tests and documentation
- Day 5: Enhance scoring with LLM integration

### Week 2: Shopify and Etsy
- Days 1-2: Implement Shopify agent
- Days 3-4: Implement Etsy agent
- Day 5: Integration tests and bug fixes

### Week 3: Configuration and Deployment
- Days 1-2: Environment management and validation
- Days 3-4: CI/CD updates and deployment docs
- Day 5: Final testing and hardening

### Week 4: Buffer and Documentation
- Days 1-2: Address issues and refinements
- Days 3-5: Complete documentation and deployment guides

---

## Acceptance Criteria

### Functional Requirements
- [ ] All LLM roles execute real OpenAI calls when test mode is disabled
- [ ] ShopifyAgent performs 9 operations via Shopify Admin API
- [ ] EtsyAgent performs 9 operations via Etsy API v3
- [ ] Enhanced scoring uses LLM for quality assessment
- [ ] Test mode works for all components (backward compatible)

### Quality Requirements
- [ ] Test coverage ≥ 80% overall, ≥ 85% for new code
- [ ] All CI/CD tests pass
- [ ] No breaking changes to existing APIs
- [ ] Code passes linting (ruff, black)
- [ ] Type hints added to all new functions

### Documentation Requirements
- [ ] .env.sample created with all variables
- [ ] API setup guides for OpenAI, Shopify, Etsy
- [ ] Deployment guide for production
- [ ] Raspberry Pi optimization guide
- [ ] Updated APEG_STATUS.md with Phase 8 completion

### Security Requirements
- [ ] No hardcoded secrets in code
- [ ] Environment variable validation
- [ ] API error messages don't leak credentials
- [ ] Rate limiting implemented
- [ ] Input validation for all external data

---

## Future Enhancements (Post-Phase 8)

### Phase 9: Advanced Features
- GraphQL API support for Shopify
- Webhook handlers for real-time updates
- Multi-shop support for Etsy
- Batch operations for efficiency
- Caching layer for API responses

### Phase 10: Enterprise Features
- Database backend (PostgreSQL) for scalability
- Admin dashboard for monitoring
- User authentication and authorization
- Multi-tenant support
- Audit logging and compliance

### Phase 11: AI Enhancements
- Custom fine-tuned models for scoring
- Reinforcement learning for macro selection
- Automated A/B testing for prompts
- Predictive analytics for inventory

---

## Appendix

### A. API Documentation Links
- **OpenAI:** https://platform.openai.com/docs/api-reference
- **Shopify:** https://shopify.dev/docs/api/admin-rest
- **Etsy:** https://developers.etsy.com/documentation/

### B. Dependency Versions
```toml
openai = ">=1.0.0"
requests = ">=2.31.0"
requests-oauthlib = ">=1.3.0"
language-tool-python = ">=2.7.0"
fastapi = ">=0.104.0"
uvicorn = ">=0.24.0"
```

### C. Environment Variable Reference
See `.env.sample` for complete list.

### D. Troubleshooting Guide
**Common Issues:**
1. "OPENAI_API_KEY not set" - Add to .env or set APEG_TEST_MODE=true
2. "Shopify authentication failed" - Verify shop URL and access token
3. "Etsy token expired" - Implement automatic token refresh
4. "Rate limit exceeded" - Add delays, use retry logic

---

**Document Status:** APPROVED FOR IMPLEMENTATION
**Last Updated:** 2025-11-20
**Next Review:** After Week 2 completion
