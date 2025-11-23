"""
Domain agents for APEG runtime.

Components:
- BaseAgent: Abstract base class for all agents
- ShopifyAgent: Shopify e-commerce operations
- EtsyAgent: Etsy marketplace operations
- ValidatorAgent: Enhanced validation for generated code
- MetaAgent: Dynamic subagent generation
- GeneratedAgent: Wrapper for dynamically generated agents
- Agent registry: Dynamic agent instantiation

Auto-registration:
When this module is imported, Shopify and Etsy agents are automatically
registered in the global agent registry.
"""

from .base_agent import BaseAgent
from .agent_registry import (
    register_agent,
    get_agent,
    list_agents,
    is_agent_registered,
    unregister_agent,
    clear_registry,
    AGENT_REGISTRY
)
from .shopify_agent import ShopifyAgent
from .etsy_agent import EtsyAgent
from .validator_agent import ValidatorAgent, ValidationReport
from .meta_agent import MetaAgent, GeneratedAgent

__all__ = [
    "BaseAgent",
    "ShopifyAgent",
    "EtsyAgent",
    "ValidatorAgent",
    "ValidationReport",
    "MetaAgent",
    "GeneratedAgent",
    "register_agent",
    "get_agent",
    "list_agents",
    "is_agent_registered",
    "unregister_agent",
    "clear_registry",
    "AGENT_REGISTRY"
]

# Auto-register domain agents
register_agent("shopify", ShopifyAgent)
register_agent("etsy", EtsyAgent)
register_agent("validator", ValidatorAgent)
