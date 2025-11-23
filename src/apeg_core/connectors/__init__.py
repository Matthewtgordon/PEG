"""
Connectors for external services and APIs.

Components:
- OpenAIClient: OpenAI API integration with test mode support
- PluginManager: Dynamic plugin loading and management
- PluginBase: Base class for plugins
- EcommConnector: Unified Shopify/Etsy connector with encrypted key storage
- GitHubTools: GitHub API for repository operations (future)
- HTTPTools: Generic HTTP client with test mode (future)
"""

from .openai_client import OpenAIClient
from .plugin_manager import (
    PluginManager,
    PluginBase,
    get_plugin_manager,
    load_plugins
)
from .ecomm import EcommConnector, EC

__all__ = [
    "OpenAIClient",
    "PluginManager",
    "PluginBase",
    "get_plugin_manager",
    "load_plugins",
    "EcommConnector",
    "EC",
]
