from typing import Optional

from agents import Runner  # from `openai-agents` package

from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.sdk_integration.handoff_coordinator import HandoffCoordinator


TRIAGE_INSTRUCTIONS = """
You are a Shopify inventory assistant for a single small jewelry store.

- The user speaks in natural language.
- You are allowed to call tools on the underlying Shopify agent to:
  - list products
  - look up a product and its variants
  - update inventory quantities for a given product variant
- When the user says things like:
  - "show products" or "what do we have in stock"
  - "set the Cable / Medium variant of the Tanzanite anklet to 5"
  - "add 3 large Tanzanite ankle bracelets"
  infer the correct product and variant and call the appropriate inventory tool.
- Always describe what you did in plain English in your final answer.
- If you are not sure which product/variant they mean, ask a follow-up question instead of guessing.
""".strip()


def build_triage_agent() -> "object":
    """
    Build a single OpenAI Agents SDK agent that knows how to talk
    to the APEG ShopifyAgent via the handoff coordinator.
    """
    # This uses the same env + test_mode you already configured.
    shopify = ShopifyAgent()

    coordinator = HandoffCoordinator()

    # Register Shopify as the only domain agent for now.
    coordinator.register_apeg_agent(
        name="shopify",
        agent=shopify,
        instructions=(
            "You are the Shopify domain agent. You perform real API calls "
            "for listing products and updating inventory."
        ),
    )

    # Build the triage agent that the LLM will interact with.
    triage_agent = coordinator.create_triage_agent(
        name="apeg-shopify-triage",
        instructions=TRIAGE_INSTRUCTIONS,
    )

    return triage_agent


def main() -> None:
    triage_agent = build_triage_agent()

    print("APEG Shopify NL agent ready.")
    print("Type natural-language commands. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if user_text.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not user_text:
            continue

        # Run a short interaction using the OpenAI Agents runner.
        result = Runner.run_sync(
            triage_agent,
            input=user_text,
            max_turns=4,
        )

        print("\nAgent:")
        print(result.final_output)
        print("-" * 40)


if __name__ == "__main__":
    main()
