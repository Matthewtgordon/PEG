from typing import Dict, Any, List

from apeg_core.agents.shopify_agent import ShopifyAgent
from apeg_core.schemas.inventory_commands import (
    InventoryUpdateCommand,
    InventoryQueryCommand,
    parse_inventory_context,
    InventoryContextParseError,
)


class InventoryCommandError(Exception):
    pass


def _resolve_product(agent: ShopifyAgent, title_filter: str) -> Dict[str, Any]:
    """
    Find a product whose title contains the given filter string (case-insensitive).
    Returns the first matching product summary dict from list_products().
    """
    products = agent.list_products()
    if not isinstance(products, list):
        raise InventoryCommandError("ShopifyAgent.list_products() did not return a list")

    matches = [
        p for p in products
        if title_filter.lower() in str(p.get("title", "")).lower()
    ]
    if not matches:
        raise InventoryCommandError(f"No product found matching title filter: {title_filter!r}")

    # For now: first match
    return matches[0]


def _resolve_variant(full_product: Dict[str, Any], variant_label: str) -> str:
    """
    Find a variant whose title contains the given label (case-insensitive).
    Returns the variant ID.
    """
    variants: List[Dict[str, Any]] = full_product.get("variants") or []
    for v in variants:
        title = str(v.get("title", "")).lower()
        if variant_label.lower() in title:
            vid = v.get("id")
            if not vid:
                continue
            return vid

    raise InventoryCommandError(
        f"No variant found matching label {variant_label!r} "
        f"in product {full_product.get('title', '<unknown>')!r}"
    )


def execute_inventory_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an InventoryCommand against Shopify via ShopifyAgent.

    Schema Reference:
    -----------------
    The canonical schema for inventory commands is defined in:
    apeg_core.schemas.inventory_commands.InventoryUpdateCommand

    You can validate commands using:
    - parse_inventory_context(command) to get a typed InventoryUpdateCommand
    - Or pass a plain dict matching the schema (as shown below)

    Expected command shape (v1):

    {
        "task_type": "inventory_update",
        "store": "dev",  # for now we assume env already selects the store
        "product_title": "TEST - ... Tanzanite December",
        "variants": [
            {
                "variant_label": "Cable / Medium",
                "new_quantity": 2
            },
            {
                "variant_label": "Cable / Large",
                "new_quantity": 1
            }
        ]
    }

    Returns a result dict with status and per-variant update results.
    """
    if command.get("task_type") != "inventory_update":
        raise InventoryCommandError(f"Unsupported task_type: {command.get('task_type')!r}")

    # In future, "store" could select different domains/tokens.
    store = command.get("store", "dev")

    agent = ShopifyAgent()  # uses existing env + test_mode setup

    product_title_filter = command.get("product_title")
    if not product_title_filter:
        raise InventoryCommandError("Missing 'product_title' in inventory command")

    # 1) resolve product
    product_summary = _resolve_product(agent, product_title_filter)
    product_id = product_summary["id"]

    # 2) get full product details (for variants)
    full_product = agent.get_product(product_id)
    variants_spec = command.get("variants") or []

    if not variants_spec:
        raise InventoryCommandError("No 'variants' list provided in inventory command")

    updates: List[Dict[str, Any]] = []

    for vcmd in variants_spec:
        label = vcmd.get("variant_label")
        if not label:
            raise InventoryCommandError("Variant entry missing 'variant_label'")

        try:
            new_qty = int(vcmd.get("new_quantity"))
        except (TypeError, ValueError):
            raise InventoryCommandError(
                f"Invalid 'new_quantity' for variant {label!r}: {vcmd.get('new_quantity')!r}"
            )

        variant_id = _resolve_variant(full_product, label)

        update_result = agent.update_inventory(
            product_id=product_id,
            variant_id=variant_id,
            new_quantity=new_qty,
        )
        updates.append({
            "variant_label": label,
            "variant_id": variant_id,
            "update_result": update_result,
        })

    return {
        "status": "success",
        "store": store,
        "product_id": product_id,
        "product_title": full_product.get("title"),
        "updates": updates,
    }
