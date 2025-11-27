"""
Tests for the inventory text-to-command translator.
"""
from __future__ import annotations

import json
import os
from unittest.mock import Mock, patch

import pytest

from apeg_core.translators.inventory_text_to_command import (
    build_inventory_command_from_text,
    format_inventory_result,
)


class TestInventoryTranslator:
    """Test suite for inventory translator."""

    def test_build_command_requires_api_key(self):
        """Test that build_inventory_command_from_text requires OPENAI_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                build_inventory_command_from_text("Set Tanzanite to 5")

    @patch("apeg_core.translators.inventory_text_to_command.OpenAI")
    def test_build_command_success(self, mock_openai_class):
        """Test successful translation of natural language to command."""
        # Mock the OpenAI client response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Create a mock response
        mock_message = Mock()
        mock_message.content = json.dumps({
            "task_type": "inventory_update",
            "store": "dev",
            "product_title": "Tanzanite ankle bracelet",
            "variants": [
                {"variant_label": "Medium", "new_quantity": 5}
            ]
        })

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        # Set environment variable
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = build_inventory_command_from_text("Set Tanzanite to 5")

        # Verify result
        assert result["task_type"] == "inventory_update"
        assert result["store"] == "dev"
        assert "Tanzanite" in result["product_title"]
        assert len(result["variants"]) == 1
        assert result["variants"][0]["variant_label"] == "Medium"
        assert result["variants"][0]["new_quantity"] == 5

        # Verify OpenAI client was called correctly
        mock_openai_class.assert_called_once_with(api_key="test-key")
        mock_client.chat.completions.create.assert_called_once()

    @patch("apeg_core.translators.inventory_text_to_command.OpenAI")
    def test_build_command_strips_markdown(self, mock_openai_class):
        """Test that markdown code fences are stripped from response."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Response with markdown code fences
        mock_message = Mock()
        mock_message.content = "```json\n" + json.dumps({
            "task_type": "inventory_update",
            "store": "dev",
            "product_title": "Test Product",
            "variants": [{"variant_label": "Small", "new_quantity": 10}]
        }) + "\n```"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = build_inventory_command_from_text("Set Test Product Small to 10")

        assert result["task_type"] == "inventory_update"
        assert len(result["variants"]) == 1

    @patch("apeg_core.translators.inventory_text_to_command.OpenAI")
    def test_build_command_invalid_json(self, mock_openai_class):
        """Test error handling for invalid JSON response."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_message = Mock()
        mock_message.content = "This is not valid JSON"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(ValueError, match="not valid JSON"):
                build_inventory_command_from_text("Set Tanzanite to 5")

    @patch("apeg_core.translators.inventory_text_to_command.OpenAI")
    def test_build_command_invalid_task_type(self, mock_openai_class):
        """Test error handling for invalid task_type."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_message = Mock()
        mock_message.content = json.dumps({
            "task_type": "invalid_type",
            "store": "dev",
            "product_title": "Test",
            "variants": []
        })

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(ValueError, match="Invalid task_type"):
                build_inventory_command_from_text("Set Tanzanite to 5")

    @patch("apeg_core.translators.inventory_text_to_command.OpenAI")
    def test_build_command_missing_variants(self, mock_openai_class):
        """Test error handling for missing variants."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_message = Mock()
        mock_message.content = json.dumps({
            "task_type": "inventory_update",
            "store": "dev",
            "product_title": "Test"
        })

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(ValueError, match="variants"):
                build_inventory_command_from_text("Set Tanzanite to 5")


class TestInventoryResultFormatter:
    """Test suite for inventory result formatter."""

    def test_format_basic_result(self):
        """Test formatting of basic inventory result."""
        result = {
            "status": "success",
            "store": "dev",
            "product_title": "TEST - Tanzanite Ankle Bracelet",
            "product_id": "123456",
            "updates": [
                {
                    "variant_label": "Medium",
                    "variant_id": "var_001",
                    "update_result": {
                        "status": "success",
                        "old_quantity": 3,
                        "new_quantity": 5
                    }
                }
            ]
        }

        formatted = format_inventory_result(result)

        assert "Status: success" in formatted
        assert "Store: dev" in formatted
        assert "Tanzanite" in formatted
        assert "Product ID: 123456" in formatted
        assert "Medium" in formatted
        assert "var_001" in formatted
        assert "3 → 5" in formatted

    def test_format_multiple_variants(self):
        """Test formatting of result with multiple variant updates."""
        result = {
            "status": "success",
            "store": "dev",
            "product_title": "Test Product",
            "product_id": "123",
            "updates": [
                {
                    "variant_label": "Small",
                    "variant_id": "v1",
                    "update_result": {
                        "status": "success",
                        "old_quantity": 5,
                        "new_quantity": 10
                    }
                },
                {
                    "variant_label": "Large",
                    "variant_id": "v2",
                    "update_result": {
                        "status": "success",
                        "old_quantity": 2,
                        "new_quantity": 8
                    }
                }
            ]
        }

        formatted = format_inventory_result(result)

        assert "Small" in formatted
        assert "Large" in formatted
        assert "5 → 10" in formatted
        assert "2 → 8" in formatted

    def test_format_empty_updates(self):
        """Test formatting of result with no updates."""
        result = {
            "status": "success",
            "store": "dev",
            "product_title": "Test Product",
            "product_id": "123",
            "updates": []
        }

        formatted = format_inventory_result(result)

        assert "(no updates)" in formatted
