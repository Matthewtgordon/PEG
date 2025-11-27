from apeg_core.services.shopify_inventory_service import execute_inventory_command


def main() -> None:
    # Example command: set Medium=2, Large=1 for your test product.
    command = {
        "task_type": "inventory_update",
        "store": "dev",
        "product_title": "Tanzanite ankle bracelet",  # substring of your long title
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
