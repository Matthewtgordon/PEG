# OpenAI Agents SDK Integration Guide

Complete guide to using OpenAI Agents SDK with APEG.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [Core Components](#core-components)
6. [API Reference](#api-reference)
7. [Examples](#examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The APEG-SDK integration provides bidirectional compatibility between:

- **APEG's domain agents** (Shopify, Etsy) with Thompson Sampling orchestration
- **OpenAI Agents SDK** for LLM-driven multi-agent workflows with handoffs

### Key Features

- Wrap APEG agents as SDK agents with automatic tool generation
- Use SDK agents within APEG orchestrator
- Agent handoffs between APEG and SDK agents
- Preserve all existing APEG functionality
- Test mode for development without API calls

## Installation

### Method 1: pip (Recommended)

```bash
pip install openai-agents --break-system-packages
```

### Verify Installation

```python
from agents import Agent, Runner, function_tool
print("SDK installed successfully")
```

## Architecture

```
+------------------------------------------+
|         APEG Orchestrator                |
|  (Thompson Sampling, MCTS, Workflows)    |
+--------------------+---------------------+
                     |
         +-----------+------------+
         |                        |
         v                        v
   APEG Agents               SDK Agents
   (Direct)                  (via Adapters)
   - Shopify                 - LLM Conversations
   - Etsy                    - Handoffs
   - Custom                  - Sessions

+------------------------------------------+
|      SDK Integration Layer               |
|  - APEGAgentAdapter (APEG -> SDK)        |
|  - SDKAgentWrapper (SDK -> APEG)         |
|  - ToolBridge (methods -> tools)         |
|  - HandoffCoordinator (transitions)      |
+------------------------------------------+
```

## Quick Start

### 1. Wrap APEG Agent as SDK Agent

```python
from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.sdk_integration import APEGAgentAdapter
from agents import Runner

# Create APEG agent
shopify = ShopifyAgent(config={"test_mode": True})

# Wrap as SDK agent
adapter = APEGAgentAdapter(shopify)
sdk_agent = adapter.to_sdk_agent()

# Use with SDK Runner
result = Runner.run_sync(sdk_agent, "List products")
print(result.final_output)
```

### 2. Use SDK Agent in APEG

```python
from agents import Agent
from apeg_core.sdk_integration import SDKAgentWrapper

# Create SDK agent
customer_service = Agent(
    name="CustomerService",
    instructions="You are a helpful customer service agent."
)

# Wrap for APEG compatibility
wrapped = SDKAgentWrapper(customer_service, config={"test_mode": True})

# Use APEG interface
result = wrapped.execute("inquiry", {"prompt": "Help me with my order"})
```

### 3. Multi-Agent Handoffs with Coordinator

```python
from apeg_core.sdk_integration import HandoffCoordinator
from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.agents.etsy_agent import EtsyAgent

# Create coordinator
coordinator = HandoffCoordinator()

# Register agents
coordinator.register_apeg_agent("shopify", ShopifyAgent(config={"test_mode": True}))
coordinator.register_apeg_agent("etsy", EtsyAgent(config={"test_mode": True}))

# Create triage agent
triage = coordinator.create_triage_agent(
    name="E-commerce Router",
    instructions="Route requests to Shopify or Etsy based on platform mentioned"
)
```

## Core Components

### ToolBridge

Converts APEG agent methods to SDK function tools:

```python
from apeg_core.sdk_integration import ToolBridge

bridge = ToolBridge(shopify_agent)
tools = bridge.create_tools()  # List of SDK function tools

# Filter specific methods
tools = bridge.create_tools(
    method_filter=lambda name: name in ['list_products', 'get_product']
)
```

### APEGAgentAdapter

Wraps APEG BaseAgent as OpenAI SDK Agent:

```python
from apeg_core.sdk_integration import APEGAgentAdapter

adapter = APEGAgentAdapter(
    apeg_agent=shopify_agent,
    instructions="Handle Shopify operations",  # Optional custom instructions
    method_filter=lambda n: n.startswith('list')  # Optional filter
)

sdk_agent = adapter.to_sdk_agent()
```

### SDKAgentWrapper

Makes SDK agents APEG-compatible:

```python
from apeg_core.sdk_integration import SDKAgentWrapper

wrapper = SDKAgentWrapper(sdk_agent, config={"test_mode": True})

# Use APEG interface
result = wrapper.execute(action="task", context={"prompt": "Do something"})
capabilities = wrapper.describe_capabilities()
```

### HandoffCoordinator

Manages agent registration and handoffs:

```python
from apeg_core.sdk_integration import HandoffCoordinator

coordinator = HandoffCoordinator()

# Register agents
coordinator.register_apeg_agent("name", agent, instructions="...")
coordinator.register_sdk_agent("name", sdk_agent)

# Create triage
triage = coordinator.create_triage_agent(name="Router")

# Manage context
coordinator.set_context("key", "value")
coordinator.get_context("key")
```

## API Reference

### APEGAgentAdapter

```python
APEGAgentAdapter(
    apeg_agent: BaseAgent,
    instructions: Optional[str] = None,
    handoffs: Optional[List[Agent]] = None,
    method_filter: Optional[Callable[[str], bool]] = None
)
```

**Methods:**
- `to_sdk_agent() -> Agent`: Create SDK agent from APEG agent
- `create_with_handoffs(adapters: List[APEGAgentAdapter]) -> Agent`: Create with handoffs
- `get_capabilities() -> List[str]`: Get agent capabilities

### SDKAgentWrapper

```python
SDKAgentWrapper(
    sdk_agent: Agent,
    config: Optional[Dict[str, Any]] = None
)
```

**Methods:**
- `execute(action: str, context: Dict) -> Dict`: Execute task (APEG interface)
- `describe_capabilities() -> List[str]`: List capabilities
- `name` property: Agent name

### ToolBridge

```python
ToolBridge(apeg_agent: BaseAgent)
```

**Methods:**
- `create_tools(method_filter: Optional[Callable]) -> List`: Generate SDK tools
- `get_method_schemas() -> List[Dict]`: Get method schema info

### HandoffCoordinator

```python
HandoffCoordinator()
```

**Methods:**
- `register_apeg_agent(name, agent, instructions) -> APEGAgentAdapter`
- `register_sdk_agent(name, agent) -> None`
- `get_agent(name) -> Optional[Agent]`
- `get_adapter(name) -> Optional[APEGAgentAdapter]`
- `create_triage_agent(name, instructions, include_agents) -> Agent`
- `set_context(key, value) -> None`
- `get_context(key, default) -> Any`
- `clear_context() -> None`
- `describe() -> Dict`

## Examples

See `examples/openai_sdk/` directory:

1. **basic_adapter.py** - Simple APEG to SDK conversion
2. **multi_agent_handoff.py** - Agent handoffs and routing
3. **mixed_workflow.py** - Combined APEG + SDK workflows

Run examples:

```bash
cd /path/to/PEG
python3 examples/openai_sdk/basic_adapter.py
python3 examples/openai_sdk/multi_agent_handoff.py
python3 examples/openai_sdk/mixed_workflow.py
```

## Best Practices

### 1. Use Test Mode for Development

```python
shopify = ShopifyAgent(config={"test_mode": True})
wrapper = SDKAgentWrapper(sdk_agent, config={"test_mode": True})
```

### 2. Filter Methods Carefully

Not all agent methods should become tools:

```python
adapter = APEGAgentAdapter(
    agent,
    method_filter=lambda name: name in ['list_products', 'get_product']
)
```

### 3. Provide Clear Instructions

```python
adapter = APEGAgentAdapter(
    shopify,
    instructions="You manage Shopify inventory. Check stock before orders."
)
```

### 4. Handle Errors Gracefully

```python
result = wrapper.execute(action, context)
if result['status'] == 'failed':
    print(f"Error: {result.get('error')}")
```

### 5. Use HandoffCoordinator for Multi-Agent

```python
coordinator = HandoffCoordinator()
coordinator.register_apeg_agent("shopify", shopify_agent)
coordinator.register_apeg_agent("etsy", etsy_agent)
triage = coordinator.create_triage_agent()
```

## Troubleshooting

### Import Errors

```python
# SDK should be installed via pip
from agents import Agent, Runner

# If not installed:
# pip install openai-agents --break-system-packages
```

### Tool Generation Warnings

Some methods with complex types (Dict, List) may show Pydantic warnings:
- These methods are skipped during tool generation
- Other methods work normally
- Use `method_filter` to explicitly include/exclude methods

### Test Mode

Test mode returns stub responses without real API calls:
- Set `test_mode=True` in agent config
- Useful for development and testing
- No OpenAI API key required

### API Key

For real LLM calls, set environment variable:

```bash
export OPENAI_API_KEY="your-key-here"
```

## Further Reading

- [OpenAI Agents SDK Documentation](https://openai.github.io/openai-agents-python/)
- [APEG Architecture](../CLAUDE.md)
- [Example Code](../examples/openai_sdk/)
