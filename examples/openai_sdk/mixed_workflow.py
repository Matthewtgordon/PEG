#!/usr/bin/env python3
"""
Mixed workflow example combining APEG orchestrator with SDK agents.

Demonstrates:
- Using SDKAgentWrapper to make SDK agents APEG-compatible
- Using both native APEG agents and wrapped SDK agents
- Executing tasks through both agent types
"""

import sys
sys.path.insert(0, 'src')

from agents import Agent as SDKAgent

from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.sdk_integration import SDKAgentWrapper, APEGAgentAdapter


def main():
    print("=" * 70)
    print("EXAMPLE 3: Mixed APEG + SDK Agent Workflow")
    print("=" * 70)

    # Create native APEG domain agent
    print("\n1. Creating native APEG domain agent (Shopify)...")
    shopify_agent = ShopifyAgent(config={"test_mode": True})
    print(f"   Created {shopify_agent.name}")

    # Create SDK agent directly
    print("\n2. Creating SDK agent (Customer Service)...")
    customer_service_sdk = SDKAgent(
        name="CustomerService",
        instructions="""You are a customer service agent for an e-commerce business.
Help customers with questions about orders, products, and policies.
Be friendly and professional."""
    )
    print(f"   Created SDK agent: {customer_service_sdk.name}")

    # Wrap SDK agent for APEG compatibility
    print("\n3. Wrapping SDK agent for APEG compatibility...")
    wrapped_sdk_agent = SDKAgentWrapper(
        customer_service_sdk,
        config={"test_mode": True}
    )
    print(f"   Wrapped agent name: {wrapped_sdk_agent.name}")
    print(f"   APEG interface: execute(), describe_capabilities()")

    # Show that wrapped agent has APEG interface
    print("\n4. Verifying APEG interface...")
    print(f"   Agent name property: {wrapped_sdk_agent.name}")
    print(f"   Capabilities: {wrapped_sdk_agent.describe_capabilities()}")

    # Compare agent types
    print("\n5. Comparing agent types:")
    print(f"   Native APEG (Shopify):")
    print(f"   - Type: {type(shopify_agent).__name__}")
    print(f"   - Has execute(): {hasattr(shopify_agent, 'execute')}")
    print(f"   - Has describe_capabilities(): {hasattr(shopify_agent, 'describe_capabilities')}")

    print(f"\n   Wrapped SDK (CustomerService):")
    print(f"   - Type: {type(wrapped_sdk_agent).__name__}")
    print(f"   - Has execute(): {hasattr(wrapped_sdk_agent, 'execute')}")
    print(f"   - Has describe_capabilities(): {hasattr(wrapped_sdk_agent, 'describe_capabilities')}")

    # Execute using APEG interface
    print("\n6. Executing via APEG interface (test mode)...")

    print("\n   Step 1: Customer service agent handles inquiry...")
    result = wrapped_sdk_agent.execute(
        action="inquiry",
        context={"prompt": "Customer asks: Is the Blue Sapphire ring available?"}
    )
    print(f"   Status: {result.get('status')}")
    if result.get('output'):
        output = str(result['output'])
        print(f"   Response: {output[:80]}...")

    print("\n   Step 2: Shopify agent checks inventory...")
    shopify_result = shopify_agent.execute(
        "product_sync",
        {"product_id": "ring-123"}
    )
    print(f"   Status: {shopify_result.get('status')}")
    print(f"   Product: {shopify_result.get('title', 'N/A')}")

    # Show direct method calls on APEG agent
    print("\n7. Direct method calls on APEG agent...")
    products = shopify_agent.list_products(limit=2)
    print(f"   list_products returned {len(products)} products:")
    for p in products:
        print(f"   - {p['title']}: ${p['price']} (inventory: {p['inventory']})")

    # Demonstrate round-trip conversion
    print("\n8. Demonstrating round-trip conversion...")
    print("   APEG -> SDK -> APEG")

    # Convert Shopify to SDK
    adapter = APEGAgentAdapter(shopify_agent)
    shopify_sdk = adapter.to_sdk_agent()
    print(f"   Step 1: ShopifyAgent -> SDK: {shopify_sdk.name}")

    # Wrap back to APEG
    rewrapped = SDKAgentWrapper(shopify_sdk, config={"test_mode": True})
    print(f"   Step 2: SDK -> APEG wrapper: {rewrapped.name}")
    print(f"   Step 3: APEG interface preserved: {hasattr(rewrapped, 'execute')}")

    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)
    print("\nKey concepts demonstrated:")
    print("- SDKAgentWrapper makes SDK agents APEG-compatible")
    print("- Both agent types have same APEG interface")
    print("- Round-trip conversion preserves functionality")
    print("- Mixed workflows use consistent interface")
    print("=" * 70)


if __name__ == "__main__":
    main()
