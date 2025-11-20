"""
MCP (Model Context Protocol) Client

Provides integration with MCP servers for external tool calling.
This is an EXPERIMENTAL feature and NOT required for core APEG functionality.

The client operates in two modes:
1. Real Mode: Connects to MCP servers if langgraph-mcp is installed
2. Mock Mode: Returns deterministic test data if library not available

Usage:
    from apeg_core.connectors import MCPClient

    client = MCPClient(config={"server_url": "http://localhost:3000"})
    result = client.call_tool(
        server="filesystem",
        tool="read_file",
        params={"path": "/tmp/test.txt"}
    )

    # Check result
    if result["success"]:
        print(result["result"])
    else:
        print(f"Error: {result['error']}")

Environment Variables:
    APEG_TEST_MODE: If true, always use mock mode (default: true)
    MCP_SERVER_URL: Default MCP server URL (default: http://localhost:3000)
"""

import os
import logging
from typing import Dict, Any, Optional

# Conditional import - MCP is optional
MCP_AVAILABLE = False
try:
    import langgraph_mcp
    MCP_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP client wrapper for calling external tools via Model Context Protocol.

    If langgraph-mcp is not installed, this client operates in mock mode,
    returning deterministic test data without making real MCP calls.

    Attributes:
        config: Configuration dictionary with MCP server settings
        test_mode: Whether to use mock data (from APEG_TEST_MODE)
        client: Underlying MCP client (None if library not available)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize MCP client.

        Args:
            config: Optional configuration dict with keys:
                - server_url: Base URL for MCP server (default: http://localhost:3000)
                - timeout: Request timeout in seconds (default: 30)
                - retry_count: Number of retries on failure (default: 2)

        Example:
            >>> client = MCPClient({"server_url": "http://mcp.example.com"})
            >>> client.test_mode
            True
        """
        self.config = config or {}
        self.test_mode = os.getenv("APEG_TEST_MODE", "true").lower() == "true"

        if not MCP_AVAILABLE:
            logger.warning(
                "langgraph-mcp not installed. MCP client running in mock mode. "
                "Install with: pip install langgraph-mcp"
            )
            self.client = None
        else:
            # Initialize real MCP client
            self.client = self._init_mcp_client()

    def _init_mcp_client(self):
        """
        Initialize the actual MCP client (if library is available).

        Returns:
            MCP client instance or None if initialization fails
        """
        if not MCP_AVAILABLE:
            return None

        try:
            # Get server URL from config or environment
            server_url = self.config.get(
                "server_url",
                os.getenv("MCP_SERVER_URL", "http://localhost:3000")
            )

            # Initialize client (adjust based on langgraph-mcp API)
            client = langgraph_mcp.MCPClient(server_url)
            logger.info(f"MCP client initialized: {server_url}")
            return client

        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            return None

    def call_tool(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool.

        Args:
            server: MCP server identifier (e.g., "filesystem", "web_search")
            tool: Tool name (e.g., "read_file", "search")
            params: Tool parameters as dict

        Returns:
            Tool response as dict with keys:
                - success: bool (True if tool call succeeded)
                - result: Any (tool-specific response data)
                - error: Optional[str] (error message if success=False)

        Examples:
            >>> client = MCPClient()
            >>> result = client.call_tool("filesystem", "read_file", {"path": "/tmp/test"})
            >>> result["success"]
            True
            >>> result["result"]["content"]
            'Mock file content'

        Raises:
            No exceptions are raised; errors are returned in response dict
        """
        # Test mode or library not available - return mock data
        if self.test_mode or not self.client:
            return self._mock_tool_call(server, tool, params)

        # Real MCP call
        try:
            timeout = self.config.get("timeout", 30)
            retry_count = self.config.get("retry_count", 2)

            for attempt in range(retry_count + 1):
                try:
                    # Example call - adjust based on langgraph-mcp API
                    response = self.client.call(
                        server=server,
                        tool=tool,
                        parameters=params,
                        timeout=timeout
                    )

                    logger.info(f"MCP call succeeded: {server}.{tool}")
                    return {
                        "success": True,
                        "result": response,
                        "error": None
                    }

                except Exception as e:
                    if attempt < retry_count:
                        logger.warning(
                            f"MCP call failed (attempt {attempt + 1}/{retry_count + 1}): {e}"
                        )
                        continue
                    else:
                        logger.error(
                            f"MCP call failed after {retry_count + 1} attempts: {e}"
                        )
                        return {
                            "success": False,
                            "result": None,
                            "error": str(e)
                        }

        except Exception as e:
            logger.error(f"Unexpected error in MCP call: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }

    def _mock_tool_call(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Return mock data for testing (when MCP is not available or test mode is enabled).

        Args:
            server: MCP server identifier
            tool: Tool name
            params: Tool parameters

        Returns:
            Mock response with deterministic data
        """
        logger.info(f"[MOCK] MCP call: {server}.{tool}({params})")

        # Return deterministic mock data based on server and tool
        mock_responses = {
            "filesystem": {
                "read_file": {
                    "content": "Mock file content",
                    "size": 18,
                    "encoding": "utf-8"
                },
                "write_file": {
                    "success": True,
                    "bytes_written": 123,
                    "path": params.get("path", "/tmp/mock")
                },
                "list_files": {
                    "files": [
                        {"name": "file1.txt", "size": 100},
                        {"name": "file2.txt", "size": 200}
                    ]
                }
            },
            "web_search": {
                "search": {
                    "results": [
                        {
                            "title": "Mock Search Result",
                            "url": "http://example.com",
                            "snippet": "This is a mock search result snippet"
                        }
                    ],
                    "total_results": 1
                }
            },
            "database": {
                "query": {
                    "rows": [
                        {"id": 1, "name": "Mock Row 1"},
                        {"id": 2, "name": "Mock Row 2"}
                    ],
                    "count": 2
                }
            }
        }

        # Get mock result or return generic mock
        result = mock_responses.get(server, {}).get(tool, {
            "mock_server": server,
            "mock_tool": tool,
            "mock_params": params
        })

        return {
            "success": True,
            "result": result,
            "error": None
        }
