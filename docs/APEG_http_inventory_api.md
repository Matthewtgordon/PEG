# APEG HTTP Inventory API

## Endpoints

### GET /health

- Purpose: quick health check.
- Example response:

  {
    "status": "healthy",
    "version": "1.0.0",
    "test_mode": false,
    "debug": false,
    "timestamp": "2025-11-27T19:10:18.355563Z"
  }

### POST /run

- Purpose: generic APEG entrypoint.
- For inventory flows, we send an `inventory_update` context.

## Inventory Update Contract

Request example:

  POST /run
  Content-Type: application/json

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

Notes:
- `task_type` must be `"inventory_update"`.
- `store` is a logical key (e.g. `"dev"`, `"prod"`).
- `product_title` should match the Shopify Admin product title or a strong substring.
- `variants` is a list of objects with:
  - `variant_label`: human label (e.g. `"Medium"`, `"Large"`).
  - `new_quantity`: integer, final absolute quantity.

## Example curl

  curl -sS -X POST http://localhost:8000/run \
    -H "Content-Type: application/json" \
    -d '{
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
    }'

## Example successful response (shape)

  {
    "status": "success",
    "final_output": "{...stringified result...}",
    "state": {
      "mode": "inventory_update",
      "result": {
        "status": "success",
        "store": "dev",
        "product_id": "...",
        "product_title": "...",
        "updates": [
          {
            "variant_label": "Medium",
            "variant_id": "...",
            "update_result": {
              "product_id": "...",
              "variant_id": "...",
              "old_inventory": 2,
              "new_inventory": 2,
              "status": "updated",
              "timestamp": "..."
            }
          },
          {
            "variant_label": "Large",
            "variant_id": "...",
            "update_result": {
              "product_id": "...",
              "variant_id": "...",
              "old_inventory": 1,
              "new_inventory": 1,
              "status": "updated",
              "timestamp": "..."
            }
          }
        ]
      },
      "history": [],
      "score": 1.0,
      "error": null
    }
  }

This document is the contract for:
- Web UI buttons and forms
- Voice / LLM front door that constructs JSON and POSTs to `/run`.
