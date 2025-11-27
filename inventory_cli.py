#!/usr/bin/env python3
"""
Inventory CLI - Natural language to inventory command translator and executor.

Usage:
    python inventory_cli.py

    Then enter natural language inventory requests at the prompt.
    Examples:
    - "Update Tanzanite ankle bracelet: Medium to 3, Large to 5"
    - "Set Tanzanite anklets Cable/Medium to 2, Cable/Large to 1"
    - "I need to set the Tanzanite December ankle bracelet inventory to: Medium = 3, Large = 4"

    Type 'quit' or 'exit' to exit.

Requirements:
    - OPENAI_API_KEY environment variable must be set
    - Shopify environment variables must be set (for execution)
"""
from __future__ import annotations

import sys
import os
from typing import Any, Dict

# Add src to path if running from repo root
if os.path.exists("src"):
    sys.path.insert(0, os.path.abspath("."))

from src.apeg_core.translators.inventory_text_to_command import (
    build_inventory_command_from_text,
    format_inventory_result,
)
from src.apeg_core.services.shopify_inventory_service import (
    execute_inventory_command,
    InventoryCommandError,
)


def print_banner():
    """Print welcome banner."""
    print("=" * 70)
    print("  INVENTORY CLI - Natural Language Inventory Update Tool")
    print("=" * 70)
    print()
    print("Enter natural language inventory requests.")
    print("Examples:")
    print('  - "Update Tanzanite ankle bracelet: Medium to 3, Large to 5"')
    print('  - "Set Tanzanite anklets Cable/Medium to 2, Cable/Large to 1"')
    print()
    print("Type 'quit' or 'exit' to exit.")
    print("Type 'dry-run <text>' to see the translated command without executing.")
    print()
    print("-" * 70)
    print()


def handle_request(user_input: str, dry_run: bool = False) -> None:
    """
    Handle a single inventory request.

    Args:
        user_input: Natural language inventory request
        dry_run: If True, only translate but don't execute
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {user_input}")
    print("-" * 70)

    try:
        # Step 1: Translate to command
        print("\n[1] Translating natural language to InventoryCommand...")
        command = build_inventory_command_from_text(user_input)

        print("\n[2] Generated command:")
        import json
        print(json.dumps(command, indent=2))

        if dry_run:
            print("\n[DRY RUN] Skipping execution.")
            return

        # Step 2: Execute command
        print("\n[3] Executing inventory command...")
        result = execute_inventory_command(command)

        # Step 3: Format and display result
        print("\n[4] Result:")
        print(format_inventory_result(result))

    except InventoryCommandError as e:
        print(f"\n❌ Inventory Command Error: {e}")
    except ValueError as e:
        print(f"\n❌ Translation Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70 + "\n")


def interactive_mode():
    """Run in interactive mode with prompt."""
    print_banner()

    while True:
        try:
            user_input = input("📦 Enter inventory request (or 'quit' to exit): ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            # Check for dry-run mode
            dry_run = False
            if user_input.lower().startswith("dry-run "):
                dry_run = True
                user_input = user_input[8:].strip()

            handle_request(user_input, dry_run=dry_run)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break


def stdin_mode():
    """Read from stdin and process a single request."""
    user_input = sys.stdin.read().strip()
    if not user_input:
        print("Error: No input provided", file=sys.stderr)
        sys.exit(1)

    handle_request(user_input, dry_run=False)


def main():
    """Main entry point."""
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        print("Please set your OpenAI API key to use the translator.", file=sys.stderr)
        sys.exit(1)

    # Determine mode based on whether stdin is a terminal
    if sys.stdin.isatty():
        # Interactive mode
        interactive_mode()
    else:
        # Stdin mode (piped input)
        stdin_mode()


if __name__ == "__main__":
    main()
