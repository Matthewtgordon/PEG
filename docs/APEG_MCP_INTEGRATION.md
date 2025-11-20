# APEG MCP Integration Guide

**Version:** 1.0.0
**Date:** 2025-11-20
**Status:** EXPERIMENTAL - Test Mode Only

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [WorkflowGraph Integration](#workflowgraph-integration)
5. [MCP Client API](#mcp-client-api)
6. [Code Examples](#code-examples)
7. [Testing](#testing)
8. [Limitations](#limitations)
9. [Security Considerations](#security-considerations)
10. [Troubleshooting](#troubleshooting)
11. [Future Roadmap](#future-roadmap)

---

## Overview

This document explains how to integrate **Model Context Protocol (MCP)** servers with APEG workflows. MCP enables APEG to call external tools and services without coupling core runtime logic to specific implementations.

### What is MCP?

Model Context Protocol is a standardized protocol for:
- Discovering tools available on remote servers
- Executing tools with structured parameters
- Receiving structured responses
- Enabling dynamic workflows based on available capabilities

### Current Status

- **Implementation:** Fully functional in test mode
- **Production Readiness:** NOT READY - requires `langgraph-mcp` library integration
- **Test Mode:** Returns deterministic mock data
- **Real Mode:** Requires `langgraph-mcp` installation (not yet integrated)

### Important Warnings

⚠️ **EXPERIMENTAL FEATURE**

This integration is in early stages and should NOT be used in production without:
- Full integration of the `langgraph-mcp` library
- Comprehensive security review
- Authentication and authorization implementation
- Production testing and hardening

---

## Architecture

### Component Overview

```
┌─────────────────┐
│  Orchestrator   │
│  (workflow)     │
└────────┬────────┘
         │
         │ (mcp_tool node)
         ▼
┌─────────────────┐
│   MCPClient     │
│  (connector)    │
└────────┬────────┘
         │
         ├─ Test Mode ──► Mock Responses
         │
         └─ Real Mode ──► langgraph-mcp ──► MCP Server
```

### Key Components

1. **MCPClient** (`src/apeg_core/connectors/mcp_client.py`)
   - Abstraction layer for MCP protocol
   - Test mode support with mock data
   - Graceful fallback if library not available

2. **Orchestrator** (`src/apeg_core/orchestrator.py`)
   - Executes `mcp_tool` node type
   - Maps workflow state to tool parameters
   - Maps tool results back to workflow state

3. **WorkflowGraph** (`WorkflowGraph.json`)
   - Defines MCP tool nodes
   - Specifies input/output mappings
   - Documents MCP node schema

---

## Configuration

### SessionConfig.json

Add MCP configuration to your SessionConfig:

```json
{
  "mcp": {
    "server_url": "http://localhost:3000",
    "timeout": 30,
    "retry_count": 2
  }
}
```

**Configuration Options:**

- `server_url`: Base URL for MCP server (default: `http://localhost:3000`)
- `timeout`: Request timeout in seconds (default: `30`)
- `retry_count`: Number of retries on failure (default: `2`)

### Environment Variables

- `APEG_TEST_MODE`: If `true`, always use mock mode (default: `true`)
- `MCP_SERVER_URL`: Override default MCP server URL

**Example:**

```bash
export APEG_TEST_MODE=true
export MCP_SERVER_URL=http://mcp.example.com:8080
```

---

## WorkflowGraph Integration

### MCP Node Structure

```json
{
  "id": "my_mcp_node",
  "type": "mcp_tool",
  "description": "Description of what this node does",
  "mcp_config": {
    "server": "server_identifier",
    "tool_name": "tool_to_invoke",
    "input_mapping": {
      "tool_param": "state_key"
    },
    "output_mapping": {
      "state_key": "result.path"
    }
  }
}
```

**Field Definitions:**

- `type`: Must be `"mcp_tool"`
- `server`: MCP server identifier (e.g., `filesystem`, `web_search`, `database`)
- `tool_name`: Name of tool to invoke
- `input_mapping`: Maps workflow state to tool parameters
- `output_mapping`: Maps tool response to workflow state

### Input Mapping

Maps workflow state keys to tool parameters.

**Format:** `"tool_parameter": "state_key"`

**Example:**

```json
"input_mapping": {
  "path": "file_path",
  "query": "search_query"
}
```

If `state["file_path"] = "/tmp/test.txt"`, tool receives:
```json
{
  "path": "/tmp/test.txt"
}
```

### Output Mapping

Maps tool response to workflow state using dot notation.

**Format:** `"state_key": "result.nested.path"`

**Example:**

```json
"output_mapping": {
  "file_content": "result.content",
  "file_size": "result.size"
}
```

If tool returns:
```json
{
  "success": true,
  "result": {
    "content": "Hello World",
    "size": 11
  }
}
```

State receives:
```python
state["file_content"] = "Hello World"
state["file_size"] = 11
```

### Example Nodes

#### Filesystem Read

```json
{
  "id": "read_config",
  "type": "mcp_tool",
  "description": "Read configuration file",
  "mcp_config": {
    "server": "filesystem",
    "tool_name": "read_file",
    "input_mapping": {
      "path": "config_path"
    },
    "output_mapping": {
      "config_data": "result.content"
    }
  }
}
```

#### Web Search

```json
{
  "id": "search_docs",
  "type": "mcp_tool",
  "description": "Search documentation",
  "mcp_config": {
    "server": "web_search",
    "tool_name": "search",
    "input_mapping": {
      "query": "search_query"
    },
    "output_mapping": {
      "search_results": "result.results"
    }
  }
}
```

#### Database Query

```json
{
  "id": "fetch_data",
  "type": "mcp_tool",
  "description": "Query database",
  "mcp_config": {
    "server": "database",
    "tool_name": "query",
    "input_mapping": {
      "sql": "query_string"
    },
    "output_mapping": {
      "query_results": "result.rows"
    }
  }
}
```

---

## MCP Client API

### Importing

```python
from apeg_core.connectors.mcp_client import MCPClient, MCP_AVAILABLE
```

### Initialization

```python
# Default configuration
client = MCPClient()

# Custom configuration
client = MCPClient(config={
    "server_url": "http://localhost:3000",
    "timeout": 30,
    "retry_count": 2
})
```

### Calling Tools

```python
result = client.call_tool(
    server="filesystem",
    tool="read_file",
    params={"path": "/tmp/test.txt"}
)

if result["success"]:
    print(f"File content: {result['result']['content']}")
else:
    print(f"Error: {result['error']}")
```

### Response Format

**Success:**
```python
{
    "success": True,
    "result": {
        # Tool-specific response data
    },
    "error": None
}
```

**Failure:**
```python
{
    "success": False,
    "result": None,
    "error": "Error message"
}
```

### Checking Library Availability

```python
from apeg_core.connectors.mcp_client import MCP_AVAILABLE

if MCP_AVAILABLE:
    print("langgraph-mcp is installed")
else:
    print("Running in mock mode")
```

---

## Code Examples

### Example 1: Simple Workflow with MCP

```python
from apeg_core import APEGOrchestrator

# Define workflow
workflow = {
    "nodes": [
        {
            "id": "start",
            "type": "process",
            "agent": "PEG",
            "action": "Initialize"
        },
        {
            "id": "read_file",
            "type": "mcp_tool",
            "mcp_config": {
                "server": "filesystem",
                "tool_name": "read_file",
                "input_mapping": {
                    "path": "file_path"
                },
                "output_mapping": {
                    "file_content": "result.content"
                }
            }
        },
        {
            "id": "end",
            "type": "process",
            "agent": "PEG",
            "action": "Complete"
        }
    ],
    "edges": [
        {"from": "start", "to": "read_file"},
        {"from": "read_file", "to": "end"}
    ],
    "entry_point": "start"
}

# Create orchestrator
config = {"mcp": {"server_url": "http://localhost:3000"}}
orchestrator = APEGOrchestrator(
    config_path=config,
    workflow_graph_path=workflow
)

# Set initial state
orchestrator.state["file_path"] = "/tmp/config.json"

# Execute
orchestrator.execute_graph()

# Check results
if "file_content" in orchestrator.state:
    print(f"Success: {orchestrator.state['file_content']}")
elif "_mcp_error" in orchestrator.state:
    print(f"Error: {orchestrator.state['_mcp_error']}")
```

### Example 2: Direct MCP Client Usage

```python
from apeg_core.connectors.mcp_client import MCPClient

# Initialize client
client = MCPClient(config={"server_url": "http://localhost:3000"})

# Call filesystem tool
result = client.call_tool(
    server="filesystem",
    tool="read_file",
    params={"path": "/tmp/test.txt"}
)

print(f"Success: {result['success']}")
print(f"Content: {result['result']['content']}")

# Call web search tool
result = client.call_tool(
    server="web_search",
    tool="search",
    params={"query": "APEG documentation"}
)

if result["success"]:
    for item in result["result"]["results"]:
        print(f"- {item['title']}: {item['url']}")
```

### Example 3: Error Handling

```python
from apeg_core import APEGOrchestrator

# Workflow with error handling
workflow = {
    "nodes": [
        {
            "id": "mcp_call",
            "type": "mcp_tool",
            "mcp_config": {
                "server": "filesystem",
                "tool_name": "read_file",
                "input_mapping": {"path": "file_path"},
                "output_mapping": {"content": "result.content"}
            }
        },
        {
            "id": "handle_success",
            "type": "process",
            "agent": "PEG",
            "action": "Process content"
        },
        {
            "id": "handle_error",
            "type": "process",
            "agent": "PEG",
            "action": "Log error"
        }
    ],
    "edges": [
        {"from": "mcp_call", "to": "handle_success", "condition": "success"},
        {"from": "mcp_call", "to": "handle_error", "condition": "mcp_failed"}
    ],
    "entry_point": "mcp_call"
}

orchestrator = APEGOrchestrator(
    config_path={"mcp": {}},
    workflow_graph_path=workflow
)

orchestrator.state["file_path"] = "/tmp/test.txt"
orchestrator.execute_graph()

# Check error
if "_mcp_error" in orchestrator.state:
    print(f"MCP Error: {orchestrator.state['_mcp_error']}")
```

---

## Testing

### Running Tests

```bash
# Unit tests
APEG_TEST_MODE=true pytest tests/test_mcp_client.py -v

# Integration tests
APEG_TEST_MODE=true pytest tests/test_mcp_integration.py -v

# All MCP tests
APEG_TEST_MODE=true pytest tests/test_mcp*.py -v
```

### Test Mode Behavior

When `APEG_TEST_MODE=true`:
- MCP client returns mock data
- No real network calls are made
- Deterministic responses for testing

**Mock Responses:**

- **filesystem.read_file**: Returns `"Mock file content"`
- **filesystem.write_file**: Returns success with 123 bytes written
- **web_search.search**: Returns one mock search result
- **database.query**: Returns two mock rows
- **unknown tools**: Returns generic mock data

### Writing Tests

```python
import pytest
import os
from apeg_core.connectors.mcp_client import MCPClient

@pytest.fixture
def test_mode():
    """Ensure test mode."""
    original = os.environ.get("APEG_TEST_MODE")
    os.environ["APEG_TEST_MODE"] = "true"
    yield
    if original:
        os.environ["APEG_TEST_MODE"] = original
    else:
        os.environ.pop("APEG_TEST_MODE", None)

def test_mcp_call(test_mode):
    """Test MCP call in test mode."""
    client = MCPClient()
    result = client.call_tool("filesystem", "read_file", {"path": "/test"})

    assert result["success"] is True
    assert "content" in result["result"]
```

---

## Limitations

### Current Limitations

1. **No Real MCP Library Integration**
   - `langgraph-mcp` not yet integrated
   - Real MCP calls will fail
   - Only test mode works

2. **No Authentication**
   - MCP servers must be publicly accessible
   - No API key or token support
   - Security risk in production

3. **Limited Error Handling**
   - Network errors may not be handled gracefully
   - No circuit breaker for repeated failures
   - No rate limiting

4. **No Tool Discovery**
   - Cannot query available tools from server
   - Must know tool names in advance
   - No schema validation

5. **Simplistic State Mapping**
   - Only supports dot notation for nested paths
   - No complex transformations
   - No conditional mapping

### Known Issues

- **Issue:** `langgraph-mcp` import fails
  - **Impact:** Real MCP calls not possible
  - **Workaround:** Use test mode
  - **Status:** Expected, integration pending

- **Issue:** Errors stored in `state["_mcp_error"]` may be overwritten
  - **Impact:** Only last error is available
  - **Workaround:** Check error after each MCP node
  - **Status:** Design limitation

---

## Security Considerations

### Authentication

⚠️ **CRITICAL:** MCP integration currently has NO authentication.

**DO NOT:**
- Expose MCP servers to public internet
- Use MCP in production without authentication
- Store sensitive data in MCP server responses

**Recommended:**
- Implement API key authentication
- Use VPN or private network for MCP servers
- Encrypt sensitive data in transit (HTTPS)

### Input Validation

- MCP client does not validate tool parameters
- Orchestrator does not sanitize state values
- Risk of injection attacks if state contains user input

**Mitigation:**
- Validate all inputs before mapping to MCP parameters
- Sanitize user input in workflow nodes before MCP calls
- Use allowlists for server and tool names

### Network Security

- MCP client makes HTTP requests to external servers
- No certificate validation implemented
- Vulnerable to man-in-the-middle attacks

**Mitigation:**
- Use HTTPS for all MCP communication
- Implement certificate pinning
- Run MCP servers on private network

---

## Troubleshooting

### MCP Client Not Working

**Symptom:** MCP calls always return mock data

**Causes:**
1. `APEG_TEST_MODE=true` (expected behavior)
2. `langgraph-mcp` not installed
3. MCP server not running

**Solutions:**
1. Check `APEG_TEST_MODE` environment variable
2. Install library: `pip install langgraph-mcp` (when available)
3. Verify MCP server is running: `curl http://localhost:3000/health`

### State Mapping Not Working

**Symptom:** Output values not appearing in state

**Causes:**
1. Incorrect `output_mapping` path
2. Tool response structure different than expected
3. State key name collision

**Solutions:**
1. Check tool response format in logs
2. Verify `result.` prefix in output paths
3. Use unique state keys

### MCP Node Always Fails

**Symptom:** `action_result = "mcp_failed"`

**Causes:**
1. Missing or invalid `mcp_config`
2. Server identifier not recognized
3. Tool name incorrect

**Solutions:**
1. Check node has `type: "mcp_tool"` and complete `mcp_config`
2. Verify server name matches available servers
3. Check tool name spelling

### Error Stored in State

**Symptom:** `state["_mcp_error"]` contains error message

**Cause:** MCP call failed

**Solutions:**
1. Check error message for details
2. Verify input parameters are correct
3. Check MCP server logs
4. Ensure server and tool exist

---

## Future Roadmap

### Phase 1: Library Integration (Planned)

- [ ] Integrate `langgraph-mcp` library
- [ ] Implement real MCP protocol calls
- [ ] Add connection pooling
- [ ] Implement retry logic with exponential backoff

### Phase 2: Security Hardening (Planned)

- [ ] Implement API key authentication
- [ ] Add certificate validation
- [ ] Implement rate limiting
- [ ] Add input sanitization

### Phase 3: Enhanced Features (Future)

- [ ] Tool discovery from MCP servers
- [ ] Schema validation for tool parameters
- [ ] Complex state transformations
- [ ] Conditional mapping based on response
- [ ] Circuit breaker pattern
- [ ] MCP server health monitoring

### Phase 4: Production Readiness (Future)

- [ ] Comprehensive security audit
- [ ] Performance testing and optimization
- [ ] Production deployment guide
- [ ] Monitoring and alerting setup
- [ ] Incident response procedures

---

## Additional Resources

### Documentation

- APEG Requirements: `docs/APEG_REQUIREMENTS_SUMMARY.md`
- APEG Status: `docs/APEG_STATUS.md`
- Deployment Guide: `docs/DEPLOYMENT.md`

### Code References

- MCP Client: `src/apeg_core/connectors/mcp_client.py:1`
- Orchestrator MCP Handler: `src/apeg_core/orchestrator.py:344`
- MCP Client Tests: `tests/test_mcp_client.py:1`
- MCP Integration Tests: `tests/test_mcp_integration.py:1`

### Related Specifications

- Model Context Protocol: (External documentation - to be added)
- LangGraph MCP: (External documentation - to be added)

---

**Last Updated:** 2025-11-20
**Version:** 1.0.0
**Status:** EXPERIMENTAL
**Maintainer:** APEG Development Team
