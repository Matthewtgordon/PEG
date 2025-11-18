# APEG Runtime - Requirements Summary

**Version:** 1.0.0
**Date:** 2025-11-18
**Status:** Draft

## 1. Executive Summary

APEG (Autonomous Prompt Engineering Graph) is a modernized Python runtime that:
- Executes workflow graphs with intelligent agent orchestration
- Uses multi-armed bandit (MAB) selection with loop detection for adaptive decision-making
- Integrates OpenAI Agents/Graph APIs for advanced agentic capabilities
- Supports domain-specific agents (Shopify, Etsy) for e-commerce integration
- Implements scoring, logging, and adoption gates for quality control

### Design Philosophy
- **Spec as Authority:** Existing PEG JSON/TXT files define behavior; prototype code provides implementation guidance
- **Minimize Placeholders:** All stubs must be tracked and documented
- **Modular Architecture:** Clean package structure with clear separation of concerns
- **Test-Driven:** Comprehensive test coverage with CI/CD integration
- **Production-Ready:** Focus on Python 3.11+, Ubuntu Linux (Raspberry Pi target)

---

## 2. Core Components

### 2.1 Orchestrator (`src/apeg_core/orchestrator.py`)

**Responsibilities:**
- Load and parse SessionConfig.json, WorkflowGraph.json, TagEnum.json, Knowledge.json
- Execute workflow graphs as defined in WorkflowGraph.json
- Manage agent roles (PEG, ENGINEER, VALIDATOR, CHALLENGER, LOGGER, SCORER, TESTER)
- Route between nodes based on conditions and edges
- Integrate decision engine, scoring, and logging

**Key Features:**
- Start at configured "intake" node
- Execute nodes in DAG order following edges
- Apply loop guard and scoring at decision points
- Handle conditional routing (score_passed, validation_failed, loop_detected, etc.)
- Circuit breaker pattern for node failures
- Retry logic with exponential backoff

**Acceptance Criteria:**
- [ ] Loads all required config files without error
- [ ] Builds internal graph representation from WorkflowGraph.json
- [ ] Executes simple workflow from intake → prep → build → review → export
- [ ] Handles conditional edges correctly
- [ ] Integrates with decision engine (bandit + loop guard)
- [ ] Logs all node transitions to history

### 2.2 Decision Engine (`src/apeg_core/decision/`)

#### 2.2.1 Bandit Selector (`bandit_selector.py`)
**Algorithm:** Thompson Sampling with exploration bonus

**Responsibilities:**
- Maintain per-macro success/failure statistics
- Sample from Beta distribution for each macro
- Apply exploration bonus: `1.0 / (1 + plays)`
- Persist weights to JSON file
- Support decay factor for aging historical data

**Acceptance Criteria:**
- [ ] Loads/saves weights from `bandit_weights.json`
- [ ] Correctly implements Thompson Sampling
- [ ] Returns best macro given history and config
- [ ] Applies decay to historical statistics
- [ ] Updates statistics based on rewards/scores

#### 2.2.2 Loop Guard (`loop_guard.py`)
**Algorithm:** Repeated macro detection with score improvement threshold

**Responsibilities:**
- Monitor last N "build" actions in history
- Detect if same macro chosen repeatedly
- Check for score improvement > epsilon
- Trigger fallback if loop detected

**Configuration (from SessionConfig.json):**
- `N`: Number of consecutive repeats to check (default: 3)
- `epsilon`: Minimum score improvement required (default: 0.02)

**Acceptance Criteria:**
- [ ] Filters history to extract "build" events
- [ ] Correctly detects loops (same macro, N times, no improvement)
- [ ] Returns False if score improves beyond epsilon
- [ ] Returns True and logs loop detection

#### 2.2.3 MCTS Planner (`mcts_planner.py`)
**Status:** Placeholder (APEG-PH-1)

**Future Responsibilities:**
- Implement Monte Carlo Tree Search for macro planning
- Use UCT (Upper Confidence Bound for Trees) for exploration
- Generate multi-step macro plans
- Balance exploration vs exploitation

**Acceptance Criteria (Placeholder):**
- [ ] Stub class exists with clear docstring
- [ ] Marked with TODO[APEG-PH-1] in code
- [ ] Registered in docs/APEG_PLACEHOLDERS.md
- [ ] Does not crash when imported

### 2.3 Workflow Executor (`src/apeg_core/workflow/graph_executor.py`)

**Responsibilities:**
- Execute individual workflow nodes
- Call appropriate agents/tools per node definition
- Manage node state and transitions
- Apply scoring and loop guard logic
- Handle node failures and retries

**Integration:**
- Works with APEGOrchestrator to execute graph
- Calls openai_tools.py for agent interactions
- Uses decision engine for macro selection
- Logs results via logbook_adapter.py

**Acceptance Criteria:**
- [ ] Executes each node type correctly (start, process, decision, trigger, end)
- [ ] Calls agents based on node.agent field
- [ ] Applies node.action logic
- [ ] Returns result + metadata for routing
- [ ] Handles errors gracefully

### 2.4 OpenAI Integration (`src/apeg_core/connectors/openai_tools.py`)

**Responsibilities:**
- Wrapper for OpenAI Python SDK
- Support for Agents/Graph APIs (if available)
- Instantiate agents with system prompts from specs
- Register tools for domain agents
- Execute tasks and return structured responses
- Handle API errors and rate limits

**Configuration Sources:**
- PromptModules.json for API endpoints
- SessionConfig.json for defaults (temperature=0.3, max_tokens=4096)
- PromptEngineer.txt for system prompt templates
- Knowledge.json for agent context

**Acceptance Criteria:**
- [ ] Initializes OpenAI client with API key from environment
- [ ] Creates agents/assistants with system prompts
- [ ] Registers custom tools/functions
- [ ] Executes tasks and returns responses
- [ ] Handles rate limits and API errors
- [ ] Logs all API calls

**OpenAI Agents/Graph Research Required:**
- [ ] Check current SDK for Agents API (beta.assistants, beta.threads)
- [ ] Check for graph/orchestration features
- [ ] Determine if native graph support exists
- [ ] Fallback to local graph executor if needed

### 2.5 Domain Agents (`src/apeg_core/agents/`)

#### 2.5.1 Base Agent (`base_agent.py`)
**Interface Definition:**

```python
class BaseAgent:
    def __init__(self, name: str, description: str, config: dict):
        pass

    def run_task(self, task: dict | str, context: dict) -> dict:
        """Execute a task and return structured result."""
        pass

    def attach_tools(self, tools: list) -> None:
        """Register available tools/functions."""
        pass

    @property
    def supported_tasks(self) -> list[str]:
        """List of task types this agent can handle."""
        pass
```

**Acceptance Criteria:**
- [ ] Base class with clear interface
- [ ] Type hints and docstrings
- [ ] Subclasses can override all methods
- [ ] Provides common utilities (logging, error handling)

#### 2.5.2 Shopify Agent (`shopify_agent.py`)
**Status:** Stub with placeholders

**Intended Operations:**
- Product sync (fetch product data from Shopify)
- Inventory check (check stock levels)
- SEO analysis (analyze product SEO)
- Order management (future)
- Customer management (future)

**Current Implementation:**
- Stub methods that log intent
- Return structured dummy data
- No real API calls (test mode only)
- Each stub marked with TODO[APEG-PH-x]

**Acceptance Criteria:**
- [ ] Subclasses BaseAgent
- [ ] Implements product_sync() stub
- [ ] Implements inventory_check() stub
- [ ] Implements seo_analysis() stub
- [ ] Returns predictable structured data
- [ ] All stubs documented in APEG_PLACEHOLDERS.md
- [ ] Tests verify stub behavior

#### 2.5.3 Etsy Agent (`etsy_agent.py`)
**Status:** Stub with placeholders

**Intended Operations:**
- Listing sync (fetch listing data from Etsy)
- Inventory management
- SEO optimization
- Shop analytics (future)

**Current Implementation:**
- Similar to ShopifyAgent
- Stub methods with structured responses
- Test mode only
- Placeholders tracked

**Acceptance Criteria:**
- [ ] Subclasses BaseAgent
- [ ] Implements listing_sync() stub
- [ ] Implements inventory_management() stub
- [ ] Returns predictable structured data
- [ ] All stubs documented in APEG_PLACEHOLDERS.md
- [ ] Tests verify stub behavior

### 2.6 Connectors (`src/apeg_core/connectors/`)

#### 2.6.1 HTTP Tools (`http_tools.py`)
**Responsibilities:**
- Abstraction layer for HTTP requests
- Support for test mode (no real transactional operations)
- Centralized error handling
- Rate limiting and retry logic
- Request/response logging

**Features:**
- GET, POST, PUT, DELETE methods
- Header management (auth, content-type)
- Query parameter encoding
- JSON request/response handling
- Timeout configuration
- Test mode flag to prevent real API calls

**Acceptance Criteria:**
- [ ] Implements safe HTTP methods
- [ ] Test mode blocks real transactions
- [ ] Handles common HTTP errors (4xx, 5xx)
- [ ] Retries with exponential backoff
- [ ] Logs all requests and responses
- [ ] Validates SSL certificates

#### 2.6.2 GitHub Tools (`github_tools.py`)
**Status:** Port from existing `src/connectors/github_connector.py`

**Responsibilities:**
- Read files from GitHub repositories
- Commit changes (if configured)
- Branch management
- File change tracking

**Configuration:**
- From SessionConfig.json github_integration section
- Repository: Matthewtgordon/PEGGPT (or APEG-configured repo)
- Auth via GITHUB_PAT environment variable

**Acceptance Criteria:**
- [ ] Read files from repo
- [ ] List repository contents
- [ ] Create commits (if enabled)
- [ ] Track file changes
- [ ] Handle authentication

### 2.7 Memory Management (`src/apeg_core/memory/memory_manager.py`)

**Status:** Port from existing `src/memory_manager.py`

**Responsibilities:**
- Maintain session state
- Store workflow history
- Tag-based memory recall
- Knowledge base integration

**Acceptance Criteria:**
- [ ] Stores session context
- [ ] Retrieves memory by tags
- [ ] Integrates with Knowledge.json
- [ ] Thread-safe operations

### 2.8 Scoring System (`src/apeg_core/scoring/evaluator.py`)

**Responsibilities:**
- Load scoring configuration from PromptScoreModel.json
- Evaluate workflow outputs against criteria
- Map scores to bandit rewards
- Track scoring history

**Scoring Criteria (from SessionConfig.json):**
1. **Clarity** - Output is clear and understandable
2. **Constraint Obedience** - Follows all specified constraints
3. **Format Compliance** - Matches required format/structure
4. **User Override Respect** - Honors user overrides and preferences

**Scoring Model (PromptScoreModel.json):**
- Thresholds for pass/fail
- Weights for each criterion
- Aggregation method (average, weighted, etc.)

**Acceptance Criteria:**
- [ ] Loads PromptScoreModel.json
- [ ] Evaluates outputs against 4 criteria
- [ ] Returns float score (0.0 to 1.0)
- [ ] Maps scores to bandit rewards (0 or 1)
- [ ] Logs all scoring events
- [ ] Supports custom scoring heuristics if config missing

### 2.9 Logging System (`src/apeg_core/logging/logbook_adapter.py`)

**Responsibilities:**
- Append-only logging to Logbook.json and Journal.json
- Structured log entries with metadata
- Atomic writes to prevent corruption
- Query interface for log analysis

**Log Entry Structure:**
```json
{
  "timestamp": "2025-11-18T10:30:00+00:00",
  "phase": "review",
  "component": "orchestrator",
  "outcome": "score_passed",
  "score": 0.87,
  "notes": "..."
}
```

**Acceptance Criteria:**
- [ ] Writes to Logbook.json atomically
- [ ] Writes to Journal.json for detailed logs
- [ ] Includes timestamp, phase, component, outcome, score
- [ ] Supports querying by phase or component
- [ ] Thread-safe operations
- [ ] Handles file lock contention

### 2.10 Adoption Gate

**Purpose:** Quality control before saving/exporting outputs

**Logic (from PromptEngineer.txt):**
```
score = run_scoring(current_output, PromptScoreModel.json)
if score < threshold:
    log_to_logbook("adoption_gate_failed", {"score": score})
    block export, route to fallback
else:
    log_to_logbook("adoption_gate_passed", {"score": score})
    proceed to export
```

**Integration:**
- Runs in "review" or dedicated "adoption_gate" node
- Uses scoring/evaluator.py
- Routes to fallback if score < threshold
- Threshold from SessionConfig.json (minimum_score: 0.80)

**Acceptance Criteria:**
- [ ] Evaluates output score
- [ ] Compares against threshold
- [ ] Logs result (passed/failed)
- [ ] Routes to correct next node
- [ ] Integrates with bandit selector (failed = negative reward)

---

## 3. Runtime Environment

### 3.1 Platform Requirements
- **OS:** Ubuntu Linux (Raspberry Pi compatible)
- **Python:** 3.11 or higher
- **Package Manager:** pip with pyproject.toml support

### 3.2 Dependencies
**Core:**
- openai (OpenAI Python SDK)
- requests or httpx (HTTP client)
- jsonschema (Schema validation)
- python-dotenv (Environment variables)

**Testing:**
- pytest (Test framework)
- pytest-cov (Coverage reporting)

**Optional:**
- google-generativeai (for Gemini scoring models)

### 3.3 Environment Variables
- `OPENAI_API_KEY` - OpenAI API authentication
- `GITHUB_PAT` - GitHub Personal Access Token (optional)
- `APEG_TEST_MODE` - Enable test mode (no real API calls)

---

## 4. Configuration Files

### 4.1 SessionConfig.json
**Purpose:** Runtime configuration

**Key Sections:**
- `session_type`, `mode`, `tools_enabled`, `web_access`
- `scoring` - Enabled, criteria, apply_learning
- `loop_guard` - N, epsilon
- `selector` - Algorithm, bandit settings
- `openai_chat_defaults` - Temperature, max_tokens
- `github_integration` - Repo, branch, commit settings

### 4.2 WorkflowGraph.json
**Purpose:** Workflow definition

**Structure:**
- `agent_roles` - Role definitions (PEG, ENGINEER, etc.)
- `nodes` - Workflow nodes (id, label, type, agent, action)
- `edges` - Transitions (from, to, condition)

### 4.3 Knowledge.json
**Purpose:** Knowledge base for agent context

**Structure:**
- `knowledge_items` - List of facts/rules
- Each item: id, topic, tag, tier, content

### 4.4 TagEnum.json
**Purpose:** System-wide tag definitions

**Categories:**
- format, exemption, enforcement, trigger, logging, feature, safety, evaluation, meta, rule, execution, procedure

### 4.5 PromptModules.json
**Purpose:** API endpoint definitions

**Modules:**
- `openai_chat` - OpenAI API configuration
- `github_read` - GitHub API configuration

---

## 5. CLI Entrypoint

### 5.1 Location
`src/apeg_cli.py` or `src/apeg/__main__.py`

### 5.2 Basic Usage
```bash
# Run demo workflow
python -m apeg_core

# Or via CLI script
python src/apeg_cli.py

# Run specific workflow
python -m apeg_core --workflow demo

# Test mode
APEG_TEST_MODE=1 python -m apeg_core
```

### 5.3 Responsibilities
- Load configurations
- Initialize orchestrator
- Run workflow
- Print results
- Handle errors gracefully
- Provide --help documentation

**Acceptance Criteria:**
- [ ] Loads configs from current directory
- [ ] Runs simple demo workflow
- [ ] Prints high-level results
- [ ] Exits with appropriate status codes
- [ ] Provides clear error messages

---

## 6. Testing Strategy

### 6.1 Unit Tests
- Test each module in isolation
- Mock external dependencies (OpenAI API, HTTP calls)
- Achieve >80% code coverage

### 6.2 Integration Tests
- Test orchestrator with real configs
- Test agent interactions
- Test workflow execution end-to-end

### 6.3 Test Organization
```
tests/
├── test_decision_bandit.py
├── test_decision_loop_guard.py
├── test_orchestrator_apeg.py
├── test_agents_shopify.py
├── test_agents_etsy.py
├── test_scoring_apeg.py
├── test_logging_apeg.py
├── test_adoption_gate.py
└── conftest.py  # Shared fixtures
```

### 6.4 CI/CD
- GitHub Actions workflow: `.github/workflows/apeg-ci.yml`
- Run on Python 3.11, 3.12
- Run pytest with coverage
- Optionally run validate_repo.py

---

## 7. Acceptance Criteria

### 7.1 Package Structure
- [ ] pyproject.toml exists with proper metadata and dependencies
- [ ] src/apeg_core/ package structure created
- [ ] All modules organized by responsibility
- [ ] CLI entrypoint functional

### 7.2 Core Functionality
- [ ] APEGOrchestrator loads configs and runs workflows
- [ ] Decision engine (bandit + loop guard) ported and tested
- [ ] OpenAI integration functional (with test mode)
- [ ] Domain agents (Shopify, Etsy) implemented as stubs
- [ ] Scoring system integrated
- [ ] Logging system functional
- [ ] Adoption gate implemented

### 7.3 Testing
- [ ] All phases have corresponding tests
- [ ] Tests pass in CI
- [ ] Coverage >80%
- [ ] No critical failures

### 7.4 Documentation
- [ ] APEG_STATUS.md up-to-date
- [ ] APEG_TODO.md reflects remaining work
- [ ] APEG_PLACEHOLDERS.md tracks all stubs
- [ ] APEG_RUNTIME_STATUS.md created

### 7.5 Quality
- [ ] Code follows PEP 8
- [ ] Type hints used throughout
- [ ] Docstrings for all public classes/methods
- [ ] No untracked placeholders

---

## 8. Known Limitations

### 8.1 Current Placeholders
1. **MCTS Planner** - Stub only, no real implementation
2. **Shopify Agent** - No real API calls, test mode only
3. **Etsy Agent** - No real API calls, test mode only
4. **Advanced Scoring** - Simple heuristics if PromptScoreModel.json incomplete

### 8.2 Future Enhancements
- Real Shopify/Etsy API integration
- MCTS planning implementation
- Advanced prompt engineering techniques
- Telemetry and monitoring
- Performance optimization
- Multi-agent coordination

---

## 9. Migration from PEG

### 9.1 Strategy
- Keep existing PEG files intact
- New APEG code in src/apeg_core/
- Port logic, not just copy
- Improve type hints and documentation
- Maintain backward compatibility where possible

### 9.2 Legacy Files
- Move to archived_configs/ or archived_src/
- Document in APEG_STATUS.md as "legacy - not used by APEG runtime"
- Do not delete

---

## 10. Success Criteria Summary

APEG runtime is considered **COMPLETE** when:

1. ✅ APEG package layout exists under src/apeg_core/
2. ✅ APEGOrchestrator can load configs and run demo workflow
3. ✅ Decision engine (bandit + loop guard) ported and tested
4. ✅ Domain agents (Shopify, Etsy) implemented as testable stubs
5. ✅ Scoring, logging, adoption gate functional
6. ✅ CI workflow exists and passes
7. ✅ All documentation up-to-date (STATUS, TODO, PLACEHOLDERS, RUNTIME_STATUS)
8. ✅ All placeholders tracked and documented
9. ✅ Code committed to feature branch
10. ✅ No persistent test failures

**Failure Condition:**
If persistent failures occur that cannot be resolved, create `docs/APEG_FAILURE_REPORT.md` with details and stop.
