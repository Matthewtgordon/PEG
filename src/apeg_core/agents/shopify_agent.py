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

        TODO[APEG-PH-5]: Replace with real Shopify API call
        Expected API call:
            inventory_item = shopify.InventoryItem.find(variant_id)
            inventory_item.adjust_inventory_level(new_quantity)
        """
        logger.info(
            "ShopifyAgent.update_inventory(product=%s, variant=%s, qty=%d) [STUB]",
            product_id, variant_id, new_quantity
        )

        # Stub data
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

        TODO[APEG-PH-5]: Replace with real Shopify API call
        Expected API call:
            shopify.Order.find(limit=limit, status=status_filter)
        """
        logger.info("ShopifyAgent.list_orders(status=%s, limit=%d) [STUB]", status_filter, limit)

        # Stub data
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
            etsy_order_payload: Etsy order data dictionary

        Returns:
            Created Shopify order dictionary

        TODO[APEG-PH-5]: Implement order mapping and creation
        - Map Etsy order fields to Shopify order schema
        - Create draft order via API
        - Handle inventory updates
        - Log synchronization event
        """
        logger.info("ShopifyAgent.create_order_from_etsy() [STUB]")
        logger.debug("Etsy order data: %s", etsy_order_payload)

        # Stub data
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

        TODO[APEG-PH-5]: Implement customer messaging
        - Add order note via API
        - Or trigger email notification
        - Handle email templates
        """
        logger.info(
            "ShopifyAgent.send_customer_message(order=%s, type=%s) [STUB]",
            order_id, message_type
        )

        # Stub data
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
        tracking_number: str | None = None
    ) -> Dict[str, Any]:
        """
        Mark an order as fulfilled.

        Args:
            order_id: Shopify order ID
            tracking_number: Optional shipping tracking number

        Returns:
            Fulfillment result

        TODO[APEG-PH-5]: Implement order fulfillment
        """
        logger.info("ShopifyAgent.fulfill_order(id=%s) [STUB]", order_id)

        return {
            "order_id": order_id,
            "status": "fulfilled",
            "tracking_number": tracking_number,
            "timestamp": "2025-11-19T12:00:00Z",
        }

    def cancel_order(self, order_id: str, reason: str | None = None) -> Dict[str, Any]:
        """
        Cancel an order.

        Args:
            order_id: Shopify order ID
            reason: Optional cancellation reason

        Returns:
            Cancellation result

        TODO[APEG-PH-5]: Implement order cancellation
        """
        logger.info("ShopifyAgent.cancel_order(id=%s) [STUB]", order_id)

        return {
            "order_id": order_id,
            "status": "cancelled",
            "reason": reason or "customer_request",
            "timestamp": "2025-11-19T12:00:00Z",
        }
