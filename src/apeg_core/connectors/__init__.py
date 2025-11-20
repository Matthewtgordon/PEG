"""
Connectors for external services and APIs.

Components:
- OpenAIClient: OpenAI API integration with test mode support
- GitHubTools: GitHub API for repository operations (future)
- HTTPTools: Generic HTTP client with test mode (future)
"""

from .openai_client import OpenAIClient

__all__ = ["OpenAIClient"]
