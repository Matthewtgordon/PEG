"""
Base Agent - Abstract base class for all domain-specific agents.

This module provides the foundation for domain agents like:
- ShopifyAgent: Shopify e-commerce operations
- EtsyAgent: Etsy marketplace operations
- Future: Amazon, eBay, custom integrations

All domain agents should inherit from BaseAgent and implement:
- describe_capabilities(): Return list of supported operations
- Individual operation methods with clear signatures
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all domain agents.

    Provides a standard interface for agent discovery, configuration,
    and execution. Subclasses must implement execute() method and
    describe_capabilities().

    Attributes:
        config: Agent configuration dictionary
        test_mode: Whether agent is in test mode (returns mock data)
        name: Agent name (from property)
    """

    def __init__(self, config: Dict[str, Any] | None = None, test_mode: bool = False) -> None:
        """
        Initialize the agent with configuration.

        Args:
            config: Optional configuration dictionary with API keys,
                   endpoints, and agent-specific settings
            test_mode: If True, use mock data instead of real API calls
        """
        self.config = config or {}
        self.test_mode = test_mode

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent's name.

        Returns:
            Agent name string (e.g., "ShopifyAgent", "EtsyAgent")
        """
        pass

    @abstractmethod
    def execute(self, action: str, context: Dict) -> Dict:
        """Execute an action with given context.

        This is the main entry point for agent operations. Subclasses
        should implement this to route to specific action handlers.

        Args:
            action: Action identifier (e.g., "product_sync", "inventory_check")
            context: Context dictionary with parameters for the action

        Returns:
            Dictionary containing results of the action

        Raises:
            NotImplementedError: If action is not supported
            ValueError: If context is invalid for the action

        Example:
            result = agent.execute("product_sync", {"product_id": "123"})
        """
        raise NotImplementedError("Subclasses must implement execute()")

    @abstractmethod
    def describe_capabilities(self) -> List[str]:
        """
        Return a list of capability identifiers supported by this agent.

        Capabilities are operation names that this agent can perform.
        Used for agent discovery and orchestration planning.

        Returns:
            List of capability names (e.g., ["list_products", "create_order"])

        Example:
            >>> agent = ShopifyAgent()
            >>> agent.describe_capabilities()
            ["list_products", "get_product", "update_inventory", ...]
        """
        raise NotImplementedError("Subclasses must implement describe_capabilities()")

    def _log_action(self, action: str, result: Dict) -> None:
        """Log an action execution to stdout.

        Args:
            action: Action that was executed
            result: Result dictionary from the action
        """
        status = result.get("status", "unknown")
        logger.info(f"Agent {self.name} executed '{action}': status={status}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(capabilities={len(self.describe_capabilities())})"
