"""Tests for MCP client."""

import pytest
import os
from apeg_core.connectors.mcp_client import MCPClient, MCP_AVAILABLE


@pytest.fixture
def test_mode():
    """Ensure test mode is enabled for all tests."""
    original = os.environ.get("APEG_TEST_MODE")
    os.environ["APEG_TEST_MODE"] = "true"
    yield
    if original is not None:
        os.environ["APEG_TEST_MODE"] = original
    else:
        os.environ.pop("APEG_TEST_MODE", None)


def test_mcp_client_init(test_mode):
    """Test MCP client initialization."""
    client = MCPClient(config={"server_url": "http://localhost:3000"})

    assert client is not None
    assert client.test_mode is True
    assert client.config["server_url"] == "http://localhost:3000"


def test_mcp_client_init_default_config(test_mode):
    """Test MCP client with default configuration."""
    client = MCPClient()

    assert client is not None
    assert client.test_mode is True
    assert client.config == {}


def test_mcp_call_filesystem_read(test_mode):
    """Test MCP filesystem read_file call in mock mode."""
    client = MCPClient()

    result = client.call_tool(
        server="filesystem",
        tool="read_file",
        params={"path": "/tmp/test.txt"}
    )

    assert result["success"] is True
    assert result["error"] is None
    assert "content" in result["result"]
    assert result["result"]["content"] == "Mock file content"


def test_mcp_call_filesystem_write(test_mode):
    """Test MCP filesystem write_file call in mock mode."""
    client = MCPClient()

    result = client.call_tool(
        server="filesystem",
        tool="write_file",
        params={"path": "/tmp/output.txt", "content": "test data"}
    )

    assert result["success"] is True
    assert result["error"] is None
    assert result["result"]["success"] is True
    assert result["result"]["bytes_written"] == 123


def test_mcp_call_web_search(test_mode):
    """Test MCP web_search call in mock mode."""
    client = MCPClient()

    result = client.call_tool(
        server="web_search",
        tool="search",
        params={"query": "test query"}
    )

    assert result["success"] is True
    assert result["error"] is None
    assert "results" in result["result"]
    assert len(result["result"]["results"]) > 0
    assert "title" in result["result"]["results"][0]


def test_mcp_call_unknown_server(test_mode):
    """Test MCP call to unknown server returns generic mock data."""
    client = MCPClient()

    result = client.call_tool(
        server="unknown_server",
        tool="unknown_tool",
        params={"param": "value"}
    )

    assert result["success"] is True
    assert result["error"] is None
    assert "mock_server" in result["result"]
    assert result["result"]["mock_server"] == "unknown_server"


def test_mcp_library_availability():
    """Test that MCP_AVAILABLE flag is set correctly."""
    # This test just verifies the flag exists and is boolean
    assert isinstance(MCP_AVAILABLE, bool)

    # Log the status for debugging
    if MCP_AVAILABLE:
        print("langgraph-mcp is installed")
    else:
        print("langgraph-mcp is NOT installed (expected in test mode)")
