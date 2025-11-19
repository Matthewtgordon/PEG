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

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseAgent(ABC):
    """
    Base class for all domain agents.

    Provides a standard interface for agent discovery and configuration.
    Subclasses must implement describe_capabilities() and operation methods.
    """

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        """
        Initialize the agent with configuration.

        Args:
            config: Optional configuration dictionary with API keys,
                   endpoints, and agent-specific settings
        """
        self.config = config or {}

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
