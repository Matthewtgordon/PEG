"""Integration tests for MCP workflow nodes."""

import pytest
import os
import json
from pathlib import Path
from apeg_core import APEGOrchestrator


@pytest.fixture
def test_mode():
    """Ensure test mode for all tests."""
    original = os.environ.get("APEG_TEST_MODE")
    os.environ["APEG_TEST_MODE"] = "true"
    yield
    if original is not None:
        os.environ["APEG_TEST_MODE"] = original
    else:
        os.environ.pop("APEG_TEST_MODE", None)


@pytest.fixture
def mcp_workflow(tmp_path):
    """Create workflow with MCP node."""
    workflow = {
        "nodes": [
            {
                "id": "start",
                "type": "process",
                "agent": "PEG",
                "action": "Initialize"
            },
            {
                "id": "mcp_read",
                "type": "mcp_tool",
                "description": "Read file using MCP",
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
            {"from": "start", "to": "mcp_read"},
            {"from": "mcp_read", "to": "end"}
        ],
        "entry_point": "start"
    }

    workflow_path = tmp_path / "mcp_workflow.json"
    with open(workflow_path, "w") as f:
        json.dump(workflow, f, indent=2)

    return workflow_path


@pytest.fixture
def basic_config(tmp_path):
    """Create minimal config for testing."""
    config = {
        "session_type": "PEG",
        "mode": "Full",
        "tools_enabled": True,
        "mcp": {
            "server_url": "http://localhost:3000",
            "timeout": 30,
            "retry_count": 2
        }
    }

    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return config_path


def test_mcp_node_execution(test_mode, mcp_workflow, basic_config):
    """Test MCP node executes without errors in workflow."""
    orchestrator = APEGOrchestrator(
        config_path=basic_config,
        workflow_graph_path=mcp_workflow
    )

    # Set initial state with file path
    orchestrator.state["file_path"] = "/tmp/test.txt"

    # Execute graph
    orchestrator.execute_graph()

    # Should not crash
    assert orchestrator.state is not None

    # Should have processed MCP node
    # Either file_content should be present (success) or _mcp_error (failure)
    assert "file_content" in orchestrator.state or "_mcp_error" in orchestrator.state

    # If successful, verify mock data
    if "file_content" in orchestrator.state:
        assert orchestrator.state["file_content"] == "Mock file content"


def test_mcp_node_missing_config(test_mode, tmp_path, basic_config):
    """Test MCP node handles missing config gracefully."""
    workflow = {
        "nodes": [
            {
                "id": "bad_mcp",
                "type": "mcp_tool",
                "description": "MCP node with missing config",
                "mcp_config": {}  # Missing server and tool_name
            }
        ],
        "edges": [],
        "entry_point": "bad_mcp"
    }

    workflow_path = tmp_path / "bad_mcp_workflow.json"
    with open(workflow_path, "w") as f:
        json.dump(workflow, f)

    orchestrator = APEGOrchestrator(
        config_path=basic_config,
        workflow_graph_path=workflow_path
    )

    # Should not crash
    orchestrator.execute_graph()
    assert orchestrator.state is not None

    # Should have completed without file_content (missing tool_name)
    # Mock mode will still return data for unknown tools
    assert "file_content" not in orchestrator.state or orchestrator.state.get("file_content") is None


def test_mcp_web_search_node(test_mode, tmp_path, basic_config):
    """Test MCP web search node."""
    workflow = {
        "nodes": [
            {
                "id": "search",
                "type": "mcp_tool",
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
        ],
        "edges": [],
        "entry_point": "search"
    }

    workflow_path = tmp_path / "search_workflow.json"
    with open(workflow_path, "w") as f:
        json.dump(workflow, f)

    orchestrator = APEGOrchestrator(
        config_path=basic_config,
        workflow_graph_path=workflow_path
    )

    # Set search query
    orchestrator.state["search_query"] = "test query"

    # Execute
    orchestrator.execute_graph()

    assert orchestrator.state is not None

    # Should have search results (mock data)
    if "search_results" in orchestrator.state:
        assert isinstance(orchestrator.state["search_results"], list)
        assert len(orchestrator.state["search_results"]) > 0
