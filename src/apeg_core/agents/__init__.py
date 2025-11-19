"""
Domain-specific agents for APEG runtime.

Components:
- BaseAgent: Abstract base class for all agents
- ShopifyAgent: Shopify e-commerce integration (stub)
- EtsyAgent: Etsy marketplace integration (stub)
- llm_roles: LLM role wrappers (ENGINEER, VALIDATOR, etc.)
"""

from apeg_core.agents.base_agent import BaseAgent
from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.agents.etsy_agent import EtsyAgent
from apeg_core.agents import llm_roles

__all__ = ["BaseAgent", "ShopifyAgent", "EtsyAgent", "llm_roles"]
