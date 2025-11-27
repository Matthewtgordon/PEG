"""
APEG Schema Definitions

This package contains canonical schema definitions for APEG data structures.

Modules:
--------
- inventory_commands: Schemas for Shopify inventory operations
"""

from apeg_core.schemas.inventory_commands import (
    InventoryUpdateCommand,
    InventoryQueryCommand,
    VariantUpdate,
    parse_inventory_context,
    InventoryContextParseError,
    EXAMPLE_INVENTORY_UPDATE_CONTEXT,
    EXAMPLE_INVENTORY_QUERY_CONTEXT,
)

__all__ = [
    "InventoryUpdateCommand",
    "InventoryQueryCommand",
    "VariantUpdate",
    "parse_inventory_context",
    "InventoryContextParseError",
    "EXAMPLE_INVENTORY_UPDATE_CONTEXT",
    "EXAMPLE_INVENTORY_QUERY_CONTEXT",
]
