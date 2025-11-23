#!/usr/bin/env python3
"""
Basic example: Wrap APEG agent as OpenAI SDK agent.

Demonstrates:
- Creating APEG agent (Shopify)
- Wrapping with APEGAgentAdapter
- Using ToolBridge to extract tools
- Showing available tools from agent methods
"""

import sys
sys.path.insert(0, 'src')

from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.sdk_integration import APEGAgentAdapter, ToolBridge


def main():
    print("=" * 70)
    print("EXAMPLE 1: Basic APEG Agent -> SDK Agent Adapter")
    print("=" * 70)

    # Create APEG Shopify agent in test mode
    print("\n1. Creating APEG Shopify agent (test mode)...")
    shopify_agent = ShopifyAgent(config={"test_mode": True})
    print(f"   Created {shopify_agent.__class__.__name__}")

    # Show APEG capabilities
    print("\n2. APEG agent capabilities:")
    capabilities = shopify_agent.describe_capabilities()
    for cap in capabilities:
        print(f"   - {cap}")

    # Create ToolBridge and show tool schemas
    print("\n3. Creating ToolBridge to extract tools...")
    bridge = ToolBridge(shopify_agent)
    tools = bridge.create_tools()
    print(f"   Created {len(tools)} SDK tools")

    # List tools
    print("\n4. Available SDK tools (from APEG agent methods):")
    for i, tool in enumerate(tools, 1):
        name = getattr(tool, '__name__', str(tool))
        doc = getattr(tool, '__doc__', '')
        print(f"   {i}. {name}")
        if doc:
            print(f"      Description: {doc[:60]}...")

    # Wrap as SDK agent
    print("\n5. Wrapping APEG agent as SDK agent...")
    adapter = APEGAgentAdapter(shopify_agent)
    sdk_agent = adapter.to_sdk_agent()
    print(f"   SDK Agent name: {sdk_agent.name}")
    print(f"   SDK Agent tools: {len(sdk_agent.tools)}")

    # Show SDK agent instructions
    print("\n6. SDK Agent instructions preview:")
    instructions = sdk_agent.instructions
    if len(instructions) > 200:
        print(f"   {instructions[:200]}...")
    else:
        print(f"   {instructions}")

    # Test calling an APEG method directly
    print("\n7. Testing APEG agent method directly (test mode)...")
    products = shopify_agent.list_products(limit=2)
    print(f"   list_products returned {len(products)} products:")
    for p in products:
        print(f"   - {p['title']} (${p['price']})")

    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)
    print("\nKey concepts demonstrated:")
    print("- APEGAgentAdapter wraps APEG agents as SDK agents")
    print("- ToolBridge automatically converts methods to SDK tools")
    print("- Agent capabilities become callable tools in SDK")
    print("=" * 70)


if __name__ == "__main__":
    main()
