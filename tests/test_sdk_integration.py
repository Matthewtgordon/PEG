"""
Unit tests for OpenAI Agents SDK integration.

Tests:
- ToolBridge functionality
- APEGAgentAdapter conversion
- SDKAgentWrapper compatibility
- HandoffCoordinator management
"""

import pytest
import sys

sys.path.insert(0, 'src')

from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.agents.etsy_agent import EtsyAgent
from apeg_core.sdk_integration import (
    APEGAgentAdapter,
    SDKAgentWrapper,
    ToolBridge,
    HandoffCoordinator,
)

from agents import Agent


class TestToolBridge:
    """Test ToolBridge creates SDK tools from APEG agents."""

    def test_tool_bridge_initialization(self):
        """Test ToolBridge can be initialized with APEG agent."""
        agent = ShopifyAgent(config={"test_mode": True})
        bridge = ToolBridge(agent)

        assert bridge.apeg_agent is agent
        assert bridge.agent_name == "ShopifyAgent"

    def test_create_tools_from_shopify_agent(self):
        """Test tools are created from ShopifyAgent methods."""
        agent = ShopifyAgent(config={"test_mode": True})
        bridge = ToolBridge(agent)

        tools = bridge.create_tools()

        assert len(tools) > 0, "Expected at least one tool"

        # Verify tools have expected attributes
        for tool in tools:
            assert hasattr(tool, 'name'), f"Tool missing name attribute"

    def test_create_tools_from_etsy_agent(self):
        """Test tools are created from EtsyAgent methods."""
        agent = EtsyAgent(config={"test_mode": True})
        bridge = ToolBridge(agent)

        tools = bridge.create_tools()

        assert len(tools) > 0, "Expected at least one tool from EtsyAgent"

    def test_tool_filter_includes_specific_methods(self):
        """Test method_filter parameter includes specific tools."""
        agent = ShopifyAgent(config={"test_mode": True})
        bridge = ToolBridge(agent)

        # Only include list_products and get_product methods
        tools = bridge.create_tools(
            method_filter=lambda name: name in ['list_products', 'get_product']
        )

        # Should have exactly 2 tools
        assert len(tools) == 2, f"Expected 2 tools, got {len(tools)}"

        tool_names = [getattr(t, 'name', str(t)) for t in tools]
        assert any('list_products' in name for name in tool_names)
        assert any('get_product' in name for name in tool_names)

    def test_tool_filter_excludes_methods(self):
        """Test method_filter excludes specific methods."""
        agent = ShopifyAgent(config={"test_mode": True})
        bridge = ToolBridge(agent)

        # Create all tools
        all_tools = bridge.create_tools()

        # Create filtered tools (exclude list_products)
        filtered_tools = bridge.create_tools(
            method_filter=lambda name: name != 'list_products'
        )

        assert len(filtered_tools) < len(all_tools), "Filtered should have fewer tools"

    def test_get_method_schemas(self):
        """Test get_method_schemas returns schema info."""
        agent = ShopifyAgent(config={"test_mode": True})
        bridge = ToolBridge(agent)

        schemas = bridge.get_method_schemas()

        assert len(schemas) > 0, "Expected at least one schema"
        for schema in schemas:
            assert 'name' in schema
            assert 'description' in schema
            assert 'parameters' in schema


class TestAPEGAgentAdapter:
    """Test APEGAgentAdapter wraps APEG agents as SDK agents."""

    def test_adapter_initialization(self):
        """Test adapter initializes with APEG agent."""
        agent = ShopifyAgent(config={"test_mode": True})
        adapter = APEGAgentAdapter(agent)

        assert adapter.apeg_agent is agent
        assert adapter.agent_name == "ShopifyAgent"

    def test_adapter_with_custom_instructions(self):
        """Test adapter accepts custom instructions."""
        agent = ShopifyAgent(config={"test_mode": True})
        instructions = "Custom instructions for testing"

        adapter = APEGAgentAdapter(agent, instructions=instructions)

        assert adapter.instructions == instructions

    def test_to_sdk_agent_creates_agent(self):
        """Test to_sdk_agent() creates valid SDK Agent."""
        agent = ShopifyAgent(config={"test_mode": True})
        adapter = APEGAgentAdapter(agent)

        sdk_agent = adapter.to_sdk_agent()

        assert sdk_agent is not None
        assert sdk_agent.name == "ShopifyAgent"
        assert len(sdk_agent.tools) > 0

    def test_to_sdk_agent_caches_result(self):
        """Test to_sdk_agent() caches the SDK agent."""
        agent = ShopifyAgent(config={"test_mode": True})
        adapter = APEGAgentAdapter(agent)

        sdk_agent1 = adapter.to_sdk_agent()
        sdk_agent2 = adapter.sdk_agent

        # The cached agent should be the same
        assert sdk_agent2 is sdk_agent1

    def test_create_with_handoffs(self):
        """Test create_with_handoffs configures handoffs."""
        shopify = ShopifyAgent(config={"test_mode": True})
        etsy = EtsyAgent(config={"test_mode": True})

        # Create adapters
        shopify_adapter = APEGAgentAdapter(shopify)
        etsy_adapter = APEGAgentAdapter(etsy)

        # Configure shopify to hand off to etsy
        shopify_sdk = shopify_adapter.create_with_handoffs([etsy_adapter])

        assert len(shopify_sdk.handoffs) == 1
        assert shopify_sdk.handoffs[0].name == "EtsyAgent"

    def test_get_capabilities(self):
        """Test get_capabilities returns agent capabilities."""
        agent = ShopifyAgent(config={"test_mode": True})
        adapter = APEGAgentAdapter(agent)

        capabilities = adapter.get_capabilities()

        assert len(capabilities) > 0
        assert 'list_products' in capabilities


class TestSDKAgentWrapper:
    """Test SDKAgentWrapper makes SDK agents APEG-compatible."""

    def test_wrapper_initialization(self):
        """Test wrapper initializes with SDK agent."""
        sdk_agent = Agent(name="Test", instructions="Test agent")
        wrapper = SDKAgentWrapper(sdk_agent)

        assert wrapper.sdk_agent is sdk_agent
        assert wrapper.name == "Test"

    def test_wrapper_name_property(self):
        """Test wrapper has name property from SDK agent."""
        sdk_agent = Agent(name="MyAgent", instructions="Test")
        wrapper = SDKAgentWrapper(sdk_agent)

        assert wrapper.name == "MyAgent"

    def test_execute_interface_exists(self):
        """Test wrapper has APEG-compatible execute interface."""
        sdk_agent = Agent(name="Test", instructions="You are helpful")
        wrapper = SDKAgentWrapper(sdk_agent)

        # Verify execute method exists with correct signature
        import inspect
        sig = inspect.signature(wrapper.execute)

        assert 'action' in sig.parameters or len(sig.parameters) >= 2
        assert 'context' in sig.parameters or len(sig.parameters) >= 2

    def test_describe_capabilities(self):
        """Test describe_capabilities returns list."""
        sdk_agent = Agent(name="Test", instructions="Test")
        wrapper = SDKAgentWrapper(sdk_agent)

        capabilities = wrapper.describe_capabilities()

        assert isinstance(capabilities, list)
        assert len(capabilities) > 0

    def test_execute_in_test_mode(self):
        """Test execute returns proper result in test mode."""
        sdk_agent = Agent(name="TestAgent", instructions="Test")
        wrapper = SDKAgentWrapper(sdk_agent, config={"test_mode": True})

        result = wrapper.execute("test_action", {"prompt": "Do something"})

        assert result['status'] == 'completed'
        assert 'test_mode' in result or 'TEST MODE' in str(result.get('output', ''))
        assert result['agent_name'] == "TestAgent"


class TestHandoffCoordinator:
    """Test HandoffCoordinator manages agent registration and handoffs."""

    def test_coordinator_initialization(self):
        """Test coordinator initializes empty."""
        coordinator = HandoffCoordinator()

        assert coordinator.registered_agents == {}

    def test_register_apeg_agent(self):
        """Test register_apeg_agent adds agent."""
        coordinator = HandoffCoordinator()
        agent = ShopifyAgent(config={"test_mode": True})

        adapter = coordinator.register_apeg_agent("shopify", agent)

        assert "shopify" in coordinator.registered_agents
        assert coordinator.registered_agents["shopify"] == "apeg"
        assert adapter is not None

    def test_register_sdk_agent(self):
        """Test register_sdk_agent adds agent."""
        coordinator = HandoffCoordinator()
        sdk_agent = Agent(name="Test", instructions="Test")

        coordinator.register_sdk_agent("test", sdk_agent)

        assert "test" in coordinator.registered_agents
        assert coordinator.registered_agents["test"] == "sdk"

    def test_get_agent_returns_apeg_agent(self):
        """Test get_agent returns registered APEG agent."""
        coordinator = HandoffCoordinator()
        agent = ShopifyAgent(config={"test_mode": True})
        coordinator.register_apeg_agent("shopify", agent)

        retrieved = coordinator.get_agent("shopify")

        assert retrieved is agent

    def test_get_agent_returns_sdk_agent(self):
        """Test get_agent returns registered SDK agent."""
        coordinator = HandoffCoordinator()
        sdk_agent = Agent(name="Test", instructions="Test")
        coordinator.register_sdk_agent("test", sdk_agent)

        retrieved = coordinator.get_agent("test")

        assert retrieved is sdk_agent

    def test_get_adapter(self):
        """Test get_adapter returns adapter for APEG agent."""
        coordinator = HandoffCoordinator()
        agent = ShopifyAgent(config={"test_mode": True})
        coordinator.register_apeg_agent("shopify", agent)

        adapter = coordinator.get_adapter("shopify")

        assert adapter is not None
        assert isinstance(adapter, APEGAgentAdapter)

    def test_create_triage_agent(self):
        """Test create_triage_agent creates agent with handoffs."""
        coordinator = HandoffCoordinator()
        coordinator.register_apeg_agent(
            "shopify",
            ShopifyAgent(config={"test_mode": True})
        )
        coordinator.register_apeg_agent(
            "etsy",
            EtsyAgent(config={"test_mode": True})
        )

        triage = coordinator.create_triage_agent(name="Triage")

        assert triage.name == "Triage"
        assert len(triage.handoffs) == 2

    def test_context_management(self):
        """Test context set/get/clear operations."""
        coordinator = HandoffCoordinator()

        coordinator.set_context("key1", "value1")
        assert coordinator.get_context("key1") == "value1"
        assert coordinator.get_context("missing", "default") == "default"

        coordinator.clear_context()
        assert coordinator.get_context("key1") is None

    def test_describe(self):
        """Test describe returns coordinator state."""
        coordinator = HandoffCoordinator()
        coordinator.register_apeg_agent(
            "shopify",
            ShopifyAgent(config={"test_mode": True})
        )

        desc = coordinator.describe()

        assert 'apeg_agents' in desc
        assert 'sdk_agents' in desc
        assert 'total_agents' in desc
        assert desc['total_agents'] == 1


class TestEndToEndIntegration:
    """Test end-to-end SDK integration scenarios."""

    def test_apeg_to_sdk_roundtrip(self):
        """Test round-trip: APEG -> SDK -> APEG."""
        # Start with APEG agent
        original_agent = ShopifyAgent(config={"test_mode": True})

        # Convert to SDK
        adapter = APEGAgentAdapter(original_agent)
        sdk_agent = adapter.to_sdk_agent()

        # Wrap back for APEG
        wrapped = SDKAgentWrapper(sdk_agent, config={"test_mode": True})

        # Verify wrapped agent has APEG interface
        assert hasattr(wrapped, 'execute')
        assert hasattr(wrapped, 'name')
        assert hasattr(wrapped, 'describe_capabilities')

    def test_coordinator_multi_agent_setup(self):
        """Test coordinator with multiple agents."""
        coordinator = HandoffCoordinator()

        # Register multiple APEG agents
        coordinator.register_apeg_agent(
            "shopify",
            ShopifyAgent(config={"test_mode": True}),
            instructions="Handle Shopify operations"
        )
        coordinator.register_apeg_agent(
            "etsy",
            EtsyAgent(config={"test_mode": True}),
            instructions="Handle Etsy operations"
        )

        # Register SDK agent
        coordinator.register_sdk_agent(
            "assistant",
            Agent(name="Assistant", instructions="General assistance")
        )

        # Verify all registered
        agents = coordinator.registered_agents
        assert len(agents) == 3
        assert agents["shopify"] == "apeg"
        assert agents["etsy"] == "apeg"
        assert agents["assistant"] == "sdk"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
