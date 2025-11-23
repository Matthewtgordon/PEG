# OpenAI Agents SDK Integration Guide

**Document Version:** 1.0.0
**Created:** 2025-11-23
**Status:** Active Development
**Phase:** Phase 8 Enhancement

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [OpenAI Agents SDK Overview](#openai-agents-sdk-overview)
4. [Integration Design](#integration-design)
5. [Installation and Setup](#installation-and-setup)
6. [Usage Guide](#usage-guide)
7. [Configuration Reference](#configuration-reference)
8. [Multi-Agent Workflows](#multi-agent-workflows)
9. [Domain Agent Integration](#domain-agent-integration)
10. [Session Management](#session-management)
11. [Guardrails and Safety](#guardrails-and-safety)
12. [Testing and Validation](#testing-and-validation)
13. [Migration Guide](#migration-guide)
14. [Troubleshooting](#troubleshooting)
15. [Future Roadmap](#future-roadmap)
16. [References](#references)

---

## Executive Summary

This document provides comprehensive guidance for integrating the OpenAI Agents SDK with the APEG (Autonomous Prompt Engineering Graph) system. The integration enables sophisticated multi-agent workflows, handoffs between specialized agents, tool integration, and session management while maintaining backwards compatibility with existing APEG infrastructure.

### Key Benefits

- **Multi-Agent Orchestration**: Native support for agent handoffs and collaboration
- **Tool Integration**: Domain agents (Shopify, Etsy) as function tools
- **Session Management**: Built-in conversation history with SQLite/Redis
- **Guardrails**: Input/output validation for safety and quality
- **Provider Agnostic**: Support for 100+ LLM providers via LiteLLM
- **Tracing**: Built-in execution tracing for debugging and optimization
- **Hybrid Mode**: Graceful fallback to Chat Completions API

### Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| OpenAI Agents Adapter | Implemented | `src/apeg_core/llm/openai_agents_adapter.py` |
| Role Mapping | Complete | All 8 APEG roles mapped to agents |
| Handoff Support | Implemented | Orchestrator with specialist handoffs |
| Session Management | Implemented | SQLite sessions with async support |
| Domain Tool Integration | Partial | Framework ready, needs domain agent updates |
| Guardrails | Planned | Framework in place |
| Tracing | Planned | SDK supports it, needs APEG integration |

---

## Architecture Overview

### High-Level Architecture

```
                     ┌─────────────────────────────────────────┐
                     │           APEG Orchestrator              │
                     │         (WorkflowGraph.json)             │
                     └──────────────────┬──────────────────────┘
                                        │
                     ┌──────────────────▼──────────────────────┐
                     │            AgentsBridge                  │
                     │         (Facade/Entry Point)             │
                     └──────────────────┬──────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
   ┌──────────▼──────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
   │  OpenAI Agents SDK  │   │  OpenAI Chat API    │   │    Test Mode      │
   │      Adapter        │   │    (Fallback)       │   │  (Deterministic)  │
   └──────────┬──────────┘   └─────────────────────┘   └───────────────────┘
              │
   ┌──────────▼──────────────────────────────────────────────────────────┐
   │                     OpenAI Agents SDK                                │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
   │  │   Agent     │  │   Runner    │  │   Session   │  │   Tracing   │ │
   │  │ (with tools,│  │ (execution) │  │  (history)  │  │  (debug)    │ │
   │  │  handoffs)  │  │             │  │             │  │             │ │
   │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
   └──────────────────────────────────────────────────────────────────────┘
```

### Component Interactions

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         APEG Role Execution Flow                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Orchestrator calls AgentsBridge.run_role(ENGINEER, prompt, context)  │
│                              │                                           │
│                              ▼                                           │
│  2. AgentsBridge delegates to OpenAIAgentsAdapter                        │
│                              │                                           │
│                              ▼                                           │
│  3. Adapter creates/retrieves cached Agent for ENGINEER role             │
│     - Agent configured with system prompt from RoleConfig                │
│     - Model settings (temperature, max_tokens) applied                   │
│                              │                                           │
│                              ▼                                           │
│  4. Runner.run_sync(agent, prompt) executes the agent                    │
│     - SDK handles tool calls, handoffs internally                        │
│     - Session maintains conversation history                             │
│                              │                                           │
│                              ▼                                           │
│  5. Result returned as AgentRunResult with content, metadata             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## OpenAI Agents SDK Overview

The OpenAI Agents SDK is a lightweight framework for building multi-agent workflows. Key concepts:

### Core Concepts

1. **Agents**: LLMs configured with instructions, tools, guardrails, and handoffs
2. **Handoffs**: Specialized tool calls for transferring control between agents
3. **Guardrails**: Input/output validation for safety
4. **Sessions**: Automatic conversation history management
5. **Tracing**: Built-in execution tracking

### Key Features

```python
from agents import Agent, Runner, function_tool, handoff

# Define a simple agent
agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant",
    model="gpt-4",
    tools=[my_tool],
    handoffs=[other_agent],
)

# Run synchronously
result = Runner.run_sync(agent, "Hello!")

# Run asynchronously
result = await Runner.run(agent, "Hello!")
```

### Agent Loop

1. Call LLM with model settings and message history
2. Process response (may include tool calls)
3. If final output (no tools/handoffs), return result
4. If handoff, switch to new agent and continue
5. Process tool calls and continue loop

---

## Integration Design

### Design Principles

1. **Backwards Compatibility**: Existing code using `AgentsBridge` continues to work
2. **Graceful Degradation**: Falls back to Chat API if SDK unavailable
3. **Test Mode Support**: Deterministic responses for CI/testing
4. **Hybrid Mode**: Best of both worlds - SDK with API fallback
5. **Role Preservation**: APEG LLM roles map directly to agents

### Mode Selection

| Mode | Description | Use Case |
|------|-------------|----------|
| `SDK` | OpenAI Agents SDK only | Production with full features |
| `API` | Chat Completions API only | Simple deployments |
| `TEST` | Deterministic responses | CI/CD testing |
| `HYBRID` | SDK with API fallback | Recommended default |

### Role-to-Agent Mapping

| APEG Role | Agent Name | Description |
|-----------|------------|-------------|
| `ENGINEER` | APEG-ENGINEER | Designs prompts, workflows, macro chains |
| `VALIDATOR` | APEG-VALIDATOR | Validates outputs against requirements |
| `SCORER` | APEG-SCORER | Quality evaluation and scoring |
| `CHALLENGER` | APEG-CHALLENGER | Stress-tests and finds flaws |
| `LOGGER` | APEG-LOGGER | Audit logging and compliance |
| `TESTER` | APEG-TESTER | Test case generation |
| `TRANSLATOR` | APEG-TRANSLATOR | Format/language conversion |
| `PEG` | APEG-PEG | Master orchestrator |

---

## Installation and Setup

### Prerequisites

- Python 3.9 or higher
- OpenAI API key
- APEG core package installed

### Installation

```bash
# Install OpenAI Agents SDK
pip install openai-agents

# Or with optional features
pip install 'openai-agents[voice]'    # Voice support
pip install 'openai-agents[redis]'    # Redis sessions
pip install 'openai-agents[litellm]'  # Multi-provider support

# Verify installation
python -c "from agents import Agent, Runner; print('SDK installed successfully')"
```

### Environment Setup

```bash
# Required
export OPENAI_API_KEY=sk-...

# Optional
export APEG_TEST_MODE=false          # Enable test mode
export APEG_USE_AGENTS_SDK=true      # Force SDK mode
export OPENAI_PROJECT_ID=proj_xxx    # Project ID (optional)
```

### APEG Configuration

Update `SessionConfig.json`:

```json
{
  "llm": {
    "mode": "hybrid",
    "use_openai_agents": true,
    "agents_project_id": "proj_xxx",
    "session_dir": ".apeg_sessions",
    "default_model": "gpt-4",
    "test_mode": false
  }
}
```

---

## Usage Guide

### Basic Usage with AgentsBridge (Recommended)

```python
from apeg_core.llm import AgentsBridge, LLMRole

# Initialize bridge
bridge = AgentsBridge({
    "use_openai_agents": True,
    "test_mode": False,
})

# Run a role
result = bridge.run_role(
    role=LLMRole.ENGINEER,
    prompt="Design a workflow for product synchronization",
    context={"source": "Shopify", "target": "Etsy"}
)

print(result["content"])
print(f"Success: {result['success']}")
```

### Direct Adapter Usage

```python
from apeg_core.llm import OpenAIAgentsAdapter, AgentMode, LLMRole

# Initialize adapter
adapter = OpenAIAgentsAdapter(
    config={"session_dir": ".sessions"},
    mode=AgentMode.SDK
)

# Run synchronously
result = adapter.run_agent(
    role=LLMRole.ENGINEER,
    prompt="Design a macro chain",
    context={"task": "seo_optimization"}
)

# Run asynchronously
import asyncio

async def main():
    result = await adapter.run_agent_async(
        role=LLMRole.SCORER,
        prompt="Evaluate this output quality",
        context={"output": "..."},
        session_id="session_123"  # Maintains conversation history
    )
    return result

result = asyncio.run(main())
```

### Using the Scorer Role

```python
# Score an output
result = bridge.run_scorer(
    prompt="Evaluate the quality of this product description",
    output_to_score=product_description,
    scoring_model=scoring_config,
)

print(f"Overall Score: {result.get('overall_score', 0)}")
print(f"Metrics: {result.get('metrics', {})}")
print(f"Feedback: {result.get('feedback', '')}")
```

### Using the Validator Role

```python
# Validate an output
result = bridge.run_validator(
    prompt="Validate this JSON structure",
    output_to_validate=json_output,
    validation_criteria={"schema": "product_schema.json"}
)

print(f"Valid: {result.get('valid', False)}")
print(f"Issues: {result.get('issues', [])}")
```

---

## Configuration Reference

### OpenAIAgentsAdapter Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mode` | str | `"hybrid"` | Execution mode: `sdk`, `api`, `test`, `hybrid` |
| `session_dir` | str | `".apeg_sessions"` | Directory for session databases |
| `openai_api_key` | str | env var | OpenAI API key |
| `default_model` | str | `"gpt-4"` | Default model for agents |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API authentication |
| `APEG_TEST_MODE` | Enable test mode (`true`/`false`) |
| `APEG_USE_AGENTS_SDK` | Force SDK mode (`true`/`false`) |
| `OPENAI_PROJECT_ID` | Optional project ID |

### Role Configuration (RoleConfig)

Each APEG role is configured with:

```python
@dataclass
class RoleConfig:
    name: str              # Role identifier
    description: str       # Human-readable description
    system_prompt: str     # System instructions for LLM
    model: str = "gpt-4"   # Model to use
    temperature: float = 0.7
    max_tokens: int = 2048
    response_format: str = "text"  # "text" or "json"
```

---

## Multi-Agent Workflows

### Creating an Orchestrator with Handoffs

```python
from apeg_core.llm import OpenAIAgentsAdapter, LLMRole

adapter = OpenAIAgentsAdapter()

# Create orchestrator with specialist handoffs
orchestrator = adapter.create_orchestrator_agent(
    name="APEG-Main",
    specialist_roles=[
        LLMRole.ENGINEER,
        LLMRole.VALIDATOR,
        LLMRole.SCORER,
        LLMRole.CHALLENGER,
    ]
)

# The orchestrator will automatically hand off to specialists
# based on the task requirements
```

### Handoff Flow Example

```
User: "Validate this product description and score its quality"
        │
        ▼
┌───────────────────────┐
│   APEG-Orchestrator   │
│  "Analyze task and    │
│   route to specialist"│
└───────────┬───────────┘
            │ handoff
            ▼
┌───────────────────────┐
│   APEG-VALIDATOR      │
│  "Validate structure  │
│   and format"         │
└───────────┬───────────┘
            │ handoff
            ▼
┌───────────────────────┐
│   APEG-SCORER         │
│  "Score quality and   │
│   provide feedback"   │
└───────────────────────┘
            │
            ▼
        Final Result
```

### Custom Multi-Agent Workflow

```python
from agents import Agent, Runner, handoff

# Create specialized agents
engineer = Agent(
    name="Engineer",
    instructions="You design prompts and workflows...",
    handoff_description="For designing solutions",
)

validator = Agent(
    name="Validator",
    instructions="You validate outputs...",
    handoff_description="For validation tasks",
)

scorer = Agent(
    name="Scorer",
    instructions="You score quality...",
    handoff_description="For quality scoring",
)

# Create pipeline agent
pipeline = Agent(
    name="Pipeline",
    instructions="""
    You orchestrate a design-validate-score pipeline:
    1. Hand off to Engineer for initial design
    2. Hand off to Validator to check the design
    3. Hand off to Scorer for final evaluation
    """,
    handoffs=[engineer, validator, scorer],
)

# Execute pipeline
result = Runner.run_sync(pipeline, "Design and validate a product sync workflow")
```

---

## Domain Agent Integration

### Registering Domain Agents as Tools

APEG domain agents (ShopifyAgent, EtsyAgent) can be registered as function tools:

```python
from apeg_core.agents import ShopifyAgent, EtsyAgent
from apeg_core.llm import OpenAIAgentsAdapter, LLMRole

# Initialize domain agents
shopify = ShopifyAgent(config=shopify_config)
etsy = EtsyAgent(config=etsy_config)

# Create adapter and agent
adapter = OpenAIAgentsAdapter()
engineer_agent = adapter.get_or_create_agent(LLMRole.ENGINEER)

# Register domain agents as tools
adapter.register_domain_agent_tools(
    engineer_agent,
    domain_agents=[shopify, etsy]
)

# Now the ENGINEER agent can call Shopify/Etsy operations
result = adapter.run_agent(
    LLMRole.ENGINEER,
    prompt="Sync product inventory between Shopify and Etsy",
    context={"product_id": "123"}
)
```

### Custom Function Tools

```python
from agents import Agent, function_tool

@function_tool
def get_product_data(product_id: str) -> str:
    """Fetch product data from e-commerce platform.

    Args:
        product_id: The product identifier
    """
    # Implementation
    return json.dumps({"id": product_id, "name": "Sample Product"})

@function_tool
def update_inventory(product_id: str, quantity: int) -> str:
    """Update product inventory.

    Args:
        product_id: The product identifier
        quantity: New inventory quantity
    """
    # Implementation
    return json.dumps({"success": True, "new_quantity": quantity})

# Create agent with tools
agent = Agent(
    name="Inventory-Manager",
    instructions="You manage product inventory...",
    tools=[get_product_data, update_inventory],
)
```

---

## Session Management

### Using Sessions for Conversation History

```python
from apeg_core.llm import OpenAIAgentsAdapter

adapter = OpenAIAgentsAdapter(config={"session_dir": ".sessions"})

# First turn
result1 = adapter.run_agent(
    LLMRole.ENGINEER,
    prompt="Design a product sync workflow",
    session_id="session_abc123"
)

# Second turn - agent remembers previous context
result2 = adapter.run_agent(
    LLMRole.ENGINEER,
    prompt="Now add error handling to that workflow",
    session_id="session_abc123"  # Same session
)
```

### Session Options

```python
# SQLite (default) - file-based
from agents import SQLiteSession
session = SQLiteSession("user_123", "conversations.db")

# Redis - for distributed deployments
from agents.extensions.memory import RedisSession
session = RedisSession.from_url("user_123", url="redis://localhost:6379/0")

# Use with Runner
result = await Runner.run(agent, input="...", session=session)
```

### Clearing Session History

```python
# Clear a specific session
adapter.clear_session("session_abc123")
```

---

## Guardrails and Safety

### Input Guardrails

Validate inputs before they reach the agent:

```python
from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner
from pydantic import BaseModel

class TaskValidation(BaseModel):
    is_valid_task: bool
    reasoning: str

guardrail_agent = Agent(
    name="Task-Guardrail",
    instructions="Check if the task is within APEG's scope.",
    output_type=TaskValidation,
)

async def task_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    output = result.final_output_as(TaskValidation)
    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=not output.is_valid_task,
    )

# Apply to agent
main_agent = Agent(
    name="APEG-Main",
    instructions="...",
    input_guardrails=[InputGuardrail(guardrail_function=task_guardrail)],
)
```

### Output Guardrails

Validate agent outputs before returning:

```python
from agents import OutputGuardrail

async def quality_guardrail(ctx, agent, output_data):
    # Check output quality
    score = calculate_quality_score(output_data)
    return GuardrailFunctionOutput(
        output_info={"score": score},
        tripwire_triggered=score < 0.7,  # Block low quality
    )

agent = Agent(
    name="APEG-ENGINEER",
    instructions="...",
    output_guardrails=[OutputGuardrail(guardrail_function=quality_guardrail)],
)
```

---

## Testing and Validation

### Test Mode

Enable test mode for deterministic responses:

```bash
export APEG_TEST_MODE=true
```

Or in code:

```python
adapter = OpenAIAgentsAdapter(config={"test_mode": True})
# or
adapter = OpenAIAgentsAdapter(mode=AgentMode.TEST)
```

### Unit Testing

```python
import pytest
from apeg_core.llm import OpenAIAgentsAdapter, AgentMode, LLMRole

def test_engineer_role_test_mode():
    adapter = OpenAIAgentsAdapter(mode=AgentMode.TEST)

    result = adapter.run_agent(
        LLMRole.ENGINEER,
        "Design a workflow",
        context={"task": "test"}
    )

    assert result.success
    assert result.test_mode
    assert "ENGINEER" in result.content

def test_scorer_role_returns_json():
    adapter = OpenAIAgentsAdapter(mode=AgentMode.TEST)

    result = adapter.run_agent(
        LLMRole.SCORER,
        "Score this output",
        context={"output": "test output"}
    )

    assert result.success
    content = json.loads(result.content)
    assert "overall_score" in content
    assert 0 <= content["overall_score"] <= 1
```

### Integration Testing

```python
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="API key required")
async def test_real_agent_execution():
    adapter = OpenAIAgentsAdapter(mode=AgentMode.SDK)

    result = await adapter.run_agent_async(
        LLMRole.ENGINEER,
        "Say 'Hello, APEG!'"
    )

    assert result.success
    assert not result.test_mode
    assert len(result.content) > 0
```

---

## Migration Guide

### From AgentsBridge to OpenAIAgentsAdapter

**Before (AgentsBridge only):**
```python
from apeg_core.llm import AgentsBridge, LLMRole

bridge = AgentsBridge(config)
result = bridge.run_role(LLMRole.ENGINEER, "prompt", context)
```

**After (with new adapter):**
```python
# Option 1: Continue using AgentsBridge (no changes needed)
from apeg_core.llm import AgentsBridge, LLMRole
bridge = AgentsBridge(config)
result = bridge.run_role(LLMRole.ENGINEER, "prompt", context)

# Option 2: Use adapter directly for more control
from apeg_core.llm import OpenAIAgentsAdapter, AgentMode, LLMRole
adapter = OpenAIAgentsAdapter(mode=AgentMode.SDK)
result = adapter.run_agent(LLMRole.ENGINEER, "prompt", context)
```

### Feature Comparison

| Feature | AgentsBridge | OpenAIAgentsAdapter |
|---------|--------------|---------------------|
| Basic Role Execution | Yes | Yes |
| Session Management | No | Yes |
| Multi-Agent Handoffs | Limited | Full Support |
| Custom Tools | No | Yes |
| Guardrails | No | Yes |
| Async Support | Yes | Yes |
| Test Mode | Yes | Yes |

---

## Troubleshooting

### Common Issues

#### SDK Not Installed

```
Error: OpenAI Agents SDK not installed
Solution: pip install openai-agents
```

#### API Key Not Set

```
Error: OPENAI_API_KEY not set
Solution: export OPENAI_API_KEY=sk-...
```

#### Rate Limiting

```
Error: Rate limit exceeded
Solution: Implement exponential backoff or reduce request frequency
```

#### Session Database Locked

```
Error: Database is locked
Solution: Use separate session directories or switch to Redis sessions
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.getLogger("openai.agents").setLevel(logging.DEBUG)

# Or use SDK's built-in verbose logging
from agents import enable_verbose_stdout_logging
enable_verbose_stdout_logging()
```

### Viewing Traces

The SDK automatically traces agent runs. View traces at:
https://platform.openai.com/traces

---

## Future Roadmap

### Phase 9: Self-Improvement Integration

- Feedback ingestion from agent execution history
- Automatic prompt tuning suggestions
- Performance analytics and optimization

### Planned Enhancements

1. **Tracing Integration**: Connect SDK tracing to APEG Logbook
2. **Multi-Provider Support**: Add LiteLLM for Claude, Gemini, etc.
3. **Advanced Guardrails**: PII detection, content filtering
4. **Workflow Templates**: Pre-built agent workflows for common tasks
5. **Dashboard**: Web UI for monitoring agent execution
6. **Voice Support**: Audio input/output for agents

### Hybrid Orchestration Options

The integration supports pivoting between:

| Option | Use Case |
|--------|----------|
| **OpenAI Agents SDK** | Primary multi-agent workflows |
| **LangGraph** | Complex state machines |
| **AutoGen** | Research and experimentation |
| **Custom Graph** | APEG WorkflowGraph.json |

The adapter design allows easy switching between these options.

---

## References

### Official Documentation

- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [OpenAI Agents GitHub](https://github.com/openai/openai-agents-python)
- [OpenAI API Documentation](https://platform.openai.com/docs)

### APEG Documentation

- [ADR-001: OpenAI Agents as Primary LLM Runtime](ADRS/ADR-001-OpenAI-Agents.md)
- [APEG Phase 8 Requirements](APEG_PHASE_8_REQUIREMENTS.md)
- [APEG Phase 9 Requirements](APEG_PHASE_9_REQUIREMENTS.md)
- [Next Steps](Next_Steps.md)

### Code References

- `src/apeg_core/llm/openai_agents_adapter.py` - Main adapter implementation
- `src/apeg_core/llm/agent_bridge.py` - Bridge facade
- `src/apeg_core/llm/roles.py` - Role definitions

### External Resources

- [Pydantic AI](https://ai.pydantic.dev/) - Advanced agent framework
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-provider support
- [Temporal](https://temporal.io/) - Long-running workflows

---

**Document Status:** Active
**Last Updated:** 2025-11-23
**Author:** APEG Development Team
