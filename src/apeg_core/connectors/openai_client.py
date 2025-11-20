"""OpenAI API client wrapper with test mode support.

This module provides a wrapper around the OpenAI Python SDK with:
- Automatic test mode fallback when API key is missing
- Support for APEG_TEST_MODE environment variable
- Graceful handling of missing openai package
- Chat completion interface compatible with GPT models

Example:
    from apeg_core.connectors import OpenAIClient

    # Production mode (requires OPENAI_API_KEY)
    client = OpenAIClient()
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}]
    )

    # Test mode (returns mock data)
    client = OpenAIClient(test_mode=True)
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}]
    )
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try importing OpenAI, fallback to test mode if not available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai package not installed, using test mode only")


class OpenAIClient:
    """OpenAI API client with test mode support.

    This client wrapper provides:
    - Automatic API key detection from environment
    - Test mode for development without API access
    - Graceful fallback if openai package is missing
    - Standard chat completion interface

    Attributes:
        api_key: OpenAI API key (None in test mode)
        test_mode: Whether to use mock responses
        client: OpenAI client instance (None in test mode)

    Example:
        # With API key in environment
        client = OpenAIClient()
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Analyze this code"}],
            model="gpt-4"
        )

        # Test mode
        client = OpenAIClient(test_mode=True)
        response = client.chat_completion(messages=[...])
        print(response["content"])  # "This is a test mode response."
    """

    def __init__(self, api_key: Optional[str] = None, test_mode: bool = False):
        """Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key (default: from OPENAI_API_KEY env var)
            test_mode: Force test mode even if API key is available (default: False)
        """
        # Check for explicit test mode from environment or parameter
        env_test_mode = os.getenv("APEG_TEST_MODE", "").lower() in ("true", "1", "yes")
        self.test_mode = test_mode or env_test_mode

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        # If no API key and not openai available, force test mode
        if not self.api_key or not OPENAI_AVAILABLE:
            if not self.test_mode:
                logger.warning(
                    "OpenAI API key not found or openai package not available, "
                    "enabling test mode"
                )
            self.test_mode = True
            self.client = None
        else:
            # Initialize OpenAI client
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                logger.warning("Falling back to test mode")
                self.test_mode = True
                self.client = None

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        **kwargs
    ) -> Dict[str, Any]:
        """Request a chat completion from OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: OpenAI model identifier (default: "gpt-4")
            **kwargs: Additional parameters to pass to OpenAI API
                (temperature, max_tokens, etc.)

        Returns:
            Dictionary containing:
                - content: Response text from the model
                - role: Role of the responder ("assistant")
                - model: Model used
                - finish_reason: Why generation stopped
                - usage: Token usage statistics (in test mode: None)

        Raises:
            Exception: If API call fails in production mode

        Example:
            response = client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is Python?"}
                ],
                model="gpt-4",
                temperature=0.7,
                max_tokens=500
            )
            print(response["content"])
        """
        if self.test_mode:
            return self._get_test_response(messages)

        # Make real API call
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )

            # Extract relevant information
            choice = response.choices[0]
            return {
                "content": choice.message.content,
                "role": choice.message.role,
                "model": response.model,
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            }
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    def _get_test_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a mock response for test mode.

        Args:
            messages: List of messages (used to generate contextual response)

        Returns:
            Mock response dictionary matching production format
        """
        # Extract last user message for context
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        # Generate test response
        test_content = (
            f"This is a test mode response. "
            f"In production, this would be a real OpenAI completion. "
            f"User query: {last_message[:50]}..."
        )

        return {
            "content": test_content,
            "role": "assistant",
            "model": "test-mode",
            "finish_reason": "stop",
            "usage": None,  # No usage data in test mode
        }
