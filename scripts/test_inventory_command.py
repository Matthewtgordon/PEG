from apeg_core.services.shopify_inventory_service import execute_inventory_command


def main() -> None:
    # InventoryCommand: set Medium=2, Large=1 for your test product.
    command = {
        "task_type": "inventory_update",
        "store": "dev",
        # Exact title from list_products() output
        "product_title": "TEST - Handmade Sterling Silver Beaded Ankle Bracelets  | Birthstone Tanzanite December",
        "variants": [
            {
                "variant_label": "Medium",
                "new_quantity": 2,
            },
            {
                "variant_label": "Large",
                "new_quantity": 1,
            },
        ],
    }

    result = execute_inventory_command(command)
    print("RESULT:")
    print(result)


if __name__ == "__main__":
    main()
