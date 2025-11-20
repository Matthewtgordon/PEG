"""Tests for OpenAI client wrapper with test mode support."""

import os
from unittest.mock import MagicMock, patch

import pytest

from apeg_core.connectors import OpenAIClient


def test_openai_client_test_mode():
    """Verify test mode returns canned response."""
    client = OpenAIClient(test_mode=True)

    messages = [{"role": "user", "content": "Hello, how are you?"}]
    response = client.chat_completion(messages=messages)

    # Verify response structure
    assert "content" in response
    assert "role" in response
    assert "model" in response
    assert "finish_reason" in response

    # Verify test mode indicators
    assert response["role"] == "assistant"
    assert response["model"] == "test-mode"
    assert response["finish_reason"] == "stop"
    assert response["usage"] is None

    # Verify response contains test mode message
    assert "test mode response" in response["content"].lower()


def test_openai_client_missing_key():
    """Verify falls back to test mode if no API key."""
    # Ensure no API key in environment
    with patch.dict(os.environ, {}, clear=True):
        client = OpenAIClient(test_mode=False)

        # Should automatically enable test mode
        assert client.test_mode is True
        assert client.client is None

        # Should return test response
        messages = [{"role": "user", "content": "Test"}]
        response = client.chat_completion(messages=messages)
        assert response["model"] == "test-mode"


def test_openai_client_env_test_mode():
    """Verify APEG_TEST_MODE environment variable enables test mode."""
    with patch.dict(os.environ, {"APEG_TEST_MODE": "true", "OPENAI_API_KEY": "sk-fake"}):
        client = OpenAIClient()

        # Should be in test mode despite having API key
        assert client.test_mode is True

        messages = [{"role": "user", "content": "Test"}]
        response = client.chat_completion(messages=messages)
        assert response["model"] == "test-mode"


def test_openai_client_chat_completion_mocked():
    """Verify chat completion in test mode with detailed context."""
    # Test mode doesn't require mocking OpenAI library
    client = OpenAIClient(test_mode=True)

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Explain Python decorators"}
    ]

    response = client.chat_completion(messages=messages, model="gpt-4", temperature=0.7)

    # Verify response structure
    assert "content" in response
    assert "role" in response
    assert response["role"] == "assistant"
    assert response["model"] == "test-mode"
    assert response["finish_reason"] == "stop"

    # Verify response includes context from user message
    assert "decorators" in response["content"].lower() or "python" in response["content"].lower()


def test_openai_client_error_handling():
    """Verify exceptions handled gracefully in test mode."""
    client = OpenAIClient(test_mode=True)

    # Even with malformed messages, should not crash in test mode
    messages = []
    response = client.chat_completion(messages=messages)

    # Should still return a response
    assert "content" in response
    assert response["model"] == "test-mode"
