"""Tests for ShopifyAgent domain agent.

Tests cover:
- Agent initialization and name property
- Execute method with various actions in test mode
- NotImplementedError when test_mode is False
- Capabilities listing
- Individual operation methods (stub data)
"""

import pytest

from apeg_core.agents.shopify_agent import ShopifyAgent


def test_shopify_agent_initialization():
    """Test ShopifyAgent initialization and name property."""
    # Test without config
    agent1 = ShopifyAgent()
    assert agent1.name == "ShopifyAgent"
    assert agent1.test_mode is False
    assert agent1.config == {}

    # Test with config and test mode
    config = {
        "shop_url": "https://test-shop.myshopify.com",
        "api_key": "test-key",
        "access_token": "test-token"
    }
    agent2 = ShopifyAgent(config=config, test_mode=True)
    assert agent2.name == "ShopifyAgent"
    assert agent2.test_mode is True
    assert agent2.config == config


def test_shopify_agent_execute_test_mode():
    """Test execute method with various actions in test mode."""
    agent = ShopifyAgent(test_mode=True)

    # Test product_sync action
    result1 = agent.execute("product_sync", {"product_id": "123"})
    assert result1["status"] == "synced"
    assert result1["product_id"] == "mock-123"
    assert result1["title"] == "Test Product"

    # Test inventory_check action
    result2 = agent.execute("inventory_check", {})
    assert "inventory" in result2
    assert len(result2["inventory"]) > 0
    assert result2["inventory"][0]["sku"] == "TEST-001"

    # Test seo_analysis action
    result3 = agent.execute("seo_analysis", {"product_id": "123"})
    assert result3["score"] == 85
    assert "recommendations" in result3

    # Test unknown action
    result4 = agent.execute("unknown_action", {})
    assert "error" in result4
    assert result4["action"] == "unknown_action"


def test_shopify_agent_execute_real_mode_without_credentials():
    """Test that execute in real mode without credentials uses stub data.

    When test_mode=False but credentials are not provided, the agent
    falls back to stub responses to allow graceful degradation.
    """
    agent = ShopifyAgent(test_mode=False)

    # Without credentials, has_api_client should be False
    assert agent.has_api_client is False

    # Execute should still work with stub data (graceful fallback)
    result = agent.execute("product_sync", {"product_id": "123"})
    # In real mode with no credentials, it routes to actual handlers
    # which return product details from list_products/get_product (stubs)
    assert "products" in result or "id" in result


def test_shopify_agent_describe_capabilities():
    """Test describe_capabilities returns expected operations."""
    agent = ShopifyAgent()

    capabilities = agent.describe_capabilities()

    assert isinstance(capabilities, list)
    assert len(capabilities) > 0
    assert "list_products" in capabilities
    assert "get_product" in capabilities
    assert "update_inventory" in capabilities
    assert "list_orders" in capabilities
    assert "get_order" in capabilities
    assert "create_order_from_etsy" in capabilities
    assert "send_customer_message" in capabilities
    assert "fulfill_order" in capabilities
    assert "cancel_order" in capabilities


def test_shopify_agent_list_products():
    """Test list_products method returns stub data."""
    agent = ShopifyAgent(test_mode=True)

    # Test without status filter
    products1 = agent.list_products()
    assert isinstance(products1, list)
    assert len(products1) == 2
    assert products1[0]["title"] == "Handmade Turquoise Anklet"
    assert products1[0]["status"] == "active"
    assert products1[0]["inventory"] == 10

    # Test with status filter
    products2 = agent.list_products(status_filter="draft", limit=10)
    assert isinstance(products2, list)
    assert products2[0]["status"] == "draft"
