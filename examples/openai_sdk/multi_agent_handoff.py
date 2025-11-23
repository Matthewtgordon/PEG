#!/usr/bin/env python3
"""
Multi-agent handoff example.

Demonstrates:
- Creating multiple APEG agents (Shopify, Etsy)
- Wrapping each as SDK agents
- Using HandoffCoordinator to manage agents
- Creating a triage agent that routes to specialists
"""

import sys
sys.path.insert(0, 'src')

from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.agents.etsy_agent import EtsyAgent
from apeg_core.sdk_integration import (
    APEGAgentAdapter,
    HandoffCoordinator,
)


def main():
    print("=" * 70)
    print("EXAMPLE 2: Multi-Agent Handoff (Shopify <-> Etsy)")
    print("=" * 70)

    # Create APEG domain agents
    print("\n1. Creating APEG domain agents...")
    shopify_agent = ShopifyAgent(config={"test_mode": True})
    etsy_agent = EtsyAgent(config={"test_mode": True})
    print("   Created ShopifyAgent")
    print("   Created EtsyAgent")

    # Show capabilities of each agent
    print("\n2. Agent capabilities:")
    print("   Shopify:")
    for cap in shopify_agent.describe_capabilities()[:5]:
        print(f"   - {cap}")
    print("   Etsy:")
    for cap in etsy_agent.describe_capabilities()[:5]:
        print(f"   - {cap}")

    # Create HandoffCoordinator
    print("\n3. Creating HandoffCoordinator...")
    coordinator = HandoffCoordinator()

    # Register agents
    print("\n4. Registering agents with coordinator...")
    coordinator.register_apeg_agent(
        "shopify",
        shopify_agent,
        instructions="Handle Shopify store operations including products, inventory, and orders."
    )
    coordinator.register_apeg_agent(
        "etsy",
        etsy_agent,
        instructions="Handle Etsy marketplace operations including listings, inventory, and orders."
    )

    # Show registered agents
    registered = coordinator.registered_agents
    print(f"   Registered {len(registered)} agents:")
    for name, agent_type in registered.items():
        print(f"   - {name}: {agent_type}")

    # Create triage agent
    print("\n5. Creating triage agent with handoffs...")
    triage = coordinator.create_triage_agent(
        name="E-commerce Triage",
        instructions="""You are a triage agent for e-commerce operations.

Based on the user's question, hand off to the appropriate specialist:
- Hand off to shopify for Shopify store questions
- Hand off to etsy for Etsy marketplace questions

If the question involves both platforms, choose the primary one mentioned."""
    )

    print(f"   Triage agent: {triage.name}")
    print(f"   Available handoffs: {len(triage.handoffs)}")
    for h in triage.handoffs:
        print(f"   - {h.name}")

    # Demonstrate adapter creation with handoffs
    print("\n6. Demonstrating cross-platform handoffs...")
    shopify_adapter = coordinator.get_adapter("shopify")
    etsy_adapter = coordinator.get_adapter("etsy")

    if shopify_adapter and etsy_adapter:
        # Create Shopify agent that can hand off to Etsy
        shopify_sdk = shopify_adapter.create_with_handoffs([etsy_adapter])
        print(f"   ShopifyAgent SDK can hand off to {len(shopify_sdk.handoffs)} agent(s)")

    # Show coordinator state
    print("\n7. Coordinator state:")
    state = coordinator.describe()
    print(f"   APEG agents: {state['apeg_agents']}")
    print(f"   SDK agents: {state['sdk_agents']}")
    print(f"   Total agents: {state['total_agents']}")

    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)
    print("\nKey concepts demonstrated:")
    print("- HandoffCoordinator manages multiple agents")
    print("- Triage agent routes to appropriate specialists")
    print("- Agents can hand off to each other for cross-platform ops")
    print("=" * 70)


if __name__ == "__main__":
    main()
