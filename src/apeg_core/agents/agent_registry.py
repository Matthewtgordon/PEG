"""Agent registry for dynamic agent instantiation.

This module provides a centralized registry for domain agents,
allowing dynamic discovery and instantiation based on agent names.

Example:
    from apeg_core.agents import register_agent, get_agent, ShopifyAgent

    # Register an agent
    register_agent("shopify", ShopifyAgent)

    # Get an agent instance
    agent = get_agent("shopify", config={}, test_mode=True)
    result = agent.execute("product_sync", {"product_id": "123"})
"""

import logging
from typing import Any, Dict, List, Type

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Global agent registry
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {}


def register_agent(name: str, agent_class: Type[BaseAgent]) -> None:
    """Register an agent class in the global registry.

    Args:
        name: Agent identifier (e.g., "shopify", "etsy")
        agent_class: Agent class (must inherit from BaseAgent)

    Raises:
        TypeError: If agent_class doesn't inherit from BaseAgent
        ValueError: If agent name already registered

    Example:
        from apeg_core.agents import register_agent, ShopifyAgent
        register_agent("shopify", ShopifyAgent)
    """
    if not issubclass(agent_class, BaseAgent):
        raise TypeError(f"{agent_class} must inherit from BaseAgent")

    if name in AGENT_REGISTRY:
        logger.warning(f"Agent '{name}' already registered, overwriting")

    AGENT_REGISTRY[name] = agent_class
    logger.info(f"Registered agent: {name} -> {agent_class.__name__}")


def get_agent(
    name: str,
    config: Dict[str, Any] | None = None,
    test_mode: bool = False
) -> BaseAgent:
    """Get an agent instance from the registry.

    Args:
        name: Agent identifier (e.g., "shopify", "etsy")
        config: Configuration dictionary for the agent
        test_mode: If True, agent uses mock data instead of real APIs

    Returns:
        Instantiated agent

    Raises:
        KeyError: If agent not registered

    Example:
        agent = get_agent("shopify", config={"shop_url": "..."}, test_mode=True)
        result = agent.execute("product_sync", {"product_id": "123"})
    """
    if name not in AGENT_REGISTRY:
        available = ", ".join(AGENT_REGISTRY.keys()) if AGENT_REGISTRY else "none"
        raise KeyError(
            f"Agent '{name}' not found in registry. "
            f"Available agents: {available}"
        )

    agent_class = AGENT_REGISTRY[name]
    logger.debug(f"Creating agent instance: {name} (test_mode={test_mode})")

    return agent_class(config=config, test_mode=test_mode)


def list_agents() -> List[str]:
    """List all registered agent names.

    Returns:
        List of agent identifiers

    Example:
        >>> list_agents()
        ['shopify', 'etsy']
    """
    return list(AGENT_REGISTRY.keys())


def is_agent_registered(name: str) -> bool:
    """Check if an agent is registered.

    Args:
        name: Agent identifier to check

    Returns:
        True if agent is registered, False otherwise

    Example:
        >>> is_agent_registered("shopify")
        True
    """
    return name in AGENT_REGISTRY


def unregister_agent(name: str) -> None:
    """Remove an agent from the registry.

    Args:
        name: Agent identifier to remove

    Raises:
        KeyError: If agent not registered

    Example:
        unregister_agent("shopify")
    """
    if name not in AGENT_REGISTRY:
        raise KeyError(f"Agent '{name}' not registered")

    del AGENT_REGISTRY[name]
    logger.info(f"Unregistered agent: {name}")


def clear_registry() -> None:
    """Clear all registered agents.

    Warning: This is primarily for testing. Use with caution.

    Example:
        clear_registry()  # Remove all registered agents
    """
    AGENT_REGISTRY.clear()
    logger.warning("Agent registry cleared")
