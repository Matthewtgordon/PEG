# APEG MCP Integration Guide

**Version:** 1.0.0 (Experimental)
**Last Updated:** 2025-11-20
**Status:** EXPERIMENTAL - Not Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [What is MCP?](#what-is-mcp)
3. [Use Cases](#use-cases)
4. [Configuration](#configuration)
5. [WorkflowGraph Integration](#workflowgraph-integration)
6. [Code Examples](#code-examples)
7. [Testing](#testing)
8. [Limitations](#limitations)
9. [Future Roadmap](#future-roadmap)

---

## Overview

This guide explains how to integrate **Model Context Protocol (MCP)** servers with APEG workflows. MCP enables dynamic tool discovery and execution, allowing APEG to call external services and tools defined by MCP servers.

### Current Status

- **Implementation:** Stub implementation with test mode support
- **Production Readiness:** NOT READY - experimental only
- **Required Library:** `langgraph-mcp` (not yet integrated)
- **Test Mode:** Fully functional with mock responses

### Important Warnings

⚠️ **EXPERIMENTAL FEATURE**
This integration is in early stages and should NOT be used in production without:
- Full integration of the `langgraph-mcp` library
- Comprehensive security review
- Production testing and hardening

---

## What is MCP?

**Model Context Protocol (MCP)** is a protocol for:
- Discovering tools available on remote servers
- Executing tools with structured parameters
- Receiving structured responses
- Enabling dynamic workflows based on available tools

### Architecture

```
┌─────────────────┐
│  APEG Workflow  │
│   Orchestrator  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   MCP Client    │
│   (apeg_core/   │
│   connectors)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   MCP Server    │
│  (External)     │
│   - Tools       │
│   - Resources   │
└─────────────────┘
```

---

## Use Cases

### 1. Dynamic Data Processing
Call external data processing tools without hardcoding integrations.

### 2. Multi-Service Orchestration
Coordinate actions across multiple external services via MCP.

### 3. Plugin Ecosystem
Build a plugin system where MCP servers provide specialized capabilities.

### 4. Testing and Mocking
Use test mode to simulate external tool calls for development.

---

## Configuration

### SessionConfig.json

Add MCP server configuration to your `SessionConfig.json`:

```json
{
  "mcp": {
    "servers": {
      "default": "http://localhost:8080",
      "data_processor": "http://localhost:8081",
      "ai_tools": "https://api.example.com/mcp"
    },
    "timeout": 30
  }
}
```

**Configuration Options:**
- `servers`: Dictionary mapping server IDs to URLs
- `timeout`: Request timeout in seconds (default: 30)

### Environment Variables

```bash
# Enable test mode (uses mock responses)
APEG_TEST_MODE=true

# Debug logging
APEG_DEBUG=true
```

---

## WorkflowGraph Integration

### Node Definition

Add MCP tool nodes to `WorkflowGraph.json`:

```json
{
  "nodes": [
    {
      "id": "mcp_data_fetch",
      "label": "Fetch Data via MCP",
      "type": "mcp_tool",
      "agent": "PEG",
      "mcp_config": {
        "server": "default",
        "tool_name": "fetch_data",
        "input_mapping": {
          "query": "context.user_query",
          "limit": "context.result_limit"
        },
        "output_mapping": {
          "fetched_data": "result.data",
          "status": "result.status"
        }
      }
    }
  ]
}
```

### Node Type: `mcp_tool`

**Required Fields:**
- `type`: Must be `"mcp_tool"`
- `mcp_config`: MCP-specific configuration

**MCP Config Fields:**
- `server`: Server ID from `SessionConfig.json` servers dict
- `tool_name`: Name of the tool to invoke
- `input_mapping`: Maps workflow state to tool parameters
- `output_mapping`: Maps tool results to workflow state

### Input Mapping

Maps workflow state values to tool parameters:

```json
"input_mapping": {
  "param_name": "state.path.to.value"
}
```

**Examples:**
- `"context.user_input"` → workflow state["context"]["user_input"]
- `"output"` → workflow state["output"]
- `"config.api_key"` → workflow state["config"]["api_key"]

### Output Mapping

Maps tool result values to workflow state:

```json
"output_mapping": {
  "state_key": "result.path.to.value"
}
```

**Examples:**
- `"mcp_result": "result.output"` → state["mcp_result"] = result["result"]["output"]
- `"status": "result.status"` → state["status"] = result["result"]["status"]

---

## Code Examples

### Example 1: Basic MCP Client Usage

```python
from apeg_core.connectors.mcp_client import MCPClient, MCPClientError
import os

# Set test mode for development
os.environ["APEG_TEST_MODE"] = "true"

# Initialize client
config = {
    "servers": {
        "default": "http://localhost:8080"
    },
    "timeout": 30
}

client = MCPClient(config)

# Discover available tools
try:
    tools = client.discover_tools(server="default")
    for tool in tools:
        print(f"Tool: {tool['name']}")
        print(f"  Description: {tool['description']}")
        print(f"  Parameters: {tool['parameters']}")
except MCPClientError as e:
    print(f"Error: {e}")

# Call a tool
try:
    result = client.call_tool(
        server="default",
        tool="example_tool",
        params={"input": "test data"}
    )
    print(f"Result: {result}")
except MCPClientError as e:
    print(f"Error: {e}")
```

### Example 2: Full Workflow with MCP Node

**WorkflowGraph.json:**

```json
{
  "nodes": [
    {
      "id": "intake",
      "type": "start",
      "agent": "PEG"
    },
    {
      "id": "mcp_process",
      "type": "mcp_tool",
      "agent": "PEG",
      "mcp_config": {
        "server": "data_processor",
        "tool_name": "process_data",
        "input_mapping": {
          "data": "raw_data",
          "operation": "transform_type"
        },
        "output_mapping": {
          "processed_data": "result.output",
          "metadata": "result.metadata"
        }
      }
    },
    {
      "id": "export",
      "type": "end",
      "agent": "PEG"
    }
  ],
  "edges": [
    { "from": "intake", "to": "mcp_process" },
    { "from": "mcp_process", "to": "export" }
  ]
}
```

**Python Execution:**

```python
from apeg_core import APEGOrchestrator
import json

# Load configs
with open("SessionConfig.json") as f:
    session_config = json.load(f)

with open("WorkflowGraph.json") as f:
    workflow_graph = json.load(f)

# Initialize orchestrator
orch = APEGOrchestrator(session_config, workflow_graph)

# Set initial state
orch.state["raw_data"] = [1, 2, 3, 4, 5]
orch.state["transform_type"] = "square"

# Execute workflow
orch.execute_graph()

# Check results
print(f"Processed data: {orch.state.get('processed_data')}")
print(f"Metadata: {orch.state.get('metadata')}")
```

### Example 3: Error Handling

```python
from apeg_core.connectors.mcp_client import MCPClient, MCPClientError

client = MCPClient(config={
    "servers": {"default": "http://localhost:8080"}
})

try:
    result = client.call_tool(
        server="default",
        tool="risky_tool",
        params={"input": "test"}
    )
    print(f"Success: {result}")

except MCPClientError as e:
    # Handle MCP-specific errors
    print(f"MCP Error: {e}")
    # Fallback logic here

except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")
```

---

## Testing

### Test Mode

Set `APEG_TEST_MODE=true` to use mock responses:

```bash
export APEG_TEST_MODE=true
python -m apeg_core
```

**Test mode behavior:**
- All MCP calls return deterministic mock data
- No actual network requests are made
- Useful for unit tests and development

### Unit Testing MCP Nodes

```python
import pytest
from apeg_core import APEGOrchestrator
import os

def test_mcp_node_execution():
    """Test MCP node in test mode."""
    os.environ["APEG_TEST_MODE"] = "true"

    config = {
        "mcp": {
            "servers": {"default": "http://localhost:8080"}
        }
    }

    workflow = {
        "nodes": [
            {
                "id": "test_mcp",
                "type": "mcp_tool",
                "mcp_config": {
                    "server": "default",
                    "tool_name": "test_tool",
                    "input_mapping": {"input": "test_input"},
                    "output_mapping": {"result": "result.output"}
                }
            }
        ],
        "edges": []
    }

    orch = APEGOrchestrator(config, workflow)
    orch.state["test_input"] = "test data"

    # Execute node
    node = workflow["nodes"][0]
    result = orch._execute_node(node)

    assert result["action_result"] == "success"
    assert "result" in orch.state
```

---

## Limitations

### Current Implementation

1. **Not Production Ready**
   - Stub implementation only
   - No real MCP library integration
   - Limited error handling

2. **Test Mode Only**
   - Real MCP calls will raise `MCPClientError`
   - Must use `APEG_TEST_MODE=true` for development

3. **Simple Path Resolution**
   - Only supports dot-notation paths
   - No array indexing or advanced queries

4. **No Authentication**
   - MCP server authentication not implemented
   - Security concerns for production use

5. **No Retry Logic**
   - Failed MCP calls do not retry automatically
   - No circuit breaker pattern

### Security Considerations

⚠️ **Before Production Use:**

- [ ] Implement MCP server authentication
- [ ] Add TLS/SSL verification
- [ ] Implement request signing
- [ ] Add rate limiting
- [ ] Sanitize all inputs and outputs
- [ ] Audit MCP server endpoints
- [ ] Set up network isolation

---

## Future Roadmap

### Phase 8.8.1: Library Integration (Q1 2026)
- Integrate `langgraph-mcp` library
- Implement real MCP protocol communication
- Add authentication support

### Phase 8.8.2: Enhanced Features (Q2 2026)
- Advanced path resolution (array indexing, filters)
- Retry logic with exponential backoff
- Circuit breaker pattern
- MCP server health monitoring

### Phase 8.8.3: Production Hardening (Q3 2026)
- Security audit and hardening
- TLS certificate validation
- Request/response logging
- Performance optimization
- Comprehensive test suite

---

## Troubleshooting

### Error: "MCP library not installed"

**Solution:**
```bash
# Enable test mode for development
export APEG_TEST_MODE=true

# Or wait for langgraph-mcp integration
```

### Error: "Server 'xyz' not configured"

**Solution:** Add server to `SessionConfig.json`:
```json
{
  "mcp": {
    "servers": {
      "xyz": "http://localhost:8080"
    }
  }
}
```

### Error: "Context path 'x.y.z' not found"

**Solution:** Ensure the path exists in workflow state:
```python
orch.state["x"] = {"y": {"z": "value"}}
```

---

## References

- **APEG Phase 8 Requirements:** `docs/APEG_PHASE_8_REQUIREMENTS.md`
- **Orchestrator Source:** `src/apeg_core/orchestrator.py`
- **MCP Client Source:** `src/apeg_core/connectors/mcp_client.py`
- **WorkflowGraph Schema:** `WorkflowGraph.json`

---

## Support

For questions or issues:
1. Check `docs/APEG_STATUS.md` for current implementation status
2. Review test files in `tests/` for examples
3. File issues at: https://github.com/Matthewtgordon/PEG/issues

**Remember:** This is an EXPERIMENTAL feature. Use test mode only until production integration is complete.
