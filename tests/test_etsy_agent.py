"""Tests for EtsyAgent domain agent.

Tests cover:
- Agent initialization and name property
- Execute method with various actions in test mode
- NotImplementedError when test_mode is False
- Capabilities listing
- Individual operation methods (stub data)
"""

import pytest

from apeg_core.agents.etsy_agent import EtsyAgent


def test_etsy_agent_initialization():
    """Test EtsyAgent initialization and name property."""
    # Test without config
    agent1 = EtsyAgent()
    assert agent1.name == "EtsyAgent"
    assert agent1.test_mode is False
    assert agent1.config == {}

    # Test with config and test mode
    config = {
        "api_key": "test-api-key",
        "api_secret": "test-secret",
        "shop_id": "12345678",
        "access_token": "test-access-token"
    }
    agent2 = EtsyAgent(config=config, test_mode=True)
    assert agent2.name == "EtsyAgent"
    assert agent2.test_mode is True
    assert agent2.config == config


def test_etsy_agent_execute_test_mode():
    """Test execute method with various actions in test mode."""
    agent = EtsyAgent(test_mode=True)

    # Test listing_sync action
    result1 = agent.execute("listing_sync", {"listing_id": "456"})
    assert result1["status"] == "synced"
    assert result1["listing_id"] == "mock-456"
    assert result1["title"] == "Test Listing"

    # Test inventory_management action
    result2 = agent.execute("inventory_management", {"listing_id": "456"})
    assert result2["updated"] is True
    assert result2["sku"] == "TEST-002"
    assert result2["quantity"] == 30

    # Test shop_stats action
    result3 = agent.execute("shop_stats", {})
    assert result3["views"] == 1200
    assert result3["favorites"] == 45
    assert result3["sales"] == 23

    # Test unknown action
    result4 = agent.execute("unknown_action", {})
    assert "error" in result4
    assert result4["action"] == "unknown_action"


def test_etsy_agent_execute_real_mode_raises():
    """Test that execute raises NotImplementedError when test_mode is False."""
    agent = EtsyAgent(test_mode=False)

    with pytest.raises(NotImplementedError, match="Real Etsy API not implemented"):
        agent.execute("listing_sync", {"listing_id": "456"})


def test_etsy_agent_describe_capabilities():
    """Test describe_capabilities returns expected operations."""
    agent = EtsyAgent()

    capabilities = agent.describe_capabilities()

    assert isinstance(capabilities, list)
    assert len(capabilities) > 0
    assert "list_listings" in capabilities
    assert "create_listing" in capabilities
    assert "update_listing" in capabilities
    assert "update_inventory" in capabilities
    assert "list_orders" in capabilities
    assert "ship_order" in capabilities
    assert "send_customer_message" in capabilities
    assert "suggest_listing_seo" in capabilities
    assert "get_shop_stats" in capabilities


def test_etsy_agent_list_listings():
    """Test list_listings method returns stub data."""
    agent = EtsyAgent(test_mode=True)

    # Test without status filter
    listings1 = agent.list_listings()
    assert isinstance(listings1, list)
    assert len(listings1) == 2
    assert listings1[0]["title"] == "Handmade Gemstone Anklet - Turquoise Beads"
    assert listings1[0]["status"] == "active"
    assert listings1[0]["quantity"] == 8

    # Test with status filter
    listings2 = agent.list_listings(status_filter="draft", limit=10)
    assert isinstance(listings2, list)
    assert listings2[0]["status"] == "draft"
