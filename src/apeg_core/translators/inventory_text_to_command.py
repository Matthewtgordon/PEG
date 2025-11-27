"""
Inventory text-to-command translator.

Converts natural language inventory requests into structured InventoryCommand dicts
that can be executed by apeg_core.services.shopify_inventory_service.execute_inventory_command.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from openai import OpenAI


# This module translates natural language into the InventoryCommand dict
# expected by apeg_core.services.shopify_inventory_service.execute_inventory_command.


INVENTORY_COMMAND_SCHEMA_DOC = """
You act as a translator. You NEVER execute actions yourself.
You ONLY return JSON matching this schema, nothing else:

{
  "task_type": "inventory_update",
  "store": "dev",
  "product_title": "string",
  "variants": [
    {
      "variant_label": "string",      // e.g. "Medium", "Large", "Cable / Medium"
      "new_quantity": integer         // final absolute quantity
    }
  ]
}

Rules:
- task_type MUST be exactly "inventory_update".
- store MUST be "dev" for now.
- product_title MUST be a string that can match the Shopify product title
  (substring match, case-insensitive) such as:
  "TEST - Handmade Sterling Silver Beaded Ankle Bracelets  | Birthstone Tanzanite December"
  or a meaningful substring like "Tanzanite ankle bracelet".
- variants MUST be a non-empty list.
- Each new_quantity MUST be an integer >= 0 (final absolute count).
- If the user gives a single number for "anklets" without variant split,
  you MAY either:
    - assign that number to a single sensible variant_label (like "Medium"), OR
    - ask for clarification (but for this translator, prefer making a best-effort guess).
- If you cannot infer anything reasonable, still output valid JSON with:
    - an empty variants list, OR
    - new_quantity = 0 and a comment in a "note" field (but only if asked to add notes).

OUTPUT FORMAT:
- Return ONLY valid JSON (no comments, no trailing commas, no extra text).
- Do NOT wrap the JSON in backticks.
- Do NOT add explanations outside the JSON.
""".strip()


def build_inventory_command_from_text(user_text: str) -> Dict[str, Any]:
    """
    Use the OpenAI API to translate natural language into an InventoryCommand dict.

    This function:
    - Calls a chat model with a strict system prompt and the user_text.
    - Parses the returned JSON.
    - Returns the parsed dict.

    Args:
        user_text: Natural language description of the inventory update request.

    Returns:
        A dictionary matching the InventoryCommand schema with keys:
        - task_type: "inventory_update"
        - store: "dev"
        - product_title: str
        - variants: List[Dict[str, Any]] with variant_label and new_quantity

    Raises:
        ValueError: If the response cannot be parsed as JSON or if the API key is missing.
        Exception: If the OpenAI API call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Please set it to use the inventory translator."
        )

    client = OpenAI(api_key=api_key)

    messages = [
        {
            "role": "system",
            "content": INVENTORY_COMMAND_SCHEMA_DOC,
        },
        {
            "role": "user",
            "content": user_text,
        },
    ]

    # Model choice can be adjusted later; keep it explicit.
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from inventory translator model")

    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        command = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Translator output was not valid JSON: {e}\nContent: {content}") from e

    # Basic sanity checks
    if not isinstance(command, dict):
        raise ValueError(f"Translator output was not a dict: {type(command)}")

    if command.get("task_type") != "inventory_update":
        raise ValueError(f"Invalid task_type: {command.get('task_type')}")

    if not isinstance(command.get("variants"), list):
        raise ValueError("Missing or invalid 'variants' list in translator output")

    return command


def format_inventory_result(result: Dict[str, Any]) -> str:
    """
    Format the result from execute_inventory_command() into a human-readable summary.

    Args:
        result: The result dict from execute_inventory_command()

    Returns:
        A formatted string summarizing the inventory update results.
    """
    lines = []
    lines.append(f"Status: {result.get('status', 'unknown')}")
    lines.append(f"Store: {result.get('store', 'unknown')}")
    lines.append(f"Product: {result.get('product_title', 'unknown')}")
    lines.append(f"Product ID: {result.get('product_id', 'unknown')}")
    lines.append("")
    lines.append("Variant Updates:")

    updates = result.get("updates", [])
    if not updates:
        lines.append("  (no updates)")
    else:
        for upd in updates:
            label = upd.get("variant_label", "unknown")
            variant_id = upd.get("variant_id", "unknown")
            update_result = upd.get("update_result", {})

            lines.append(f"  - {label} (ID: {variant_id})")

            if isinstance(update_result, dict):
                status = update_result.get("status", "unknown")
                old_qty = update_result.get("old_quantity", "?")
                new_qty = update_result.get("new_quantity", "?")
                lines.append(f"    Status: {status}")
                lines.append(f"    Quantity: {old_qty} → {new_qty}")
            else:
                lines.append(f"    Result: {update_result}")

    return "\n".join(lines)
