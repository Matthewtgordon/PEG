"""
Shopify Agent - Domain agent for Shopify e-commerce operations.

Phase 1: Stub implementations returning dummy data for orchestration testing
Phase 2: Real Shopify Admin API integration with authentication and webhooks

Capabilities:
- Product management (list, get, update)
- Inventory management
- Order management (list, get, create, fulfill)
- Customer messaging
- Etsy order synchronization

Configuration (via environment or config dict):
- SHOPIFY_STORE_DOMAIN: Store domain (e.g., "mystore.myshopify.com")
- SHOPIFY_ACCESS_TOKEN: Admin API access token
- SHOPIFY_API_VERSION: API version (default: "2024-01")

Usage:
    # Test mode (default, no real API calls)
    agent = ShopifyAgent(config={"test_mode": True})

    # Real API mode (requires credentials)
    agent = ShopifyAgent(config={
        "test_mode": False,
        "store_domain": "mystore.myshopify.com",
        "access_token": "shpat_xxxx"
    })
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from apeg_core.agents.base_agent import BaseAgent
from apeg_core.connectors.http_tools import HTTPClient

logger = logging.getLogger(__name__)


class ShopifyAPIError(Exception):
    """Exception raised for Shopify API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ShopifyAPIClient:
    """
    Low-level Shopify Admin API client.

    Handles authentication, rate limiting, and API versioning for
    Shopify Admin REST API calls.

    Attributes:
        store_domain: Shopify store domain
        access_token: Admin API access token
        api_version: API version string
    """

    def __init__(
        self,
        store_domain: str,
        access_token: str,
        api_version: str = "2024-01"
    ):
        """
        Initialize Shopify API client.

        Args:
            store_domain: Store domain (e.g., "mystore.myshopify.com")
            access_token: Admin API access token
            api_version: API version (default: "2024-01")
        """
        self.store_domain = store_domain.rstrip("/")
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{self.store_domain}/admin/api/{api_version}"

        self._http_client = HTTPClient(
            base_url=self.base_url,
            test_mode=False,
            timeout=30
        )

        logger.info("ShopifyAPIClient initialized for %s (API %s)", store_domain, api_version)

    def _headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to Shopify API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._http_client.get(url, params=params, headers=self._headers())

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to Shopify API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._http_client.post(url, json=data, headers=self._headers())

    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PUT request to Shopify API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._http_client.put(url, json=data, headers=self._headers())

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request to Shopify API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._http_client.delete(url, headers=self._headers())


class ShopifyAgent(BaseAgent):
    """
    Shopify domain agent for e-commerce operations.

    Supports both test mode (stub responses) and real API mode
    when credentials are provided.

    Configuration:
        test_mode: If True, use stub responses (default: True)
        store_domain: Shopify store domain
        access_token: Admin API access token
        api_version: API version (default: "2024-01")

    Environment variables (alternative to config):
        SHOPIFY_STORE_DOMAIN
        SHOPIFY_ACCESS_TOKEN
        SHOPIFY_API_VERSION
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        test_mode: Optional[bool] = None
    ):
        """
        Initialize Shopify agent with optional API client.

        Args:
            config: Configuration dictionary
            test_mode: Override test mode (for backward compatibility)
        """
        # Handle backward compatibility: test_mode can be passed directly
        # Pass test_mode to base class if specified
        base_test_mode = test_mode if test_mode is not None else False
        super().__init__(config, test_mode=base_test_mode)

        self._api_client: Optional[ShopifyAPIClient] = None

        # Try to initialize API client if not in test mode
        if not self.test_mode:
            self._init_api_client()

    def _init_api_client(self) -> None:
        """Initialize the Shopify API client from config or environment."""
        store_domain = self.config.get("store_domain") or os.environ.get("SHOPIFY_STORE_DOMAIN")
        access_token = self.config.get("access_token") or os.environ.get("SHOPIFY_ACCESS_TOKEN")
        api_version = self.config.get("api_version") or os.environ.get("SHOPIFY_API_VERSION", "2024-01")

        if store_domain and access_token:
            self._api_client = ShopifyAPIClient(
                store_domain=store_domain,
                access_token=access_token,
                api_version=api_version
            )
            logger.info("ShopifyAgent API client initialized")
        else:
            logger.warning(
                "ShopifyAgent: Missing credentials (SHOPIFY_STORE_DOMAIN, SHOPIFY_ACCESS_TOKEN). "
                "Using test mode fallback."
            )

    @property
    def name(self) -> str:
        """Return agent name."""
        return "ShopifyAgent"

    @property
    def has_api_client(self) -> bool:
        """Check if real API client is available."""
        return self._api_client is not None

    def execute(self, action: str, context: Dict) -> Dict:
        """Execute a Shopify action.

        Args:
            action: Action name (product_sync, inventory_check, seo_analysis)
            context: Action context dictionary

        Returns:
            Action result dictionary
        """
        logger.info(f"ShopifyAgent executing action '{action}' (test_mode={self.test_mode})")

        # Test mode: return mock data for backward compatibility
        if self.test_mode:
            if action == "product_sync":
                return {"status": "synced", "product_id": "mock-123", "title": "Test Product"}
            elif action == "inventory_check":
                return {"inventory": [{"sku": "TEST-001", "quantity": 50}]}
            elif action == "seo_analysis":
                return {"score": 85, "recommendations": ["Add meta description"]}
            else:
                return {"error": "Unknown action", "action": action}

        # Real mode: route to API-backed handlers
        if action == "product_sync":
            product_id = context.get("product_id")
            if product_id:
                return self.get_product(product_id)
            return {"status": "synced", "products": self.list_products()}
        elif action == "inventory_check":
            return {"inventory": self.list_products(limit=10)}
        elif action == "seo_analysis":
            return {"score": 85, "recommendations": ["Add meta description"]}
        else:
            return {"error": "Unknown action", "action": action}

    def describe_capabilities(self) -> List[str]:
        """
        List all Shopify operations supported by this agent.

        Returns:
            List of capability names
        """
        return [
            "list_products",
            "get_product",
            "update_inventory",
            "list_orders",
            "get_order",
            "create_order_from_etsy",
            "send_customer_message",
            "fulfill_order",
            "cancel_order",
        ]

    def list_products(
        self,
        status_filter: str | None = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List products in the Shopify store.

        Args:
            status_filter: Filter by status (active, archived, draft)
            limit: Maximum number of products to return

        Returns:
            List of product dictionaries
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info("ShopifyAgent.list_products(status=%s, limit=%d) [API]", status_filter, limit)
            try:
                params = {"limit": limit}
                if status_filter:
                    params["status"] = status_filter
                response = self._api_client.get("products.json", params=params)
                products = response.get("products", [])
                # Normalize response
                return [
                    {
                        "id": str(p.get("id")),
                        "title": p.get("title", ""),
                        "status": p.get("status", "active"),
                        "inventory": sum(v.get("inventory_quantity", 0) for v in p.get("variants", [])),
                        "price": p.get("variants", [{}])[0].get("price", "0.00"),
                        "sku": p.get("variants", [{}])[0].get("sku", ""),
                    }
                    for p in products
                ]
            except Exception as e:
                logger.error("Shopify API error in list_products: %s", e)
                raise ShopifyAPIError(f"Failed to list products: {e}")

        # Stub data for test mode
        logger.info("ShopifyAgent.list_products(status=%s, limit=%d) [STUB]", status_filter, limit)
        return [
            {
                "id": "demo-prod-1",
                "title": "Handmade Turquoise Anklet",
                "status": status_filter or "active",
                "inventory": 10,
                "price": "29.99",
                "sku": "ANK-TURQ-001",
            },
            {
                "id": "demo-prod-2",
                "title": "Rose Quartz Beaded Bracelet",
                "status": status_filter or "active",
                "inventory": 15,
                "price": "24.99",
                "sku": "BRC-ROSE-001",
            },
        ]

    def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific product.

        Args:
            product_id: Shopify product ID

        Returns:
            Product details dictionary
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info("ShopifyAgent.get_product(id=%s) [API]", product_id)
            try:
                response = self._api_client.get(f"products/{product_id}.json")
                p = response.get("product", {})
                return {
                    "id": str(p.get("id")),
                    "title": p.get("title", ""),
                    "description": p.get("body_html", ""),
                    "status": p.get("status", "active"),
                    "inventory": sum(v.get("inventory_quantity", 0) for v in p.get("variants", [])),
                    "price": p.get("variants", [{}])[0].get("price", "0.00"),
                    "sku": p.get("variants", [{}])[0].get("sku", ""),
                    "variants": [
                        {
                            "id": str(v.get("id")),
                            "title": v.get("title", ""),
                            "inventory": v.get("inventory_quantity", 0),
                            "price": v.get("price", "0.00"),
                            "sku": v.get("sku", ""),
                        }
                        for v in p.get("variants", [])
                    ],
                }
            except Exception as e:
                logger.error("Shopify API error in get_product: %s", e)
                raise ShopifyAPIError(f"Failed to get product {product_id}: {e}")

        # Stub data for test mode
        logger.info("ShopifyAgent.get_product(id=%s) [STUB]", product_id)
        return {
            "id": product_id,
            "title": "Stub Product Details",
            "description": "This is a stub product returned from ShopifyAgent.",
            "inventory": 5,
            "price": "19.99",
            "sku": "STUB-001",
            "variants": [
                {"id": "var-1", "title": "Default", "inventory": 5}
            ],
        }

    def update_inventory(
        self,
        product_id: str,
        variant_id: str | None = None,
        new_quantity: int = 0
    ) -> Dict[str, Any]:
        """
        Update inventory quantity for a product or variant.

        Args:
            product_id: Shopify product ID
            variant_id: Optional variant ID (if None, uses default variant)
            new_quantity: New inventory quantity

        Returns:
            Update result dictionary

        RESOLVED[APEG-PH-5]: Real Shopify API implementation
        Uses the Inventory Levels API to set inventory quantity.
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info(
                "ShopifyAgent.update_inventory(product=%s, variant=%s, qty=%d) [API]",
                product_id, variant_id, new_quantity
            )
            try:
                # If no variant_id, get the default variant from product
                if not variant_id:
                    product = self.get_product(product_id)
                    variants = product.get("variants", [])
                    if variants:
                        variant_id = variants[0].get("id")

                if not variant_id:
                    raise ShopifyAPIError("Could not determine variant ID")

                # Get the inventory item ID for this variant
                variant_response = self._api_client.get(f"variants/{variant_id}.json")
                inventory_item_id = variant_response.get("variant", {}).get("inventory_item_id")

                if not inventory_item_id:
                    raise ShopifyAPIError("Could not find inventory item ID")

                # Get current inventory level to find location
                levels_response = self._api_client.get(
                    "inventory_levels.json",
                    params={"inventory_item_ids": inventory_item_id}
                )
                levels = levels_response.get("inventory_levels", [])

                if not levels:
                    raise ShopifyAPIError("No inventory locations found")

                location_id = levels[0].get("location_id")
                old_quantity = levels[0].get("available", 0)

                # Set the new inventory level
                set_response = self._api_client.post(
                    "inventory_levels/set.json",
                    data={
                        "location_id": location_id,
                        "inventory_item_id": inventory_item_id,
                        "available": new_quantity
                    }
                )

                return {
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "inventory_item_id": str(inventory_item_id),
                    "location_id": str(location_id),
                    "old_inventory": old_quantity,
                    "new_inventory": new_quantity,
                    "status": "updated",
                    "timestamp": set_response.get("inventory_level", {}).get("updated_at", ""),
                }

            except Exception as e:
                logger.error("Shopify API error in update_inventory: %s", e)
                raise ShopifyAPIError(f"Failed to update inventory: {e}")

        # Stub data for test mode
        logger.info(
            "ShopifyAgent.update_inventory(product=%s, variant=%s, qty=%d) [STUB]",
            product_id, variant_id, new_quantity
        )
        return {
            "product_id": product_id,
            "variant_id": variant_id or "default-variant",
            "old_inventory": 5,
            "new_inventory": new_quantity,
            "status": "stub-updated",
            "timestamp": "2025-11-19T12:00:00Z",
        }

    def list_orders(
        self,
        status_filter: str | None = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List orders from the Shopify store.

        Args:
            status_filter: Filter by status (open, closed, cancelled, any)
            limit: Maximum number of orders to return

        Returns:
            List of order dictionaries

        RESOLVED[APEG-PH-5]: Real Shopify API implementation
        Uses the Orders API to list orders with optional status filtering.
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info("ShopifyAgent.list_orders(status=%s, limit=%d) [API]", status_filter, limit)
            try:
                params = {"limit": limit}
                if status_filter and status_filter != "any":
                    params["status"] = status_filter

                response = self._api_client.get("orders.json", params=params)
                orders = response.get("orders", [])

                return [
                    {
                        "id": str(o.get("id")),
                        "order_number": o.get("order_number"),
                        "status": o.get("financial_status", "unknown"),
                        "fulfillment_status": o.get("fulfillment_status"),
                        "total": o.get("total_price", "0.00"),
                        "customer": {
                            "email": o.get("email", ""),
                            "name": f"{o.get('customer', {}).get('first_name', '')} {o.get('customer', {}).get('last_name', '')}".strip(),
                        },
                        "line_items": [
                            {
                                "title": item.get("title", ""),
                                "quantity": item.get("quantity", 0),
                                "sku": item.get("sku", ""),
                            }
                            for item in o.get("line_items", [])
                        ],
                        "created_at": o.get("created_at"),
                    }
                    for o in orders
                ]

            except Exception as e:
                logger.error("Shopify API error in list_orders: %s", e)
                raise ShopifyAPIError(f"Failed to list orders: {e}")

        # Stub data for test mode
        logger.info("ShopifyAgent.list_orders(status=%s, limit=%d) [STUB]", status_filter, limit)
        return [
            {
                "id": "order-stub-1",
                "order_number": 1001,
                "status": status_filter or "open",
                "total": "54.98",
                "customer": {
                    "email": "customer@example.com",
                    "name": "Jane Doe"
                },
                "line_items": [
                    {"title": "Turquoise Anklet", "quantity": 2}
                ],
            },
        ]

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific order.

        Args:
            order_id: Shopify order ID

        Returns:
            Order details dictionary

        TODO[APEG-PH-5]: Replace with real Shopify API call
        """
        logger.info("ShopifyAgent.get_order(id=%s) [STUB]", order_id)

        return {
            "id": order_id,
            "order_number": 1001,
            "status": "open",
            "total": "29.99",
            "customer": {"email": "customer@example.com"},
            "fulfillment_status": "unfulfilled",
        }

    def create_order_from_etsy(
        self,
        etsy_order_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a Shopify order from Etsy order data.

        This is used for inventory synchronization when an Etsy sale occurs.

        Args:
            etsy_order_payload: Etsy order data dictionary with:
                - id: Etsy order/receipt ID
                - buyer: Buyer info (email, name)
                - items: Line items with listing_id, quantity, price
                - shipping_address: Shipping address details
                - total: Order total

        Returns:
            Created Shopify order dictionary

        RESOLVED[APEG-PH-5]: Real Shopify API implementation
        Creates a draft order in Shopify based on Etsy order data.
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info("ShopifyAgent.create_order_from_etsy() [API]")
            logger.debug("Etsy order data: %s", etsy_order_payload)
            try:
                # Map Etsy order to Shopify draft order format
                buyer = etsy_order_payload.get("buyer", {})
                items = etsy_order_payload.get("items", [])
                shipping = etsy_order_payload.get("shipping_address", {})

                # Build line items - these should reference existing Shopify products
                # In practice, you'd have a SKU mapping between Etsy and Shopify
                line_items = []
                for item in items:
                    line_item = {
                        "title": item.get("title", "Etsy Item"),
                        "quantity": item.get("quantity", 1),
                        "price": str(item.get("price", "0.00")),
                    }
                    # If SKU provided, try to match to variant
                    if item.get("sku"):
                        line_item["sku"] = item["sku"]
                    line_items.append(line_item)

                # Build draft order payload
                draft_order_data = {
                    "draft_order": {
                        "line_items": line_items,
                        "email": buyer.get("email", ""),
                        "note": f"Synced from Etsy order #{etsy_order_payload.get('id', 'unknown')}",
                        "tags": "etsy-sync",
                    }
                }

                # Add shipping address if provided
                if shipping:
                    draft_order_data["draft_order"]["shipping_address"] = {
                        "first_name": shipping.get("first_name", ""),
                        "last_name": shipping.get("last_name", ""),
                        "address1": shipping.get("address1", ""),
                        "address2": shipping.get("address2", ""),
                        "city": shipping.get("city", ""),
                        "province": shipping.get("state", ""),
                        "zip": shipping.get("zip", ""),
                        "country": shipping.get("country", "US"),
                    }

                # Create the draft order
                response = self._api_client.post("draft_orders.json", data=draft_order_data)
                draft_order = response.get("draft_order", {})

                return {
                    "created": True,
                    "source": "etsy",
                    "shopify_draft_order_id": str(draft_order.get("id")),
                    "etsy_order_id": str(etsy_order_payload.get("id", "unknown")),
                    "status": draft_order.get("status", "open"),
                    "invoice_url": draft_order.get("invoice_url", ""),
                    "total_price": draft_order.get("total_price", "0.00"),
                    "created_at": draft_order.get("created_at", ""),
                }

            except Exception as e:
                logger.error("Shopify API error in create_order_from_etsy: %s", e)
                raise ShopifyAPIError(f"Failed to create order from Etsy: {e}")

        # Stub data for test mode
        logger.info("ShopifyAgent.create_order_from_etsy() [STUB]")
        logger.debug("Etsy order data: %s", etsy_order_payload)
        return {
            "created": True,
            "source": "etsy",
            "shopify_order_id": "shopify-order-stub-123",
            "etsy_order_id": etsy_order_payload.get("id", "unknown"),
            "status": "stub-created",
            "message": "Stub order created for testing",
        }

    def send_customer_message(
        self,
        order_id: str,
        message_text: str,
        message_type: str = "note"
    ) -> Dict[str, Any]:
        """
        Send a message to customer (order note or email).

        Args:
            order_id: Shopify order ID
            message_text: Message content
            message_type: Type (note, email)

        Returns:
            Message send result

        RESOLVED[APEG-PH-5]: Real Shopify API implementation
        Adds a note to the order or triggers a notification.
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info(
                "ShopifyAgent.send_customer_message(order=%s, type=%s) [API]",
                order_id, message_type
            )
            try:
                if message_type == "note":
                    # Add order note
                    response = self._api_client.put(
                        f"orders/{order_id}.json",
                        data={
                            "order": {
                                "id": order_id,
                                "note": message_text,
                            }
                        }
                    )
                    order = response.get("order", {})
                    return {
                        "order_id": order_id,
                        "message": message_text,
                        "type": "note",
                        "status": "added",
                        "timestamp": order.get("updated_at", ""),
                    }
                else:
                    # For email type, we'd need to use notification endpoint
                    # This is a simplified implementation
                    logger.warning("Email notifications require additional setup")
                    return {
                        "order_id": order_id,
                        "message": message_text,
                        "type": message_type,
                        "status": "not_implemented",
                        "note": "Email notifications require webhook/email service setup",
                    }

            except Exception as e:
                logger.error("Shopify API error in send_customer_message: %s", e)
                raise ShopifyAPIError(f"Failed to send message: {e}")

        # Stub data for test mode
        logger.info(
            "ShopifyAgent.send_customer_message(order=%s, type=%s) [STUB]",
            order_id, message_type
        )
        return {
            "order_id": order_id,
            "message": message_text,
            "type": message_type,
            "status": "stub-sent",
            "timestamp": "2025-11-19T12:00:00Z",
        }

    def fulfill_order(
        self,
        order_id: str,
        tracking_number: str | None = None,
        tracking_company: str | None = None,
        notify_customer: bool = True
    ) -> Dict[str, Any]:
        """
        Mark an order as fulfilled.

        Args:
            order_id: Shopify order ID
            tracking_number: Optional shipping tracking number
            tracking_company: Optional tracking company (USPS, FedEx, UPS, etc.)
            notify_customer: Whether to send notification email

        Returns:
            Fulfillment result

        RESOLVED[APEG-PH-5]: Real Shopify API implementation
        Uses the Fulfillment API to create a fulfillment for all line items.
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info("ShopifyAgent.fulfill_order(id=%s) [API]", order_id)
            try:
                # Get order to find fulfillment order
                order = self._api_client.get(f"orders/{order_id}.json")
                order_data = order.get("order", {})

                # Get fulfillment orders
                fulfillment_orders_resp = self._api_client.get(
                    f"orders/{order_id}/fulfillment_orders.json"
                )
                fulfillment_orders = fulfillment_orders_resp.get("fulfillment_orders", [])

                if not fulfillment_orders:
                    raise ShopifyAPIError("No fulfillment orders found")

                # Create fulfillment for the first fulfillment order
                fulfillment_order = fulfillment_orders[0]
                fulfillment_order_id = fulfillment_order.get("id")

                # Build fulfillment payload
                fulfillment_data = {
                    "fulfillment": {
                        "line_items_by_fulfillment_order": [
                            {
                                "fulfillment_order_id": fulfillment_order_id,
                            }
                        ],
                        "notify_customer": notify_customer,
                    }
                }

                if tracking_number:
                    fulfillment_data["fulfillment"]["tracking_info"] = {
                        "number": tracking_number,
                    }
                    if tracking_company:
                        fulfillment_data["fulfillment"]["tracking_info"]["company"] = tracking_company

                # Create the fulfillment
                response = self._api_client.post("fulfillments.json", data=fulfillment_data)
                fulfillment = response.get("fulfillment", {})

                return {
                    "order_id": order_id,
                    "fulfillment_id": str(fulfillment.get("id")),
                    "status": fulfillment.get("status", "fulfilled"),
                    "tracking_number": tracking_number,
                    "tracking_company": tracking_company,
                    "notify_customer": notify_customer,
                    "timestamp": fulfillment.get("created_at", ""),
                }

            except Exception as e:
                logger.error("Shopify API error in fulfill_order: %s", e)
                raise ShopifyAPIError(f"Failed to fulfill order: {e}")

        # Stub data for test mode
        logger.info("ShopifyAgent.fulfill_order(id=%s) [STUB]", order_id)
        return {
            "order_id": order_id,
            "status": "fulfilled",
            "tracking_number": tracking_number,
            "timestamp": "2025-11-19T12:00:00Z",
        }

    def cancel_order(
        self,
        order_id: str,
        reason: str | None = None,
        email: bool = True,
        restock: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel an order.

        Args:
            order_id: Shopify order ID
            reason: Cancellation reason (customer, inventory, fraud, declined, other)
            email: Whether to send cancellation email to customer
            restock: Whether to restock items

        Returns:
            Cancellation result

        RESOLVED[APEG-PH-5]: Real Shopify API implementation
        Uses the Orders API to cancel an order.
        """
        # Use real API if available
        if self._api_client and not self.test_mode:
            logger.info("ShopifyAgent.cancel_order(id=%s) [API]", order_id)
            try:
                # Map reason to Shopify's expected format
                reason_map = {
                    "customer_request": "customer",
                    "customer": "customer",
                    "inventory": "inventory",
                    "fraud": "fraud",
                    "declined": "declined",
                    "other": "other",
                }
                cancel_reason = reason_map.get(reason or "customer", "customer")

                # Cancel the order
                response = self._api_client.post(
                    f"orders/{order_id}/cancel.json",
                    data={
                        "email": email,
                        "restock": restock,
                        "reason": cancel_reason,
                    }
                )
                order = response.get("order", {})

                return {
                    "order_id": order_id,
                    "status": "cancelled",
                    "reason": cancel_reason,
                    "email_sent": email,
                    "restocked": restock,
                    "cancelled_at": order.get("cancelled_at", ""),
                }

            except Exception as e:
                logger.error("Shopify API error in cancel_order: %s", e)
                raise ShopifyAPIError(f"Failed to cancel order: {e}")

        # Stub data for test mode
        logger.info("ShopifyAgent.cancel_order(id=%s) [STUB]", order_id)
        return {
            "order_id": order_id,
            "status": "cancelled",
            "reason": reason or "customer_request",
            "timestamp": "2025-11-19T12:00:00Z",
        }
