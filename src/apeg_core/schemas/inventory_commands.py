"""
APEG Shopify Inventory Command Schemas

Purpose
-------
Define a stable, type-checked schema for inventory-related commands
that travel between:

- Web UI or external GPTs
- APEG orchestrator `/run` endpoint
- Shopify inventory services (e.g., shopify_inventory_service)

This file does NOT depend on OpenAI Agents SDK.
It is purely about data shapes and validation.

Intended usage
--------------
1) Web UI / external caller:
   POST /run with JSON body like:

   {
     "goal": "Update Shopify inventory",
     "context": {
       "task_type": "inventory_update",
       "store": "dev",
       "product_title": "TEST - Handmade Sterling Silver Beaded Ankle Bracelets  | Birthstone Tanzanite December",
       "variants": [
         { "variant_label": "Medium", "new_quantity": 2 },
         { "variant_label": "Large",  "new_quantity": 1 }
       ]
     }
   }

2) APEG orchestrator / server:
   - Extract `context` from the /run payload.
   - Validate it using these models.
   - Route to a Shopify inventory service:
       shopify_inventory_service.execute_inventory_command(context_dict)

3) Shopify inventory service:
   - Treat the validated context as the contract for
     read/write operations.

Notes
-----
- This module is deliberately small and stable.
- It is safe to extend with additional fields later
  (e.g., tags, SKU filters) without breaking existing callers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, root_validator, validator


# ---------------------------------------------------------------------------
# Core inventory command models
# ---------------------------------------------------------------------------

class VariantUpdate(BaseModel):
    """
    Represents a requested quantity for a specific variant.
    """
    variant_label: str = Field(
        ...,
        description=(
            "Human label for the variant, e.g. 'Medium', 'Large', "
            "'Cable / Medium', etc. Used to resolve variant_id."
        ),
    )
    new_quantity: int = Field(
        ...,
        ge=0,
        description="New absolute inventory quantity for this variant.",
    )


class InventoryUpdateCommand(BaseModel):
    """
    Structured inventory update command.

    This is the canonical shape for:
    context = {
        "task_type": "inventory_update",
        "store": "dev",
        "product_title": "...",
        "variants": [
            { "variant_label": "Medium", "new_quantity": 2 },
            { "variant_label": "Large",  "new_quantity": 1 }
        ]
    }

    Fields
    ------
    task_type:
        Must be the literal string 'inventory_update'. This is used
        by the orchestrator to route to the correct domain service.

    store:
        Logical store identifier. For now typical values will be:
        - 'dev' for your demo / sandbox store
        - 'prod' or 'live' for your real Shopify store

    product_title:
        Human-readable Shopify product title used as the primary
        filter for resolving the product. This should match what
        you see in the Shopify Admin UI.

    variants:
        List of VariantUpdate objects specifying desired quantities
        by variant label.
    """

    task_type: Literal["inventory_update"] = Field(
        "inventory_update",
        description="Discriminator used by APEG to route inventory flows.",
    )
    store: str = Field(
        ...,
        description="Logical store key, e.g. 'dev', 'prod', 'live'.",
    )
    product_title: str = Field(
        ...,
        min_length=1,
        description="Full Shopify product title to match against.",
    )
    variants: List[VariantUpdate] = Field(
        ...,
        min_items=1,
        description="List of variant updates to apply.",
    )

    @validator("store")
    def normalize_store(cls, value: str) -> str:
        # Keep simple; normalize to lower-case to avoid trivial mismatches.
        return value.strip().lower()

    @root_validator
    def check_variants_non_empty(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        variants = values.get("variants") or []
        if not variants:
            raise ValueError("At least one variant update is required.")
        return values

    def to_context_dict(self) -> Dict[str, Any]:
        """
        Convert the command into a plain dict suitable for passing
        into shopify_inventory_service.execute_inventory_command().
        """
        return {
            "task_type": self.task_type,
            "store": self.store,
            "product_title": self.product_title,
            "variants": [v.dict() for v in self.variants],
        }


class InventoryQueryCommand(BaseModel):
    """
    Optional read-only inventory query.

    This is a planned extension to support natural-language queries like:
    - "How many anklets do we have in stock?"
    - "Show inventory for Tanzanite ankle bracelets."

    Shape example:

    {
      "task_type": "inventory_query",
      "store": "dev",
      "product_title_contains": "Tanzanite ankle bracelet"
    }

    For now, you can treat this as a schema-only definition.
    The implementation in services can follow later.
    """

    task_type: Literal["inventory_query"] = Field(
        "inventory_query",
        description="Discriminator for read-only inventory queries.",
    )
    store: str = Field(
        ...,
        description="Logical store key, e.g. 'dev', 'prod', 'live'.",
    )
    product_title_contains: Optional[str] = Field(
        None,
        description="Substring filter applied to product title.",
    )
    # Future filters can be added here:
    # sku: Optional[str] = None
    # status: Optional[str] = None

    @validator("store")
    def normalize_store(cls, value: str) -> str:
        return value.strip().lower()

    @root_validator
    def at_least_one_filter(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get("product_title_contains"):
            raise ValueError(
                "InventoryQueryCommand requires at least one filter "
                "(e.g., product_title_contains)."
            )
        return values

    def to_context_dict(self) -> Dict[str, Any]:
        """
        Convert the query into a plain dict for services that expect
        a generic context payload.
        """
        return {
            "task_type": self.task_type,
            "store": self.store,
            "product_title_contains": self.product_title_contains,
        }


# ---------------------------------------------------------------------------
# Helper to parse generic /run context into a specific inventory model
# ---------------------------------------------------------------------------

class InventoryContextParseError(Exception):
    """Raised when a generic context dict cannot be parsed into a known inventory command."""


def parse_inventory_context(context: Dict[str, Any]) -> InventoryUpdateCommand | InventoryQueryCommand:
    """
    Inspect a generic context dict (from /run payload) and return a
    typed inventory command model.

    This function does NOT know anything about HTTP or FastAPI.
    It is only used to cleanly separate APEG routing from service
    implementation.

    Example:
        cmd = parse_inventory_context(run_payload["context"])
        if isinstance(cmd, InventoryUpdateCommand):
            # route to inventory_update flow
        elif isinstance(cmd, InventoryQueryCommand):
            # route to inventory_query flow
    """
    if not isinstance(context, dict):
        raise InventoryContextParseError("Context must be a dict.")

    task_type = str(context.get("task_type", "")).strip().lower()

    try:
        if task_type == "inventory_update":
            return InventoryUpdateCommand(**context)
        if task_type == "inventory_query":
            return InventoryQueryCommand(**context)
    except Exception as exc:  # pydantic validation errors bubble here
        raise InventoryContextParseError(str(exc)) from exc

    raise InventoryContextParseError(
        f"Unsupported inventory task_type: {task_type!r}. "
        "Expected 'inventory_update' or 'inventory_query'."
    )


# ---------------------------------------------------------------------------
# Documentation helpers
# ---------------------------------------------------------------------------

EXAMPLE_INVENTORY_UPDATE_CONTEXT: Dict[str, Any] = {
    "task_type": "inventory_update",
    "store": "dev",
    "product_title": "TEST - Handmade Sterling Silver Beaded Ankle Bracelets  | Birthstone Tanzanite December",
    "variants": [
        {"variant_label": "Medium", "new_quantity": 2},
        {"variant_label": "Large", "new_quantity": 1},
    ],
}

EXAMPLE_INVENTORY_QUERY_CONTEXT: Dict[str, Any] = {
    "task_type": "inventory_query",
    "store": "dev",
    "product_title_contains": "Tanzanite ankle bracelet",
}
