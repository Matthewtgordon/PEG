"""
Tool bridge for converting APEG agent methods to SDK function tools.

Automatically generates SDK-compatible tools from APEG agent methods,
including proper type hints and docstrings for schema generation.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, get_type_hints

from agents import function_tool

from apeg_core.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ToolBridge:
    """
    Converts APEG agent methods to OpenAI SDK function tools.

    Automatically discovers agent methods, extracts their signatures,
    and creates SDK-compatible tools with proper schemas.

    Usage:
        >>> bridge = ToolBridge(shopify_agent)
        >>> tools = bridge.create_tools()
        >>> sdk_agent = Agent(name="Shopify", tools=tools)
    """

    # Methods to exclude from tool generation (infrastructure methods)
    EXCLUDED_METHODS = {
        'execute', 'initialize', 'cleanup', 'describe_capabilities',
        'get_config', 'set_config', 'name',
    }

    def __init__(self, apeg_agent: BaseAgent):
        """
        Initialize tool bridge.

        Args:
            apeg_agent: APEG agent to extract tools from
        """
        self.apeg_agent = apeg_agent
        self.agent_name = apeg_agent.__class__.__name__
        logger.info(f"ToolBridge initialized for {self.agent_name}")

    def create_tools(self, method_filter: Optional[Callable[[str], bool]] = None) -> List[Callable]:
        """
        Create SDK function tools from agent methods.

        Args:
            method_filter: Optional function to filter which methods become tools.
                          Takes method name, returns True to include.
                          Default: Include all public methods (not starting with _)

        Returns:
            List of SDK function tools

        Example:
            >>> # Include only specific methods
            >>> tools = bridge.create_tools(
            ...     method_filter=lambda name: name in ['get_products', 'update_inventory']
            ... )
        """
        tools = []

        # Default filter: public methods only
        if method_filter is None:
            method_filter = lambda name: not name.startswith('_')

        # Discover all methods on agent
        for method_name in dir(self.apeg_agent):
            # Skip private methods, dunder methods, and properties
            if method_name.startswith('_'):
                continue

            # Skip if filtered out
            if not method_filter(method_name):
                continue

            # Skip excluded methods
            if method_name in self.EXCLUDED_METHODS:
                continue

            # Get method
            method = getattr(self.apeg_agent, method_name)

            # Skip if not callable
            if not callable(method):
                continue

            # Create SDK tool from method
            try:
                tool = self._create_tool_from_method(method, method_name)
                tools.append(tool)
                logger.debug(f"Created tool for {self.agent_name}.{method_name}")
            except Exception as e:
                logger.warning(f"Could not create tool for {method_name}: {e}")

        logger.info(f"Created {len(tools)} tools from {self.agent_name}")
        return tools

    def _create_tool_from_method(self, method: Callable, method_name: str) -> Callable:
        """
        Create SDK function tool from a single method.

        Args:
            method: Method to wrap as tool
            method_name: Name of the method

        Returns:
            SDK function tool
        """
        # Get method signature
        sig = inspect.signature(method)

        # Get docstring for tool description
        docstring = inspect.getdoc(method) or f"{method_name} from {self.agent_name}"

        # Extract first line of docstring for description
        description = docstring.split('\n')[0] if docstring else f"Execute {method_name}"

        # Capture the method in a closure
        captured_method = method

        # Create wrapper function with proper signature
        def tool_wrapper(**kwargs):
            """Wrapper that calls the original agent method."""
            try:
                result = captured_method(**kwargs)
                # Convert result to string if needed for SDK
                if isinstance(result, dict):
                    import json
                    return json.dumps(result, indent=2, default=str)
                return str(result)
            except Exception as e:
                return f"Error executing {method_name}: {e}"

        # Copy signature and docstring
        tool_wrapper.__signature__ = sig
        tool_wrapper.__doc__ = description
        tool_wrapper.__name__ = f"{self.agent_name}_{method_name}"

        # Apply SDK function_tool decorator
        return function_tool(tool_wrapper)

    def get_method_schemas(self) -> List[Dict[str, Any]]:
        """
        Get JSON schemas for all agent methods.

        Returns:
            List of method schema dictionaries with:
                - name: Method name
                - description: From docstring
                - parameters: Parameter types and descriptions

        Useful for debugging or documentation.
        """
        schemas = []

        for method_name in dir(self.apeg_agent):
            if method_name.startswith('_') or method_name in self.EXCLUDED_METHODS:
                continue

            method = getattr(self.apeg_agent, method_name)
            if not callable(method):
                continue

            try:
                sig = inspect.signature(method)
                docstring = inspect.getdoc(method) or ""

                params = {}
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    params[param_name] = {
                        'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                        'default': str(param.default) if param.default != inspect.Parameter.empty else None,
                        'required': param.default == inspect.Parameter.empty,
                    }

                schemas.append({
                    'name': method_name,
                    'description': docstring.split('\n')[0],
                    'parameters': params,
                })
            except Exception as e:
                logger.debug(f"Could not get schema for {method_name}: {e}")

        return schemas


def apeg_method_to_sdk_tool(method: Callable, agent_name: str = "Agent") -> Callable:
    """
    Convert a single APEG agent method to SDK function tool.

    Convenience function for one-off tool creation.

    Args:
        method: Agent method to convert
        agent_name: Name prefix for tool

    Returns:
        SDK function tool

    Example:
        >>> tool = apeg_method_to_sdk_tool(
        ...     shopify_agent.get_product,
        ...     agent_name="Shopify"
        ... )
    """
    method_name = method.__name__
    sig = inspect.signature(method)
    docstring = inspect.getdoc(method) or f"{method_name}"
    description = docstring.split('\n')[0]

    # Capture method in closure
    captured_method = method

    def tool_wrapper(**kwargs):
        try:
            result = captured_method(**kwargs)
            if isinstance(result, dict):
                import json
                return json.dumps(result, indent=2, default=str)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    tool_wrapper.__signature__ = sig
    tool_wrapper.__doc__ = description
    tool_wrapper.__name__ = f"{agent_name}_{method_name}"

    return function_tool(tool_wrapper)
