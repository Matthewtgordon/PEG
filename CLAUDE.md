# CLAUDE.md - PEG Project Guide for AI Assistants

## Project Overview

**PEG (Promptable Engineer GPT)** is an advanced AI agent orchestration system designed for prompt engineering, validation, and quality control. It implements a graph-based workflow execution engine with multi-agent collaboration, reinforcement learning-based macro selection, and automated quality scoring.

### Important: APEG vs Legacy PEG

This repository contains **two implementations**:

1. **APEG (Autonomous Prompt Engineering Graph)** - Current, production-ready implementation
   - Location: `src/apeg_core/`
   - Status: Phases 0-7 complete, 132 tests passing
   - Use this for all new development
   - Modern Python packaging with pyproject.toml

2. **Legacy PEG** - Original prototype implementation
   - Location: `src/` (root level: `orchestrator.py`, `bandit_selector.py`, etc.)
   - Status: Preserved for reference, not actively developed
   - Decision engine components were ported to APEG in Phase 3

**When working on this project, use APEG (src/apeg_core/) unless explicitly working with legacy code.**

### Core Purpose
- Orchestrate complex prompt engineering workflows
- Validate and score prompt outputs against quality metrics
- Learn from historical performance using bandit algorithms
- Prevent infinite loops and degraded outputs
- Integrate with external services (OpenAI, GitHub)
- Maintain knowledge persistence and version control

### Technology Stack
- **Language**: Python 3.8-3.12
- **Key Libraries**: jsonschema, pytest, openai, google-generativeai, requests, python-dotenv
- **Configuration**: JSON-based declarative configuration
- **CI/CD**: GitHub Actions with automated validation and scoring

---

## Repository Structure

```
PEG/
├── .github/
│   └── workflows/          # CI/CD pipeline definitions
│       ├── peg-ci.yml      # Main CI pipeline (validate, test, score)
│       ├── test-matrix.yml # Matrix testing across Python versions
│       ├── append-to-log.yml
│       └── update-tasks.yml
├── src/                    # Core Python modules
│   ├── orchestrator.py     # Workflow graph execution engine
│   ├── bandit_selector.py  # Thompson Sampling macro selector
│   ├── memory_manager.py   # Short/long-term memory management
│   ├── loop_guard.py       # Loop detection system
│   ├── knowledge_update.py # Knowledge base mutation logic
│   ├── plugin_manager.py   # Plugin system for extensibility
│   ├── sandbox_executor.py # Safe execution environment
│   └── connectors/         # External service integrations
│       ├── base_connector.py
│       ├── openai_connector.py
│       ├── github_connector.py
│       └── filesystem_connector.py
├── tests/                  # Pytest test suite
│   ├── conftest.py         # Test configuration and fixtures
│   ├── test_orchestrator.py
│   ├── test_bandit_selector.py
│   ├── test_memory_manager.py
│   ├── test_workflow_graph.py
│   ├── test_knowledge_validation.py
│   └── test_environment.py
├── schemas/                # JSON Schema definitions
│   └── knowledge.schema.json
├── config/                 # Additional configuration files
├── scripts/                # Utility scripts
├── archived_configs/       # Historical configurations
│
├── WorkflowGraph.json      # Single source of truth for orchestration
├── SessionConfig.json      # Runtime configuration and settings
├── Knowledge.json          # Persistent knowledge base (versioned)
├── Rules.json              # Enforcement rules and policies
├── Tasks.json              # Checklist and task tracking
├── Tests.json              # Test definitions and expectations
├── Logbook.json            # Session audit log
├── Journal.json            # Additional logging
├── TagEnum.json            # Tag definitions for routing
├── PromptScoreModel.json   # Quality scoring metrics and weights
├── PromptModules.json      # Prompt module definitions
├── Modules.json            # System modules configuration
├── Agent_Prompts.json      # Agent role prompts
├── PromptEngineer.txt      # DSL-style workflow definition
│
├── run_scoring.py          # Quality scoring script (CI gate)
├── validate_repo.py        # Repository integrity validation
├── test_env.py             # Environment testing utility
├── requirements.txt        # Python dependencies
└── LICENSE                 # MIT License
```

---

## Core Architecture

### Workflow Execution Model

PEG uses a **directed graph workflow** defined in `WorkflowGraph.json`:

```
intake → prep → build → review → [export | loop_detector | external_call]
                          ↑          ↓
                          └─ reroute ←─ loop_detector
                          ↑          ↓
                          └─ fallback ←─ loop_detector
```

### Agent Roles (Multi-Agent System)

Defined in `WorkflowGraph.json`:
- **PEG**: Session orchestrator, controls fallback, logs via LOGGER
- **ENGINEER**: Designs macro chains, injects constraints
- **VALIDATOR**: Validates structure, schema conformance, output format
- **CHALLENGER**: Stress-tests logic, triggers fallback on flaws
- **LOGGER**: Audits file changes, mutations, scoring logs
- **SCORER**: Evaluates outputs using PromptScoreModel
- **TESTER**: Injects regression and edge tests

### Key Components

#### 1. Orchestrator (`src/orchestrator.py`)
- Graph execution engine that brings `WorkflowGraph.json` to life
- Manages workflow state, history, and node transitions
- Implements retry logic and circuit breakers
- Handles node execution and conditional routing
- **Entry Point**: `Orchestrator.execute_graph()`

#### 2. Bandit Selector (`src/bandit_selector.py`)
- Thompson Sampling algorithm for macro selection
- Learns from historical performance with decay factor
- Persists weights to `bandit_weights.json`
- Balances exploration vs exploitation
- **Key Function**: `choose_macro(macros, history, config)`

#### 3. Memory Manager (`src/memory_manager.py`)
- Short-term and long-term memory storage
- Namespace-based organization (per-task, per-agent)
- Automatic summarization when limits exceeded
- Pruning and querying capabilities
- **Usage**: `add()`, `query_long_term()`, `prune()`

#### 4. Loop Guard (`src/loop_guard.py`)
- Detects infinite loops in macro selection
- Configurable parameters: `N` (window size), `epsilon` (tolerance)
- Prevents degraded output cycles
- **Function**: `detect_loop(history, N=3, epsilon=0.02)`

#### 5. Scoring System (`run_scoring.py`)
- Weighted quality metrics defined in `PromptScoreModel.json`
- Metrics: test_pass_rate, semantic_relevance, syntactic_correctness, selector_accuracy, structure, efficiency
- CI gate: blocks export if score < threshold
- **Command**: `python run_scoring.py --model PromptScoreModel.json --input <file> --out score.json`

#### 6. Connectors (`src/connectors/`)
- **base_connector.py**: Abstract base class
- **openai_connector.py**: OpenAI API integration
- **github_connector.py**: GitHub API operations
- **filesystem_connector.py**: File system operations

---

## Configuration Files

### WorkflowGraph.json
**Purpose**: Single source of truth for workflow orchestration

**Key Sections**:
- `nodes`: Workflow stages with agent assignments
- `edges`: Transitions with conditional routing
- `agent_roles`: Role definitions and responsibilities

**Version**: 2.1.0

### SessionConfig.json
**Purpose**: Runtime configuration and feature flags

**Key Settings**:
- `session_type`: "PEG"
- `mode`: "Full"
- `tools_enabled`: true
- `scoring.enabled`: true
- `github_integration`: GitHub settings
- `selector.algorithm`: "heuristic" (with bandit config)
- `loop_guard`: Loop detection parameters
- `ci.minimum_score`: 0.80
- `macros`: List of available macros

**Version**: 1.0.1

### Knowledge.json
**Purpose**: Persistent knowledge base with versioning

**Structure**:
- `version`: Semantic versioning (X.Y.Z)
- `metadata`: Creation, update timestamps, operation log
- `knowledge_items`: Array of knowledge entries
  - Each item has: `id`, `topic`, `tag`, `tier`, `content`
  - Tiers: knowledge, enforcement, meta, procedure, safety, evaluation

**CRITICAL**: All modifications must bump version and update metadata

**Version**: 3.3.7

### Rules.json
**Purpose**: Enforcement rules and operational policies

**Structure**:
- Versioned (1.1.0)
- `rules_items`: Array with id, topic, tag, tier, content
- Tags for routing: #PROMPT_STRUCTURE, #CLOUD_RECOVERY, #MUTATION_AUDIT, etc.

### PromptScoreModel.json
**Purpose**: Quality scoring configuration

**Structure**:
- `metrics`: Array with name, weight, description
- Weights must sum to 1.0
- `ci.minimum_score`: Threshold for CI gate
- `thresholds`: Pass/fail criteria

### Tasks.json
**Purpose**: Task tracking and checklist management

**Structure**:
- `tasks`: Array with id, task, status, kind
- `kind`: "checklist" or "note"
- `status`: "done", "active", etc.

---

## Development Workflow

### 1. Making Changes

**File Modification Protocol**:
1. Always read the file first before modifying
2. Validate JSON syntax after changes
3. For versioned files (Knowledge.json, Rules.json):
   - Bump the version number (semantic versioning)
   - Update `metadata.updated_at` timestamp
   - Add operation to `metadata.operation_log`

**Example Version Bump**:
```json
{
  "version": "3.3.7",  // Change to "3.3.8" for patch, "3.4.0" for minor
  "metadata": {
    "updated_at": "2025-11-18T12:00:00+00:00",  // Current timestamp
    "operation_log": [
      {
        "timestamp": "2025-11-18T12:00:00+00:00",
        "operation": "add_knowledge_item",
        "item_id": "new-uuid-here"
      }
    ]
  }
}
```

### 2. Adding New Features

**Workflow**:
1. Update relevant JSON configs (Knowledge.json, Rules.json, etc.)
2. Implement Python code in `src/`
3. Add tests in `tests/`
4. Update `WorkflowGraph.json` if adding new nodes/edges
5. Run validation: `python validate_repo.py`
6. Run tests: `pytest tests/`
7. Run scoring: `python run_scoring.py --model PromptScoreModel.json --input <file> --out score.json`

### 3. Testing

**Test Suite**:
- Location: `tests/`
- Runner: pytest
- Configuration: `tests/conftest.py`

**Running Tests**:
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_orchestrator.py

# With coverage
pytest --cov=src tests/

# With JUnit XML report (CI format)
pytest --junitxml=test-results/results.xml tests/
```

**Test Categories**:
- Unit tests: Individual component testing
- Integration tests: Workflow and connector testing
- Validation tests: Schema and configuration integrity

### 4. CI/CD Pipeline

**Pipeline**: `.github/workflows/peg-ci.yml`

**Steps**:
1. **Checkout**: Clone repository
2. **Setup Python**: Python 3.11
3. **Install Dependencies**: `pip install -r requirements.txt`
4. **Create .env**: Inject secrets (OPENAI_API_KEY, GEMINI_API_KEY, GITHUB_PAT)
5. **Validate Repository**: `python validate_repo.py`
6. **Run Scoring**: `python run_scoring.py --model PromptScoreModel.json --input README.md --out score.json`
7. **Run Tests**: `pytest --junitxml=test-results/results.xml tests/`
8. **Upload Artifacts**: score.json, test-results/

**Quality Gate**: Pipeline fails if:
- Repository validation fails (missing files, invalid JSON, schema violations)
- Scoring falls below `ci.minimum_score` (0.80)
- Any test fails

---

## Key Conventions

### 1. Naming Conventions

**Files**:
- Configuration: PascalCase with .json (Knowledge.json, SessionConfig.json)
- Python modules: snake_case (orchestrator.py, bandit_selector.py)
- Tests: test_*.py prefix

**Code**:
- Classes: PascalCase (Orchestrator, BanditSelector, MemoryManager)
- Functions: snake_case (execute_graph, choose_macro, detect_loop)
- Constants: UPPER_SNAKE_CASE (METRIC_FUNCTIONS)
- Private methods: _leading_underscore (_execute_node, _summarize)

### 2. Tag System

**Purpose**: Enable routing and filtering

**Format**: `#TAG_NAME` (uppercase with underscores)

**Common Tags**:
- `#PROMPT_STRUCTURE`: Prompt format requirements
- `#EMULATED_ONLY`: Execution flags
- `#MUTATION_AUDIT`: Change tracking
- `#SCORING_RULES`: Quality evaluation
- `#CLOUD_RECOVERY`: Backup and restore
- `#EXTERNAL_CALL`: External API calls
- `#GITHUB_BOOTSTRAP`: GitHub integration

**Usage in JSON**:
```json
{
  "id": "unique-uuid",
  "topic": "Descriptive Topic",
  "tag": "#TAG_NAME",
  "tier": "enforcement",
  "content": "Description of the rule or knowledge."
}
```

### 3. Version Management

**Semantic Versioning** (X.Y.Z):
- **Major (X)**: Breaking changes, incompatible API changes
- **Minor (Y)**: New features, backwards-compatible
- **Patch (Z)**: Bug fixes, minor corrections

**Files Requiring Versioning**:
- Knowledge.json
- Rules.json
- SessionConfig.json
- WorkflowGraph.json
- PromptScoreModel.json

### 4. JSON Schema Validation

**Schema Location**: `schemas/`

**Validation**:
- Performed by `validate_repo.py`
- Required for CI pipeline
- Uses `jsonschema` library

**Adding New Schemas**:
1. Create schema file in `schemas/`
2. Add validation to `validate_repo.py`
3. Update `SessionConfig.json` schema_links

### 5. Error Handling

**Patterns**:
- Try-except blocks with specific exceptions
- Logging via Python logging module
- Graceful fallbacks for missing files
- Circuit breakers for repeated failures
- Retry logic with exponential backoff

**Example**:
```python
retries = 0
max_retries = config.get('retry', {}).get('max_attempts', 3)
delay = 1.0
while retries < max_retries:
    try:
        result = self._execute_node(node)
        break
    except Exception as exc:
        retries += 1
        logging.error("Node %s failed: %s", node['id'], exc)
        time.sleep(delay)
        delay *= 2
```

### 6. Logging

**Logbook.json**: Session audit trail
- All workflow events
- Scoring results
- Mutation operations
- Error conditions

**Journal.json**: Additional notes and observations

**Python Logging**:
```python
import logging
logging.basicConfig(level=logging.INFO)
logging.info("Message")
logging.error("Error message")
logging.warning("Warning message")
```

---

## Key Concepts

### 1. Workflow Graph Execution

The orchestrator executes a state machine defined in `WorkflowGraph.json`:
- **Nodes** represent stages (intake, prep, build, review, etc.)
- **Edges** define transitions with optional conditions
- **State** tracks current position, history, and scores

**Conditional Routing**:
```json
{
  "from": "review",
  "to": "export",
  "condition": "score_passed"
}
```

### 2. Thompson Sampling (Bandit Algorithm)

**Purpose**: Learn which macros produce best results

**Algorithm**:
1. Maintain success/failure counts for each macro
2. Sample from Beta distribution: `Beta(successes, failures)`
3. Add exploration bonus: `1 / (1 + plays)`
4. Select macro with highest sampled value
5. Apply decay to historical weights

**Persisted State**: `bandit_weights.json`

### 3. Loop Detection

**Problem**: Prevent infinite loops where same macro is repeatedly selected despite failures

**Solution**:
- Track last N macro selections
- Calculate score variance within window
- If variance < epsilon, loop detected
- Trigger fallback or circuit breaker

**Configuration**:
```json
"loop_guard": {
  "enabled": true,
  "N": 3,
  "epsilon": 0.02
}
```

### 4. Memory Management

**Two-Tier System**:
- **Short-term**: Recent messages (limited by `short_term_limit`)
- **Long-term**: Summarized history (unlimited)

**Automatic Summarization**: When short-term buffer exceeds limit

**Namespaces**: Organize memory by task or agent

### 5. Quality Scoring

**Weighted Metrics**:
- Each metric has weight (must sum to 1.0)
- Total score = Σ(metric_score × weight)
- CI gate enforces minimum threshold

**Metric Calculation**:
- Placeholder functions in `run_scoring.py`
- Real implementations should call actual validators/LLMs

### 6. Fallback and Recovery

**Fallback Modes**:
- Missing configuration files → embedded defaults
- Validation failures → repair and retry
- Scoring failures → reroute to different macro
- Loop detection → circuit breaker escalation

**GitHub Recovery**: Load from versioned GitHub backup if local corruption

---

## Working with the Codebase (AI Assistant Guidelines)

### 1. Understanding Project Context

**Before Making Changes**:
1. Read `WorkflowGraph.json` to understand workflow
2. Check `SessionConfig.json` for current settings
3. Review `Knowledge.json` for domain knowledge
4. Examine `Rules.json` for constraints
5. Check `Tasks.json` for active work items

### 2. Modifying Configuration Files

**JSON Files - Always**:
1. Read the file first
2. Validate JSON syntax
3. Check against schema if available
4. Update version and metadata for versioned files
5. Run `python validate_repo.py` after changes

**Knowledge.json Changes**:
```python
# 1. Read current version
with open('Knowledge.json') as f:
    data = json.load(f)

# 2. Modify
data['knowledge_items'].append(new_item)

# 3. Bump version (patch)
version_parts = data['version'].split('.')
version_parts[-1] = str(int(version_parts[-1]) + 1)
data['version'] = '.'.join(version_parts)

# 4. Update metadata
data['metadata']['updated_at'] = datetime.now().isoformat() + '+00:00'
data['metadata']['operation_log'].append({
    'timestamp': datetime.now().isoformat() + '+00:00',
    'operation': 'add_knowledge_item',
    'item_id': new_item['id']
})

# 5. Write back
with open('Knowledge.json', 'w') as f:
    json.dump(data, f, indent=2)
```

### 3. Adding New Python Modules

**Structure**:
```python
"""
Brief module description.
Longer explanation of purpose and usage.
"""
from __future__ import annotations  # Enable modern type hints

import logging
from typing import Any, Dict, List

class MyComponent:
    """Class docstring."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

    def public_method(self) -> Any:
        """Public method docstring."""
        pass

    def _private_method(self) -> Any:
        """Private method docstring."""
        pass
```

**Testing**:
```python
# tests/test_my_component.py
import pytest
from src.my_component import MyComponent

def test_my_component_basic():
    """Test basic functionality."""
    component = MyComponent({'key': 'value'})
    result = component.public_method()
    assert result is not None
```

### 4. Debugging Workflows

**Enable Debug Mode**:
```json
// SessionConfig.json
{
  "debug_mode": true
}
```

**Check Logs**:
- Review `Logbook.json` for workflow events
- Check Python logging output
- Examine `bandit_weights.json` for selector state

**Test Orchestrator**:
```bash
python src/orchestrator.py
```

### 5. Common Tasks

**Task: Add a New Knowledge Item**
1. Read `Knowledge.json`
2. Generate UUID for item
3. Add to `knowledge_items` array
4. Bump version (patch)
5. Update metadata
6. Validate: `python validate_repo.py`

**Task: Add a New Workflow Node**
1. Read `WorkflowGraph.json`
2. Add node to `nodes` array with unique id
3. Add edges connecting to/from the node
4. Update `Orchestrator._execute_node()` to handle new node
5. Add tests for new node
6. Bump version

**Task: Modify Scoring Metrics**
1. Read `PromptScoreModel.json`
2. Adjust weights (ensure they sum to 1.0)
3. Update `run_scoring.py` metric functions
4. Test: `python run_scoring.py --model PromptScoreModel.json --input test.txt --out score.json`
5. Verify CI pipeline passes

**Task: Fix a Bug**
1. Write a failing test that reproduces the bug
2. Implement the fix
3. Verify test passes
4. Run full test suite: `pytest tests/`
5. Update relevant documentation

### 6. Git Workflow

**Branch Strategy**:
- Main branch: `main`
- Feature branches: `feature/description`
- Bug fixes: `fix/description`

**Commit Messages**:
- Use conventional commits format
- Examples:
  - `feat: add new loop detection algorithm`
  - `fix: correct version bumping in knowledge update`
  - `docs: update CLAUDE.md with scoring section`
  - `test: add tests for memory manager`
  - `chore: update dependencies`

**Pull Request Process**:
1. Create feature branch from `main`
2. Make changes with clear commits
3. Ensure CI pipeline passes
4. Request review
5. Address feedback
6. Merge when approved

### 7. Common Pitfalls to Avoid

**DON'T**:
- Modify JSON files without reading them first
- Skip version bumping for versioned files
- Ignore CI pipeline failures
- Add code without tests
- Use hard-coded secrets (use environment variables)
- Modify `WorkflowGraph.json` without updating orchestrator
- Forget to update metadata timestamps
- Break JSON syntax (validate after changes)
- Push without running local validation

**DO**:
- Read files before editing
- Run `validate_repo.py` after config changes
- Write tests for new functionality
- Use logging instead of print statements
- Follow existing code style
- Update documentation when changing behavior
- Use type hints in Python code
- Handle exceptions gracefully

### 8. Environment Variables

**Required Secrets** (for CI and connectors):
- `OPENAI_API_KEY`: OpenAI API access
- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`): Google AI access
- `GITHUB_PAT`: GitHub personal access token

**Local Development**:
Create `.env` file:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
GITHUB_PAT=ghp_...
```

**Usage**:
```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
```

### 9. Useful Commands

**Validation**:
```bash
python validate_repo.py
```

**Testing**:
```bash
pytest tests/                          # All tests
pytest tests/test_orchestrator.py     # Specific test
pytest -v                              # Verbose
pytest --cov=src                       # With coverage
```

**Scoring**:
```bash
python run_scoring.py \
  --model PromptScoreModel.json \
  --input <input_file> \
  --out score.json
```

**Orchestration**:
```bash
python src/orchestrator.py
```

**Environment Check**:
```bash
python test_env.py
```

### 10. Getting Help

**Resources**:
- `PromptEngineer.txt`: DSL workflow definition
- `WorkflowGraph.json`: Visual workflow structure
- `Knowledge.json`: Domain knowledge and conventions
- Test files: Usage examples for each component

**When Stuck**:
1. Check `Knowledge.json` for relevant topics
2. Review test files for usage examples
3. Examine `Logbook.json` for error patterns
4. Enable debug mode in `SessionConfig.json`
5. Run validation to identify structural issues

---

## Summary

PEG is a sophisticated AI agent orchestration system with:
- **Graph-based workflow execution** (WorkflowGraph.json)
- **Multi-agent collaboration** (6 specialized agent roles)
- **Reinforcement learning** (Thompson Sampling bandit selector)
- **Quality assurance** (automated scoring and CI gates)
- **Safety mechanisms** (loop detection, circuit breakers, fallbacks)
- **Version control** (semantic versioning for all configs)
- **External integrations** (OpenAI, GitHub)

**Core Principle**: Configuration-as-code with JSON files as single source of truth.

**Development Cycle**: Modify configs → Update code → Add tests → Validate → Test → Score → CI

**AI Assistant Role**: Follow conventions, maintain versioning, test thoroughly, document changes.

---

## Documentation Updates

**Note:** Documentation structure reorganized on 2025-11-20:
- Created `docs/archive/` for historical documents
- Created `docs/milestones/` for implementation milestones
- Created `README.md` for project overview
- See `docs/README.md` for documentation index

---

**Last Updated**: 2025-11-20
**Document Version**: 1.1.0
**Maintainer**: PEG Development Team
